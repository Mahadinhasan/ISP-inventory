from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .forms import RegisterForm, MaterialForm, TaskForm, RequestForm, SystemSettingForm, NotificationSettingForm, UsedMaterialForm
from .models import Material, Task, MaterialRequest, UserProfile, SystemSetting, NotificationSetting, UsedMaterial, MaterialMonthlyCount
from .utils import ensure_userprofile
from django.db.models import Sum, Q, F, Case, When, IntegerField, Count
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
import json
import io
from io import StringIO
from django.core.paginator import Paginator
import requests
"""Export the current report as an Excel (.xlsx) file."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json as _json
from django.db.models.functions import TruncDate

# Helper function to handle month-end resets
def process_month_end_reset():
    """
    Check if month has ended and reset quantities if needed.
    Archives current month quantities to MaterialMonthlyCount.
    """
    now = timezone.now()
    current_month_start = datetime(now.year, now.month, 1)
    
    # Check if this month's reset has already been processed
    system_key = f"month_reset_{now.year}_{now.month}"
    try:
        setting = SystemSetting.objects.get(key=system_key)
        # Already processed this month
        return False
    except SystemSetting.DoesNotExist:
        pass
    
    # Process each material with quantity > 0
    for material in Material.objects.filter(quantity__gt=0):
        # Archive the current quantity to MaterialMonthlyCount
        monthly_count, created = MaterialMonthlyCount.objects.get_or_create(
            material=material,
            month=current_month_start,
            defaults={'count': material.quantity}
        )
        
        if not created:
            monthly_count.count = material.quantity
            monthly_count.save()
        
        # Reset quantity to 0
        material.quantity = 0
        material.save()
    
    # Mark this month's reset as processed
    SystemSetting.objects.update_or_create(
        key=system_key,
        defaults={'value': str(now), 'description': f'Month-end reset processed for {current_month_start.strftime("%B %Y")}'}
    )
    
    return True


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()

            # Ensure role groups exist and add user to selected group
            role = form.cleaned_data.get('role', 'Branch')
            for r in ['Admin', 'Storekeeper', 'Branch', 'NOC']:
                Group.objects.get_or_create(name=r)
            grp = Group.objects.get(name=role)
            user.groups.add(grp)

            # Create / update the associated UserProfile
            try:
                profile = ensure_userprofile(user)
                if profile:
                    profile.role     = role
                    profile.phone    = form.cleaned_data.get('phone', '')
                    profile.address  = form.cleaned_data.get('address', '')
                    profile.city     = form.cleaned_data.get('city', '')
                    profile.zip_code = form.cleaned_data.get('zip_code', '')
                    if form.cleaned_data.get('image'):
                        profile.image = form.cleaned_data['image']
                    profile.save()
            except Exception:
                pass

            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'inventory/register.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        user = authenticate(
            username=request.POST['username'],
            password=request.POST['password']
        )

        if user:
            login(request, user)

            if not request.POST.get('remember_me'):
                request.session.set_expiry(0)  # browser close
            else:
                request.session.set_expiry(60 * 60 * 1)  # 1 hour

            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials")
    return render(request, 'inventory/login.html')
  
@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    #Internal Communication Card show all user massage and announcement (fetch from external API websocket or database)


    # Request send by Branch materials approved by admin and auto update total materials count unique materials False
    if role == 'Branch':
        # For Branch: Count all approved requests with Normal stock status (not unique materials)
        total_materials = MaterialRequest.objects.filter(
            requester=request.user, 
            status='Approved',
            material__status='Normal'  # Only count materials with Normal stock status
        ).count()  # Count all approved requests, not distinct materials
    else:
        # For Admin & Storekeeper: Total count of all materials in system
        total_materials = Material.objects.count()
    
    active_tasks = Task.objects.filter(status='In Progress').count()
    pending_requests = MaterialRequest.objects.filter(status='Pending', requester=request.user).count()

    # Data for dashboard modals - Role-specific
    all_tasks = Task.objects.all().order_by('-created_at')
    all_requests = MaterialRequest.objects.filter(requester=request.user).order_by('-requested_at')
    all_used_materials = UsedMaterial.objects.all().select_related('technician', 'material').order_by('-added_at')
    
    # Role-specific material data for the materials modal
    technician_approved_materials = None
    advance_materials = None
    all_materials = None
    
    if role == 'Branch':
        # For Branch: Get approved MaterialRequest objects with Normal stock status only
        technician_approved_materials = MaterialRequest.objects.filter(
            requester=request.user,
            status='Approved',
            material__status='Normal'  # Only show materials with Normal stock status
        ).select_related('material').order_by('-requested_at')
        # Get Advance type requests for branch user
        advance_materials = MaterialRequest.objects.filter(
            requester=request.user,
            request_type='Advance',
            status='Approved'
        ).select_related('material').order_by('-requested_at')
    else:
        # For Admin & Storekeeper: Get all materials
        all_materials = Material.objects.all().order_by('-added_at')
        # Get all advance requests
        advance_materials = MaterialRequest.objects.filter(
            request_type='Advance',
            status='Approved'
        ).select_related('material', 'requester').order_by('-requested_at')
    
    # Branch specific stats
    my_stock_count = 0
    used_materials_count = 0
    used_material_form = None
    
    if role == 'Branch':
        # Calculate stock: Approved Requests (In) - Used Materials (Out)
        total_in = MaterialRequest.objects.filter(requester=request.user, status='Approved').aggregate(s=Sum('quantity'))['s'] or 0
        total_out = UsedMaterial.objects.filter(technician=request.user).aggregate(s=Sum('quantity'))['s'] or 0
        my_stock_count = total_in - total_out
        used_materials_count = UsedMaterial.objects.filter(technician=request.user).count()
        used_material_form = UsedMaterialForm(user=request.user)

    # Admin specific stats and branch user stats
    total_users = 0
    if role == 'Admin':
        total_users = User.objects.count()
    elif role == 'Branch':
        total_users = User.objects.filter(userprofile__role='Branch').count()
    
    #used materials
    # if role in ['Admin', 'Storekeeper', 'Branch']:
    #     all_used_materials = UsedMaterial.objects.filter(status='Accepted').select_related('technician', 'material').order_by('-added_at')
    # else:
    #     all_used_materials = []
    
    # # Role-specific material data for the materials modal
    # technician_approved_materials = None
    # advance_materials = None
    # all_materials = None
    # approved_requests = None  # For Admin/Storekeeper modal
    
    # if role == 'Branch':
    #     # For Branch: Get approved MaterialRequest objects with Normal stock status only
    #     technician_approved_materials_qs = MaterialRequest.objects.filter(
    #         requester=request.user,
    #         status='Accepted',
    #         material__status='Normal'  # Only show materials with Normal stock status
    #     ).select_related('material').order_by('-requested_at')
        
    #     # Calculate available quantity for each approved material (requested - used)
    #     technician_approved_materials = []
    #     for req in technician_approved_materials_qs:
    #         # Get used quantity for this material that has been accepted
    #         used_qty = UsedMaterial.objects.filter(
    #             technician=request.user,
    #             material=req.material,
    #             status='Accepted'
    #         ).aggregate(total=Sum('quantity'))['total'] or 0
            
    #         # Available = Requested - Used
    #         available_qty = req.quantity - used_qty
            
    #         # Store request with available quantity
    #         technician_approved_materials.append({
    #             'request': req,
    #             'available_quantity': available_qty,
    #             'used_quantity': used_qty
    #         })

    return render(request, 'inventory/dashboard.html', {
        'total_materials': total_materials,
        'active_tasks': active_tasks,
        'pending_requests': pending_requests,
        'all_materials': all_materials,
        'technician_approved_materials': technician_approved_materials,
        'advance_materials': advance_materials,
        'all_tasks': all_tasks,
        'all_requests': all_requests,
        'all_used_materials': all_used_materials,
        'role': role,
        'user': request.user,
        'my_stock_count': my_stock_count,
        'used_materials_count': used_materials_count,
        'used_material_form': used_material_form,
        'total_users': total_users,
        # 'all_used_materials': all_used_materials,
        # 'technician_approved_materials': technician_approved_materials,
    })

# @login_required
# def materials_view(request):
#     profile = ensure_userprofile(request.user)
#     role = profile.role if profile else 'Branch'

#     # Base queryset
#     materials = Material.objects.all().order_by('-added_at')
    
#     # Materials count normal/Low stock/Out of stock
#     total_normal_stock = Material.objects.filter(status='Normal').count()
#     total_low_stock = Material.objects.filter(status='Low Stock').count()
#     total_out_of_stock = Material.objects.filter(status='Out of Stock').count()

#     # Search filter - name, category, status
#     search = request.GET.get('search', '').strip()
#     if search:
#         materials = materials.filter(
#             Q(name__icontains=search) | Q(category__icontains=search) | Q(status__icontains=search)
#         )

#     # Filter by category and stock_status    
#     category = request.GET.get('category', '')
#     stock_status = request.GET.get('stock_status', '')
#     if category:
#         materials = materials.filter(category=category)
#     if stock_status:
#         status_map = {
#             'low': 'Low Stock',
#             'normal': 'Normal',
#             'out_of_stock': 'Out of Stock'
#         }
#         db_status = status_map.get(stock_status, stock_status)
#         materials = materials.filter(status=db_status)
        
#     # Pagination
#     paginator = Paginator(materials, 10)
#     page_number = request.GET.get('page')
#     materials_page = paginator.get_page(page_number)

#     if request.method == 'POST':
#         material_id = request.POST.get('material_id')
#         action = request.POST.get('action')

#         # Delete action
#         if action == 'delete':
#             if role != 'Storekeeper':
#                 messages.error(request, "Permission denied. Only Storekeeper can delete materials.")
#                 return redirect('materials')
            
#             material = get_object_or_404(Material, id=material_id)
#             material.delete()
#             messages.success(request, "Material deleted successfully!")
#             return redirect('materials')

#         # Add or Edit action
#         else:
#             if role != 'Storekeeper':
#                 messages.error(request, "Permission denied. Only Storekeeper can add/edit materials.")
#                 return redirect('materials')

#             instance = None
#             if material_id and material_id != 'undefined' and material_id.isdigit():
#                 instance = get_object_or_404(Material, id=material_id)
            
#             form = MaterialForm(request.POST, user=request.user, instance=instance)
#             if form.is_valid():
#                 form.save()
#                 messages.success(request, "Material saved successfully!")
#                 return redirect('materials')
#             else:
#                 messages.error(request, "Invalid data or material name already exists!")
#                 return redirect('materials')

#     form = MaterialForm(user=request.user)
#     context = {
#         'category': category,
#         'total_normal_stock': total_normal_stock,
#         'total_low_stock': total_low_stock,
#         'total_out_of_stock': total_out_of_stock,
#         'stock_status': stock_status,
#         'materials_page': materials_page,
#         'search': search,
#         'form': form,
#         'role': role,
#     }
#     return render(request, 'inventory/materials.html', context)




# @login_required
# def material_json(request, pk):
#     """Return material data as JSON for populating the
#      edit form via AJAX."""
#     try:
#         mat = Material.objects.get(pk=pk)
#     except Material.DoesNotExist:
#         return JsonResponse({'error': 'Material not found'}, status=404)

#     profile = ensure_userprofile(request.user)
#     role = profile.role if profile else 'Branch'
    
#     # Only Storekeeper can edit materials
#     if role != 'Storekeeper':
#         return JsonResponse({'error': 'Permission denied'}, status=403)

#     data = {
#         'id': mat.id,
#         'name': mat.name,
#         'category': mat.category,
#         'quantity': mat.quantity,
#         'min_stock_level': mat.min_stock_level,
#         'status': mat.status,
#         'notes': mat.notes or '',
#     }
#     return JsonResponse(data)

@login_required
def materials_view(request):
    """Materials management: only Storekeeper can create, edit, delete."""
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    # Base queryset - Admin/Storekeeper see all; Branch sees all (read-only)
    materials = Material.objects.all().order_by('-added_at')

    # Stock counts (Admin/Storekeeper only)
    total_normal_stock = Material.objects.filter(status='Normal').count()
    total_low_stock = Material.objects.filter(status='Low Stock').count()
    total_out_of_stock = Material.objects.filter(status='Out of Stock').count()

    # Search: name, category, status
    search = request.GET.get('search', '').strip()
    if search:
        materials = materials.filter(
            Q(name__icontains=search) | Q(category__icontains=search) | Q(status__icontains=search)
        )

    # Filter by category and stock_status
    category = request.GET.get('category', '')
    stock_status = request.GET.get('stock_status', '')
    if category:
        materials = materials.filter(category=category)
    if stock_status:
        status_map = {'low': 'Low Stock', 'normal': 'Normal', 'out_of_stock': 'Out of Stock'}
        db_status = status_map.get(stock_status, stock_status)
        materials = materials.filter(status=db_status)

    # Pagination
    paginator = Paginator(materials, 10)
    page_number = request.GET.get('page')
    materials_page = paginator.get_page(page_number)

    # POST: Create, Edit, Delete (Storekeeper only)
    if request.method == 'POST':
        if role != 'Storekeeper':
            messages.error(request, "Only Storekeeper can add, edit, or delete materials.")
            return redirect('materials')

        action = request.POST.get('action')
        material_id = request.POST.get('material_id', '').strip()

        # Delete Material (Storekeeper can delete any material)
        if action == 'delete':
            if not material_id or not material_id.isdigit():
                messages.error(request, "Invalid material specified.")
                return redirect('materials')
            try:
                mat = Material.objects.get(pk=material_id)
                mat.delete()
                messages.success(request, "Material deleted successfully.")
            except Material.DoesNotExist:
                messages.error(request, "Material not found.")
            return redirect('materials')

        # Create/Edit Material (Storekeeper can edit any material)
        instance = None
        if material_id and material_id != 'undefined' and material_id.isdigit():
            try:
                instance = Material.objects.get(pk=material_id)
            except Material.DoesNotExist:
                messages.error(request, "Material not found.")
                return redirect('materials')

        form = MaterialForm(request.POST, user=request.user, instance=instance)
        if form.is_valid():
            material = form.save(commit=False)
            is_new = not material.id

            material.save()
            messages.success(request, "Material saved successfully!")
            return redirect('materials')
        else:
            error_msg = "Please correct the errors below." if form.errors else "Invalid data."
            for field, errors in form.errors.items():
                if errors:
                    messages.error(request, f"{field}: {errors[0]}")
                    break
            else:
                messages.error(request, error_msg)
            return redirect('materials')

    form = MaterialForm(user=request.user)
    context = {
        'search': search,
        'category': category,
        'stock_status': stock_status,
        'total_normal_stock': total_normal_stock,
        'total_low_stock': total_low_stock,
        'total_out_of_stock': total_out_of_stock,
        'materials': materials_page,
        'form': form,
        'role': role,
        'user': request.user,
        'materials_page': materials_page,
    }
    return render(request, 'inventory/materials.html', context)


@login_required
def material_json(request, pk):
    """Return material data as JSON for populating the
     edit form via AJAX."""
    try:
        mat = Material.objects.get(pk=pk)
    except Material.DoesNotExist:
        return JsonResponse({'error': 'Material not found'}, status=404)

    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'
    # Only Storekeeper can fetch material data for edit form
    if role != 'Storekeeper':
        return JsonResponse({'error': 'Permission denied'}, status=403)

    data = {
        'id': mat.id,
        'name': mat.name,
        'category': mat.category,
        'quantity': mat.quantity,
        'min_stock_level': mat.min_stock_level,
        'status': mat.status,
    }
    return JsonResponse(data)

# @login_required
# def tasks_view(request):
#     profile = ensure_userprofile(request.user)
#     role = profile.role if profile else 'Branch'

#     if role == 'Branch':
#         tasks = Task.objects.filter(technician=request.user).order_by('-created_at')
#     else:
#         tasks = Task.objects.all().order_by('-created_at')

#     if request.method == 'POST':
#         action = request.POST.get('action')
        
#         if action == 'create':
#             if role == 'Branch':
#                  messages.error(request, "Branch users cannot create tasks.")
#                  return redirect('tasks')
#             form = TaskForm(request.POST)
#             if form.is_valid():
#                 form.save()
#                 messages.success(request, "Task created!")
#                 return redirect('tasks')
        
#         elif action == 'update_status':
#             task_id = request.POST.get('task_id')
#             new_status = request.POST.get('status')
#             try:
#                 task = Task.objects.get(pk=task_id)
#                 # Permission check
#                 if role == 'Branch' and task.requester != request.user:
#                     messages.error(request, "Permission denied.")
#                 else:
#                     task.status = new_status
#                     task.save()
#                     messages.success(request, f"Task status updated to {new_status}")
#             except Task.DoesNotExist:
#                 messages.error(request, "Task not found.")
#             return redirect('tasks')

#         elif action == 'delete':
#             if role != 'Admin':
#                 messages.error(request, "Only Admins can delete tasks.")
#                 return redirect('tasks')
#             task_id = request.POST.get('task_id')
#             try:
#                 task = Task.objects.get(pk=task_id)
#                 task.delete()
#                 messages.success(request, "Task deleted.")
#             except Task.DoesNotExist:
#                 messages.error(request, "Task not found.")
#             return redirect('tasks')

#     else:
#         form = TaskForm()
        
#     return render(request, 'inventory/tasks.html', {'tasks': tasks.order_by('-created_at'), 'form': form, 'role': role})

@login_required
def requests_view(request):
    base_requests = MaterialRequest.objects.filter(requester=request.user).order_by('-requested_at')
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'
    
    # For Admin/Storekeeper, show all requests instead of just their own
    if role in ['Admin', 'Storekeeper']:
        base_requests = MaterialRequest.objects.all().order_by('-requested_at')

    #Request count (pending/approved/rejected)
    pending_count = base_requests.filter(status='Pending').count()
    approved_count = base_requests.filter(status='Approved').count()
    rejected_count = base_requests.filter(status='Rejected').count()
    advance_count = base_requests.filter(request_type='Advance').count()
    
    # Get users for dropdown - improved logic to handle both UserProfile and Groups
    branch_group = Group.objects.filter(name='Branch').first()
    users_from_profile = User.objects.filter(userprofile__role='Branch').values_list('id', flat=True)
    users_from_group = User.objects.filter(groups=branch_group).values_list('id', flat=True) if branch_group else []
    all_branch_users = set(users_from_profile) | set(users_from_group)
    users = User.objects.filter(id__in=all_branch_users).select_related('userprofile').annotate(
        request_count=Sum(
            Case(
                When(material_requests__status='Approved', then=1),
                default=0,
                output_field=IntegerField()
            )
        )
    ).order_by('first_name', 'last_name')
    
    # Ensure all users have UserProfile
    for user in users:
        try:
            ensure_userprofile(user)
        except Exception:
            pass
    
    # Handle user dropdown filter - filter requests by selected branch user
    selected_user = None
    selected_user_id = request.GET.get('user', '').strip()
    if selected_user_id and selected_user_id.isdigit():
        try:
            selected_user = User.objects.get(id=selected_user_id)
            # Filter requests by this user
            base_requests = base_requests.filter(requester=selected_user)
            pending_count = base_requests.filter(status='Pending').count()
            approved_count = base_requests.filter(status='Approved').count()
            rejected_count = base_requests.filter(status='Rejected').count()
        except User.DoesNotExist:
            selected_user = None

    # Search Logic - apply BEFORE pagination
    search_query = request.GET.get('search', '').strip()
    if search_query:
        base_requests = base_requests.filter(
            Q(material__name__icontains=search_query) | 
            Q(user_note__icontains=search_query) | 
            Q(notes__icontains=search_query)|
            #type of request search
            Q(request_type__icontains=search_query)
            # Q(requester__username__icontains=search_query)
        )

    # Combine all requests (both Regular and Advance) for unified table display
    all_requests = base_requests.order_by('-requested_at')
    
    # Pagination applied to all requests combined
    paginator = Paginator(all_requests, 20)  # Show 20 requests per page
    page_number = request.GET.get('page')
    requests_page = paginator.get_page(page_number)
    
    # Count advance requests for display
    advance_count = base_requests.filter(request_type='Advance').count()

    # Initialize form - will be used in both GET and POST
    form = RequestForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        # Save received_by (Branch requester only) via AJAX (expects JSON)
        if action == 'save_received_by':
            if role != 'Branch':
                return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

            req_id = (request.POST.get('req_id') or '').strip()
            received_by = (request.POST.get('received_by') or '').strip()

            if not req_id.isdigit():
                return JsonResponse({'success': False, 'error': 'Invalid request id.'}, status=400)
            if not received_by:
                return JsonResponse({'success': False, 'error': 'Received By is required.'}, status=400)

            try:
                req = MaterialRequest.objects.get(pk=int(req_id), requester=request.user)
            except MaterialRequest.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Request not found.'}, status=404)

            if req.status != 'Approved':
                return JsonResponse({'success': False, 'error': 'Only approved requests can be recorded.'}, status=400)

            req.received_by = received_by
            req.received_at = timezone.now()
            req.save(update_fields=['received_by', 'received_at'])
            return JsonResponse({
                'success': True,
                'received_by': req.received_by,
                'received_at': req.received_at.isoformat() if req.received_at else None,
            })
        
        # Create Request
        if action == 'create':
            if role in ['Admin', 'Storekeeper']:
                 messages.error(request, "Only Branch users can submit requests.")
                 return redirect('requests')

            form = RequestForm(request.POST)
            if form.is_valid():
                req = form.save(commit=False)
                req.requester = request.user
                
                # Get request_type from POST (comes from hidden field in form)
                request_type = request.POST.get('request_type', 'Regular')
                if request_type in ['Regular', 'Advance']:
                    req.request_type = request_type
                else:
                    req.request_type = 'Regular'
                
                req.save()
                req_type_display = 'Advance' if req.request_type == 'Advance' else 'Regular'
                messages.success(request, f"{req_type_display} request submitted successfully!")
                return redirect('requests')
        
        # Manage Request (Admin only)
        elif action in ['accept', 'reject', 'save_note', 'delete']:
            if role != 'Admin':
                messages.error(request, "Permission denied.")
                return redirect('requests')
                
            req_id = request.POST.get('req_id')
            
            # Delete Action
            if action == 'delete':
                try:
                    req = MaterialRequest.objects.get(pk=req_id)
                    if req.status == 'Approved':
                        # Return stock before deleting
                        try:
                            with transaction.atomic():
                                mat = Material.objects.select_for_update().get(pk=req.material.id)
                                mat.quantity += req.quantity
                                mat.save()
                                req.delete()
                                messages.success(request, f"Approved request deleted. {req.quantity} units returned to {mat.name}.")
                        except Exception as e:
                            messages.error(request, f"Internal error during stock return: {str(e)}")
                    else:
                        req.delete()
                        messages.success(request, "Request deleted successfully.")
                except MaterialRequest.DoesNotExist:
                    messages.error(request, "Request not found.")
                return redirect('requests')

            note = request.POST.get('admin_note', '')
            admin_quantity = request.POST.get('quantity', '').strip()
            
            try:
                req = MaterialRequest.objects.get(pk=req_id)
                
                if action == 'accept':
                    if req.status == 'Approved':
                        messages.warning(request, "Request already approved.")
                        return redirect('requests')
                    
                    # Get the quantity to approve (admin can override)
                    try:
                        if admin_quantity:
                            approved_qty = int(admin_quantity)
                            if approved_qty <= 0:
                                messages.error(request, "Quantity must be greater than 0.")
                                return redirect('requests')
                        else:
                            # Use requested quantity if admin didn't specify
                            approved_qty = req.quantity
                    except ValueError:
                        messages.error(request, "Invalid quantity value.")
                        return redirect('requests')
                    
                    # Check if sufficient stock available
                    if approved_qty > req.material.quantity:
                        messages.error(request, f"Insufficient stock for {req.material.name}. Available: {req.material.quantity}, Requested: {approved_qty}")
                        return redirect('requests')
                    
                    try:
                        with transaction.atomic():
                            # Refresh material to be safe
                            mat = Material.objects.select_for_update().get(pk=req.material.id)
                            if mat.quantity < approved_qty:
                                raise ValueError("Insufficient stock")
                            
                            # Deduct the approved quantity from material
                            mat.quantity -= approved_qty
                            mat.save()
                            
                            # Update request with approved quantity
                            req.quantity = approved_qty
                            req.status = 'Approved'
                            req.admin_note = note
                            req.save()
                            messages.success(request, f"Request approved. {approved_qty} units deducted from {mat.name}.")
                    except Exception as e:
                         messages.error(request, f"Transaction failed: {str(e)}")
                         return redirect('requests')

                elif action == 'reject':
                    if req.status == 'Approved':
                        try:
                            with transaction.atomic():
                                # Return quantity to material stock
                                mat = Material.objects.select_for_update().get(pk=req.material.id)
                                mat.quantity += req.quantity
                                mat.save()
                                
                                # Update request status
                                req.status = 'Rejected'
                                req.admin_note = note
                                req.save()
                                messages.success(request, f"Request rejected and {req.quantity} units returned to {mat.name}.")
                        except Exception as e:
                             messages.error(request, f"Failed to return stock: {str(e)}")
                             return redirect('requests')
                    else:
                        req.status = 'Rejected'
                        req.admin_note = note
                        req.save()
                        messages.success(request, "Request rejected.")
                
                elif action == 'save_note':
                     req.admin_note = note
                     req.save()
                     messages.success(request, "Note saved.")

            except MaterialRequest.DoesNotExist:
                messages.error(request, "Request not found.")
            return redirect('requests')

    else:
        form = RequestForm()

    return render(request, 'inventory/requests.html', {
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'requests': requests_page, 
        'form': form,
        'role': role,
        'page_obj': requests_page,
        'users': users,
        'advance_count': advance_count,
        'selected_user': selected_user,
    })

@login_required
def reports_view(request):
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    # ── Date range ──
    preset    = request.GET.get('preset', '')
    from_date = request.GET.get('from_date', '')
    to_date   = request.GET.get('to_date', '')
    report_type = request.GET.get('type', 'all')

    now = timezone.now()
    if preset == 'today':
        from_date = to_date = now.strftime('%Y-%m-%d')
    elif preset == 'week':
        from_date = (now - timezone.timedelta(days=6)).strftime('%Y-%m-%d')
        to_date   = now.strftime('%Y-%m-%d')
    elif preset == 'month':
        from_date = now.replace(day=1).strftime('%Y-%m-%d')
        to_date   = now.strftime('%Y-%m-%d')
    elif preset == 'last30':
        from_date = (now - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
        to_date   = now.strftime('%Y-%m-%d')
    elif preset == 'last90':
        from_date = (now - timezone.timedelta(days=90)).strftime('%Y-%m-%d')
        to_date   = now.strftime('%Y-%m-%d')
    else:
        # Default: last 30 days if nothing provided
        if not from_date:
            from_date = (now - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = now.strftime('%Y-%m-%d')

    try:
        start = datetime.strptime(from_date, '%Y-%m-%d').date()
        end   = datetime.strptime(to_date,   '%Y-%m-%d').date()
    except ValueError:
        start = (now - timezone.timedelta(days=30)).date()
        end   = now.date()
        from_date = start.strftime('%Y-%m-%d')
        to_date   = end.strftime('%Y-%m-%d')

    # ── Base queryset ─────────────────────────────────────────────────────────
    requests_qs = MaterialRequest.objects.filter(
        requested_at__date__gte=start,
        requested_at__date__lte=end
    ).select_related('material', 'requester')

    # Role filter: Branch users see only their own requests
    if role == 'Branch':
        requests_qs = requests_qs.filter(requester=request.user)

    # ── Summary Stats ─────────────────────────────────────────────────────────
    total_requests   = requests_qs.count()
    approved_count   = requests_qs.filter(status='Approved').count()
    pending_count    = requests_qs.filter(status='Pending').count()
    rejected_count   = requests_qs.filter(status='Rejected').count()
    total_qty_issued = requests_qs.filter(status='Approved').aggregate(total=Sum('quantity'))['total'] or 0
    advance_count    = requests_qs.filter(request_type='Advance').count()

    # Material stock summary
    total_materials  = Material.objects.count()
    low_stock_items  = Material.objects.filter(status='Low Stock').count()
    out_of_stock     = Material.objects.filter(status='Out of Stock').count()
    normal_stock     = Material.objects.filter(status='Normal').count()

    # Used materials in period
    used_qs = UsedMaterial.objects.filter(
        added_at__date__gte=start,
        added_at__date__lte=end
    )
    if role == 'Branch':
        used_qs = used_qs.filter(technician=request.user)
    total_used_records = used_qs.count()
    total_used_qty     = used_qs.aggregate(total=Sum('quantity'))['total'] or 0

    # ── Top 10 materials by approved quantity ─────────────────────────────────
    top_materials = (
        requests_qs.filter(status='Approved')
        .values('material__name')
        .annotate(total_qty=Sum('quantity'), req_count=Count('id'))
        .order_by('-total_qty')[:10]
    )

    # ── Per-user breakdown (Admin/Storekeeper only) ───────────────────────────
    user_breakdown = []
    if role in ['Admin', 'Storekeeper']:
        user_breakdown = (
            requests_qs
            .values('requester__username', 'requester__first_name', 'requester__last_name')
            .annotate(
                total_req=Count('id'),
                approved=Count('id', filter=Q(status='Approved')),
                pending=Count('id', filter=Q(status='Pending')),
                rejected=Count('id', filter=Q(status='Rejected')),
                qty_issued=Sum('quantity', filter=Q(status='Approved'))
            )
            .order_by('-approved')[:15]
        )

    # ── Chart data: daily request counts over the date range ─────────────────
    daily_data = (
        requests_qs
        .annotate(day=TruncDate('requested_at'))
        .values('day')
        .annotate(
            approved=Count('id', filter=Q(status='Approved')),
            pending=Count('id', filter=Q(status='Pending')),
            rejected=Count('id', filter=Q(status='Rejected')),
        )
        .order_by('day')
    )
    chart_labels   = [str(d['day']) for d in daily_data]
    chart_approved = [d['approved'] for d in daily_data]
    chart_pending  = [d['pending']  for d in daily_data]
    chart_rejected = [d['rejected'] for d in daily_data]

    # Material category breakdown
    category_data = (
        requests_qs.filter(status='Approved')
        .values('material__category')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')
    )
    cat_labels = [d['material__category'] or 'Unknown' for d in category_data]
    cat_values = [d['qty'] or 0 for d in category_data]

    # ── Recent requests (up to 50 for table) ─────────────────────────────────
    recent_requests = requests_qs.order_by('-requested_at')[:50]

    # ── Low-stock materials list ──────────────────────────────────────────────
    low_stock_list = Material.objects.filter(
        status__in=['Low Stock', 'Out of Stock']
    ).order_by('status', 'name')[:20]

    context = {
        # Date range
        'from_date':   from_date,
        'to_date':     to_date,
        'preset':      preset,
        'report_type': report_type,
        'role':        role,
        # Summary
        'total_requests':   total_requests,
        'approved_count':   approved_count,
        'pending_count':    pending_count,
        'rejected_count':   rejected_count,
        'total_qty_issued': total_qty_issued,
        'advance_count':    advance_count,
        'total_used_records': total_used_records,
        'total_used_qty':   total_used_qty,
        # Stock summary
        'total_materials': total_materials,
        'low_stock_items': low_stock_items,
        'out_of_stock':    out_of_stock,
        'normal_stock':    normal_stock,
        # Tables
        'top_materials':    top_materials,
        'user_breakdown':   user_breakdown,
        'recent_requests':  recent_requests,
        'low_stock_list':   low_stock_list,
        # Chart data (serialised for JS)
        'chart_labels_json':   _json.dumps(chart_labels),
        'chart_approved_json': _json.dumps(chart_approved),
        'chart_pending_json':  _json.dumps(chart_pending),
        'chart_rejected_json': _json.dumps(chart_rejected),
        'cat_labels_json':     _json.dumps(cat_labels),
        'cat_values_json':     _json.dumps(cat_values),
    }
    return render(request, 'inventory/reports.html', context)


@login_required
def reports_export_excel(request):
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    from_date = request.GET.get('from_date', (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date   = request.GET.get('to_date',   timezone.now().strftime('%Y-%m-%d'))
    try:
        start = datetime.strptime(from_date, '%Y-%m-%d').date()
        end   = datetime.strptime(to_date,   '%Y-%m-%d').date()
    except ValueError:
        start = (timezone.now() - timezone.timedelta(days=30)).date()
        end   = timezone.now().date()

    requests_qs = MaterialRequest.objects.filter(
        requested_at__date__gte=start,
        requested_at__date__lte=end
    ).select_related('material', 'requester').order_by('-requested_at')
    if role == 'Branch':
        requests_qs = requests_qs.filter(requester=request.user)

    wb = openpyxl.Workbook()

    # ── Helper styles ─────────────────────────────────────────────────────────
    h_fill   = PatternFill('solid', fgColor='4F46E5')
    h_font   = Font(color='FFFFFF', bold=True, size=11)
    h_align  = Alignment(horizontal='center', vertical='center')
    thin     = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB'),
    )
    alt_fill = PatternFill('solid', fgColor='F5F3FF')

    def style_header_row(ws, headers, col_widths):
        ws.append(headers)
        for col_idx, width in enumerate(col_widths, 1):
            cell = ws.cell(row=ws.max_row, column=col_idx)
            cell.fill    = h_fill
            cell.font    = h_font
            cell.alignment = h_align
            cell.border  = thin
            ws.column_dimensions[get_column_letter(col_idx)].width = width

    def style_data_rows(ws, start_row):
        for row_idx, row in enumerate(ws.iter_rows(min_row=start_row, max_row=ws.max_row), 1):
            fill = PatternFill('solid', fgColor='F5F3FF') if row_idx % 2 == 0 else PatternFill('solid', fgColor='FFFFFF')
            for cell in row:
                cell.border    = thin
                cell.fill      = fill
                cell.alignment = Alignment(vertical='center')

    # ── Sheet 1: Material Requests ────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = 'Material Requests'
    ws1.row_dimensions[1].height = 22

    # Title row
    ws1.merge_cells('A1:G1')
    title_cell = ws1['A1']
    title_cell.value     = f'ISP Inventory — Material Requests Report  ({from_date}  →  {to_date})'
    title_cell.font      = Font(bold=True, size=13, color='1E1B4B')
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws1.row_dimensions[1].height = 28
    ws1.append([])  # blank

    headers = ['Date', 'Requester', 'Material', 'Category', 'Qty', 'Type', 'Status']
    widths  = [14, 22, 28, 16, 8, 12, 12]
    style_header_row(ws1, headers, widths)

    for req in requests_qs:
        ws1.append([
            req.requested_at.strftime('%Y-%m-%d'),
            req.requester.get_full_name() or req.requester.username,
            req.material.name,
            req.material.category,
            req.quantity,
            req.request_type,
            req.status,
        ])
    style_data_rows(ws1, start_row=4)

    # Status colour coding
    green  = PatternFill('solid', fgColor='D1FAE5')
    yellow = PatternFill('solid', fgColor='FEF9C3')
    red    = PatternFill('solid', fgColor='FEE2E2')
    for row in ws1.iter_rows(min_row=4, max_row=ws1.max_row):
        status_cell = row[6]
        if status_cell.value == 'Approved':
            status_cell.fill = green
            status_cell.font = Font(bold=True, color='065F46')
        elif status_cell.value == 'Pending':
            status_cell.fill = yellow
            status_cell.font = Font(bold=True, color='78350F')
        elif status_cell.value == 'Rejected':
            status_cell.fill = red
            status_cell.font = Font(bold=True, color='991B1B')

    # ── Sheet 2: Top Materials ────────────────────────────────────────────────
    ws2 = wb.create_sheet('Top Materials')
    ws2.merge_cells('A1:C1')
    ws2['A1'].value = 'Top Materials by Approved Qty'
    ws2['A1'].font  = Font(bold=True, size=12, color='1E1B4B')
    ws2['A1'].alignment = Alignment(horizontal='center')
    ws2.row_dimensions[1].height = 24
    ws2.append([])
    style_header_row(ws2, ['Material', 'Category', 'Total Approved Qty'], [30, 18, 22])
    top = (
        requests_qs.filter(status='Approved')
        .values('material__name', 'material__category')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:20]
    )
    for item in top:
        ws2.append([item['material__name'], item['material__category'], item['total_qty']])
    style_data_rows(ws2, start_row=4)

    # ── Sheet 3: User Summary ─────────────────────────────────────────────────
    ws3 = wb.create_sheet('User Summary')
    ws3.merge_cells('A1:F1')
    ws3['A1'].value = 'Per-User Request Summary'
    ws3['A1'].font  = Font(bold=True, size=12, color='1E1B4B')
    ws3['A1'].alignment = Alignment(horizontal='center')
    ws3.row_dimensions[1].height = 24
    ws3.append([])
    style_header_row(ws3, ['Username', 'Full Name', 'Total Requests', 'Approved', 'Pending', 'Qty Issued'], [18, 24, 16, 12, 12, 14])
    user_data = (
        requests_qs
        .values('requester__username', 'requester__first_name', 'requester__last_name')
        .annotate(
            total_req=Count('id'),
            approved=Count('id', filter=Q(status='Approved')),
            pending=Count('id', filter=Q(status='Pending')),
            qty_issued=Sum('quantity', filter=Q(status='Approved'))
        )
        .order_by('-approved')
    )
    for u in user_data:
        fn = f"{u['requester__first_name']} {u['requester__last_name']}".strip() or u['requester__username']
        ws3.append([
            u['requester__username'], fn,
            u['total_req'], u['approved'], u['pending'],
            u['qty_issued'] or 0,
        ])
    style_data_rows(ws3, start_row=4)

    # ── Sheet 4: Stock Status ─────────────────────────────────────────────────
    ws4 = wb.create_sheet('Stock Status')
    ws4.merge_cells('A1:D1')
    ws4['A1'].value = 'Current Stock Status'
    ws4['A1'].font  = Font(bold=True, size=12, color='1E1B4B')
    ws4['A1'].alignment = Alignment(horizontal='center')
    ws4.row_dimensions[1].height = 24
    ws4.append([])
    style_header_row(ws4, ['Material', 'Category', 'Quantity', 'Status'], [30, 18, 12, 14])
    for mat in Material.objects.order_by('status', 'name'):
        ws4.append([mat.name, mat.category, mat.quantity, mat.status])
    style_data_rows(ws4, start_row=4)
    for row in ws4.iter_rows(min_row=4, max_row=ws4.max_row):
        sc = row[3]
        if sc.value == 'Normal':
            sc.fill = green;  sc.font = Font(bold=True, color='065F46')
        elif sc.value == 'Low Stock':
            sc.fill = yellow; sc.font = Font(bold=True, color='78350F')
        elif sc.value == 'Out of Stock':
            sc.fill = red;    sc.font = Font(bold=True, color='991B1B')

    # ── Freeze top rows & return ──────────────────────────────────────────────
    for ws in [ws1, ws2, ws3, ws4]:
        ws.freeze_panes = 'A4'

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"isp_report_{from_date}_to_{to_date}.xlsx"
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def reports_export_pdf(request):
    """Export the current report as a PDF file using xhtml2pdf."""
    from xhtml2pdf import pisa
    from io import BytesIO
    from django.db.models import Count

    profile = ensure_userprofile(request.user)
    role    = profile.role if profile else 'Branch'

    from_date = request.GET.get('from_date', (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date   = request.GET.get('to_date',   timezone.now().strftime('%Y-%m-%d'))
    try:
        start = datetime.strptime(from_date, '%Y-%m-%d').date()
        end   = datetime.strptime(to_date,   '%Y-%m-%d').date()
    except ValueError:
        start = (timezone.now() - timezone.timedelta(days=30)).date()
        end   = timezone.now().date()

    requests_qs = MaterialRequest.objects.filter(
        requested_at__date__gte=start,
        requested_at__date__lte=end
    ).select_related('material', 'requester').order_by('-requested_at')
    if role == 'Branch':
        requests_qs = requests_qs.filter(requester=request.user)

    total_requests   = requests_qs.count()
    approved_count   = requests_qs.filter(status='Approved').count()
    pending_count    = requests_qs.filter(status='Pending').count()
    rejected_count   = requests_qs.filter(status='Rejected').count()
    total_qty_issued = requests_qs.filter(status='Approved').aggregate(total=Sum('quantity'))['total'] or 0

    top_materials = (
        requests_qs.filter(status='Approved')
        .values('material__name', 'material__category')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:15]
    )

    context = {
        'from_date': from_date, 'to_date': to_date,
        'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
        'generated_by': request.user.get_full_name() or request.user.username,
        'total_requests': total_requests, 'approved_count': approved_count,
        'pending_count': pending_count, 'rejected_count': rejected_count,
        'total_qty_issued': total_qty_issued,
        'requests_qs': requests_qs[:100],
        'top_materials': top_materials,
        'low_stock_list': Material.objects.filter(status__in=['Low Stock', 'Out of Stock']).order_by('status', 'name'),
    }

    html_string = render(request, 'inventory/report_pdf.html', context).content.decode('utf-8')
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse('PDF generation error', status=500)
    buffer.seek(0)
    filename = f"isp_report_{from_date}_to_{to_date}.pdf"
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def settings_view(request):
    # Ensure role groups exist
    ROLE_GROUPS = ['Admin', 'Storekeeper', 'Branch', 'NOC']
    for r in ROLE_GROUPS:
        Group.objects.get_or_create(name=r)

    # Admin access: allow either UserProfile role==Admin or membership in Admin group
    try:
        is_admin_profile = (request.user.userprofile.role == 'Admin')
    except Exception:
        is_admin_profile = False

    is_admin_group = request.user.groups.filter(name='Admin').exists()
    if not (is_admin_profile or is_admin_group):
        messages.error(request, "Only Admins can access Settings!")
        return redirect('dashboard')

    # Use User queryset for compatibility with existing template which expects User objects
    users = User.objects.all().select_related('userprofile')
    default_group = Group.objects.get(name='Branch')
    # Ensure every user has a UserProfile and at least one role-group
    for u in users:
        # create UserProfile if missing, prefilling role from first role-group if available
        try:
            ensure_userprofile(u)
        except Exception:
            # best effort; continue
            pass
        # ensure at least one role-group assigned
        if not u.groups.filter(name__in=ROLE_GROUPS).exists():
            u.groups.add(default_group)
    system_settings = SystemSetting.objects.all()

    # Notification form for current user
    notif_obj, _ = NotificationSetting.objects.get_or_create(user=request.user)
    notif_form = NotificationSettingForm(instance=notif_obj)

    setting_form = SystemSettingForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        
        
        if action == 'update_notifications':
            form = NotificationSettingForm(request.POST, instance=notif_obj)
            if form.is_valid():
                form.save()
                messages.success(request, "Notification preferences updated!")

        elif action == 'backup':
            output = StringIO()
            call_command('dumpdata', exclude=['auth.permission', 'contenttypes'], stdout=output)
            response = HttpResponse(output.getvalue(), content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="isp_backup_{}.json"'.format(
                timezone.now().strftime('%Y%m%d_%H%M%S')
            )
            return response

        # Role change: update groups and (optionally) UserProfile for compatibility
        elif action == 'change_role':
            user_id = request.POST.get('user_id')
            new_role = request.POST.get('role') or request.POST.get('new_role')
            if user_id and new_role:
                user = User.objects.get(id=user_id)
                # ensure group exists
                grp, _ = Group.objects.get_or_create(name=new_role)
                # remove existing role groups
                for rn in ROLE_GROUPS:
                    g = Group.objects.filter(name=rn).first()
                    if g and g in user.groups.all():
                        user.groups.remove(g)
                user.groups.add(grp)
                # update UserProfile if exists
                try:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.role = new_role
                    profile.save()
                except Exception:
                    pass
                messages.success(request, f"Role updated for {user.username}")

        # Group management: create/delete groups, add/remove members
        elif action == 'create_group':
            group_name = request.POST.get('group_name', '').strip()
            if group_name:
                grp, created = Group.objects.get_or_create(name=group_name)
                if created:
                    messages.success(request, f"Group '{group_name}' created!")
                else:
                    messages.warning(request, f"Group '{group_name}' already exists.")
            else:
                messages.error(request, "Group name cannot be empty.")

        elif action == 'delete_group':
            group_id = request.POST.get('group_id')
            if group_id:
                try:
                    grp = Group.objects.get(id=group_id)
                    if grp.name in ROLE_GROUPS:
                        messages.error(request, "Cannot delete built-in role groups.")
                    else:
                        grp.delete()
                        messages.success(request, f"Group '{grp.name}' deleted!")
                except Group.DoesNotExist:
                    messages.error(request, "Group not found.")

        elif action == 'add_user_to_group':
            user_id = request.POST.get('user_id')
            group_id = request.POST.get('group_id')
            try:
                user = User.objects.get(id=user_id)
                grp = Group.objects.get(id=group_id)
                user.groups.add(grp)
                messages.success(request, f"User {user.username} added to group {grp.name}!")
            except (User.DoesNotExist, Group.DoesNotExist):
                messages.error(request, "User or group not found.")

        elif action == 'remove_user_from_group':
            user_id = request.POST.get('user_id')
            group_id = request.POST.get('group_id')
            try:
                user = User.objects.get(id=user_id)
                grp = Group.objects.get(id=group_id)
                user.groups.remove(grp)
                messages.success(request, f"User {user.username} removed from group {grp.name}!")
            except (User.DoesNotExist, Group.DoesNotExist):
                messages.error(request, "User or group not found.")

        elif action == 'delete_user':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user.is_superuser:
                    messages.error(request, "Cannot delete superuser accounts.")
                else:
                    user.delete()
                    messages.success(request, f"User {user.username} deleted.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")

        return redirect('settings')

    context = {
        'users': users,
        'groups': Group.objects.all(),
        'system_settings': system_settings,
        'setting_form': setting_form,
        'notif_form': notif_form,
    }
    return render(request, 'inventory/settings.html', context)


@login_required
def used_materials_view(request):
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    # Determine which used materials to display based on role
    if role == 'Branch':
        used_materials_qs = UsedMaterial.objects.filter(technician=request.user).order_by('-added_at')
    else:
        # Admin/Storekeeper see all used materials
        used_materials_qs = UsedMaterial.objects.all().order_by('-added_at')

    # Pagination
    paginator = Paginator(used_materials_qs, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    used_materials_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # BRANCH USER ACTIONS: create, edit, delete
        if action == 'create':
            if role != 'Branch':
                messages.error(request, "Only Branch users can add Used Materials.")
                return redirect('used_materials')
            
            form = UsedMaterialForm(request.POST, user=request.user)
            if form.is_valid():
                # Additional security check: Verify material is approved for this Branch
                material = form.cleaned_data.get('material')
                
                approved_material_ids = MaterialRequest.objects.filter(
                    requester=request.user,
                    material__status='Normal',
                    status='Approved'
                ).values_list('material', flat=True).distinct()
                
                if material and material.id in approved_material_ids:
                    um = form.save(commit=False)
                    um.technician = request.user
                    um.status = 'Pending'  # Set initial status to Pending - quantity won't be deducted until approved
                    um.save()
                    messages.success(request, "Used Material recorded successfully! Awaiting Admin approval.")
                    return redirect('used_materials')
                else:
                    messages.error(request, "You can only record usage for approved materials.")
                    return redirect('used_materials')
            else:
                messages.error(request, "Invalid data received. Please check the form.")
                
        elif action == 'edit':
            if role != 'Branch':
                messages.error(request, "Only Branch users can edit used materials.")
                return redirect('used_materials')
                
            um_id = request.POST.get('um_id')
            try:
                um = UsedMaterial.objects.get(pk=um_id, technician=request.user)
                form = UsedMaterialForm(request.POST, instance=um, user=request.user)
                if form.is_valid():
                    # Additional security check: Verify material is approved for this Branch
                    material = form.cleaned_data.get('material')
                    
                    approved_material_ids = MaterialRequest.objects.filter(
                        requester=request.user,
                        material__status='Normal',
                        status='Approved'  # Ensure material request was approved
                    ).values_list('material', flat=True).distinct()
                    
                    if material and material.id in approved_material_ids:
                        updated_um = form.save(commit=False)
                        updated_um.save()
                        messages.success(request, "Used Material updated successfully.")
                        return redirect('used_materials')
                    else:
                        messages.error(request, "You can only use approved materials.")
                        return redirect('used_materials')
                else:
                    messages.error(request, "Invalid data. Please check the form.")
            except UsedMaterial.DoesNotExist:
                messages.error(request, "Record not found or access denied.")
            return redirect('used_materials')
        
        elif action == 'delete':
            if role != 'Branch':
                messages.error(request, "Only Branch users can delete used materials.")
                return redirect('used_materials')
                
            um_id = request.POST.get('um_id')
            try:
                um = UsedMaterial.objects.get(pk=um_id, technician=request.user)
                um.delete()
                messages.success(request, "Used Material deleted successfully.")
            except UsedMaterial.DoesNotExist:
                messages.error(request, "Record not found or access denied.")
            return redirect('used_materials')
        
        # BRANCH USER ACTIONS: accept, reject (only Branch can accept/reject their own materials)
        elif action == 'accept':
            if role != 'Branch':
                messages.error(request, "Permission denied. Only Branch users can approve their own used materials.")
                return redirect('used_materials')
            
            um_id = request.POST.get('um_id')
            
            try:
                used_material = UsedMaterial.objects.get(pk=um_id, technician=request.user)
                
                # Only accept if status is Pending
                if used_material.status != 'Pending':
                    messages.warning(request, f"Can only approve 'Pending' used materials. Current status: {used_material.status}")
                    return redirect('used_materials')
                
                # Perform atomic transaction for approval
                try:
                    with transaction.atomic():
                        # Get material with lock to prevent race condition
                        material = Material.objects.select_for_update().get(pk=used_material.material.id)
                        
                        # Only deduct from material if status is 'Normal'
                        if material.status == 'Normal':
                            if material.quantity < used_material.quantity:
                                messages.error(
                                    request, 
                                    f"Insufficient stock. Available: {material.quantity}, Used: {used_material.quantity}"
                                )
                                return redirect('used_materials')
                            
                            # Deduct the quantity
                            material.quantity -= used_material.quantity
                            material.save()  # save() will update status if needed
                            
                            # Update used material status
                            used_material.status = 'Accepted'
                            used_material.save()
                            
                            messages.success(
                                request, 
                                f"Used material approved. {used_material.quantity} units deducted from {material.name}."
                            )
                        else:
                            messages.error(
                                request, 
                                f"Cannot approve used material. Material status is {material.status}. Only Normal stock materials can be used."
                            )
                            return redirect('used_materials')
                except Exception as e:
                    messages.error(request, f"Error during approval: {str(e)}")
                    return redirect('used_materials')
            
            except UsedMaterial.DoesNotExist:
                messages.error(request, "Record not found or access denied.")
            return redirect('used_materials')
        
        elif action == 'reject':
            if role != 'Branch':
                messages.error(request, "Permission denied. Only Branch users can reject their own used materials.")
                return redirect('used_materials')
            
            um_id = request.POST.get('um_id')
            
            try:
                used_material = UsedMaterial.objects.get(pk=um_id, technician=request.user)
                
                if used_material.status == 'Rejected':
                    messages.warning(request, "This record is already rejected.")
                    return redirect('used_materials')
                
                # If previously accepted, return the quantity to material stock
                try:
                    with transaction.atomic():
                        if used_material.status == 'Accepted':
                            # Material was deducted, so return it
                            material = Material.objects.select_for_update().get(pk=used_material.material.id)
                            material.quantity += used_material.quantity
                            material.save()  # save() will update status if needed
                            
                            messages.success(
                                request, 
                                f"Used material rejected. {used_material.quantity} units returned to {material.name}."
                            )
                        else:
                            messages.info(request, "Used material rejected.")
                        
                        # Update used material status
                        used_material.status = 'Rejected'
                        used_material.save()
                except Exception as e:
                    messages.error(request, f"Error during rejection: {str(e)}")
                    return redirect('used_materials')
            
            except UsedMaterial.DoesNotExist:
                messages.error(request, "Record not found or access denied.")
            return redirect('used_materials')

    else:
        form = UsedMaterialForm(user=request.user) if role == 'Branch' else None

    # Determine selected_used_material and for_approval flags for modal display
    selected_used_material = None
    for_approval = False
    um_id = request.GET.get('um_id')
    if um_id and role in ['Admin', 'Storekeeper']:
        try:
            selected_used_material = UsedMaterial.objects.get(pk=um_id)
            for_approval = True
        except UsedMaterial.DoesNotExist:
            pass

    return render(request, 'inventory/used_materials.html', {
        'used_materials': used_materials_page,
        'form': form,
        'role': role,
        'page_obj': used_materials_page,
        'selected_used_material': selected_used_material,
        'for_approval': for_approval,
    })

@login_required
def get_used_material_api(request, pk):
    """API endpoint to get used material data for editing via AJAX"""
    try:
        used_material = UsedMaterial.objects.get(pk=pk, technician=request.user)
    except UsedMaterial.DoesNotExist:
        return JsonResponse({'error': 'Record not found or access denied'}, status=404)

    data = {
        'id': used_material.id,
        'material': used_material.material.id,
        'client_name': used_material.client_name or '',
        'client_phone': used_material.client_phone or '',
        'client_address': used_material.client_address or '',
        'quantity': used_material.quantity,
        'issue': used_material.issue or '',
        'status': used_material.status,
    }
    return JsonResponse(data)

@login_required
def pending_requests_api(request):
    """
    API endpoint to fetch pending requests with count and ordering.
    Returns JSON data with:
    - List of pending material requests ordered by requested_at (newest first)
    - Total count of pending requests
    - Count of pending requests by user
    """
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'
    
    try:
        # Get pending requests ordered by most recent first
        pending_requests = MaterialRequest.objects.filter(
            status='Pending'
        ).select_related('requester', 'material').order_by('-requested_at')
        
        # For non-admin users, optionally filter to their own requests
        show_all = request.GET.get('show_all', 'true').lower() == 'true'
        if not show_all and role == 'Branch':
            pending_requests = pending_requests.filter(requester=request.user)
        
        # Pagination
        page_size = int(request.GET.get('page_size', 10))
        page_number = int(request.GET.get('page', 1))
        
        paginator = Paginator(pending_requests, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Build request data
        requests_data = []
        for req in page_obj:
            requests_data.append({
                'id': req.id,
                'requester': req.requester.get_full_name() or req.requester.username,
                'requester_username': req.requester.username,
                'material_name': req.material.name,
                'material_id': req.material.id,
                'quantity': req.quantity,
                'requested_at': req.requested_at.isoformat(),
                'requested_at_display': req.requested_at.strftime('%Y-%m-%d %H:%M'),
                'status': req.status,
                'notes': req.notes or '',
            })
        
        # Return JSON response with metadata
        return JsonResponse({
            'success': True,
            'data': requests_data,
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_number,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# Custom 404 handler
def custom_404_view(request, exception=None):
    """Render a beautiful custom 404 page."""
    context = {
        'request_path': request.path,
    }
    return render(request, '404.html', context, status=404)