from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .forms import RegisterForm, MaterialForm, TaskForm, RequestForm, SystemSettingForm, NotificationSettingForm, UsedMaterialForm
from .models import Material, Task, MaterialRequest, UserProfile, SystemSetting, NotificationSetting, UsedMaterial
from .utils import ensure_userprofile
from django.db.models import Sum, Q, F
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
import json
from io import StringIO
from django.core.paginator import Paginator
import requests

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure role groups exist and add user to selected group
            role = form.cleaned_data.get('role')
            for r in ['Admin', 'Storekeeper', 'Branch', 'NOC']:
                Group.objects.get_or_create(name=r)
            if role:
                grp = Group.objects.get(name=role)
                user.groups.add(grp)
            # Create the associated UserProfile for the new user
            try:
                ensure_userprofile(user)
            except Exception:
                pass
            login(request, user)
            messages.success(request, "Account created!")
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
    all_materials = None
    
    if role == 'Branch':
        # For Branch: Get approved MaterialRequest objects with Normal stock status only
        technician_approved_materials = MaterialRequest.objects.filter(
            requester=request.user,
            status='Approved',
            material__status='Normal'  # Only show materials with Normal stock status
        ).select_related('material').order_by('-requested_at')
    else:
        # For Admin & Storekeeper: Get all materials
        all_materials = Material.objects.all().order_by('-added_at')
    
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

    # Admin specific stats
    total_users = 0
    if role == 'Admin':
        total_users = User.objects.count()

    return render(request, 'inventory/dashboard.html', {
        'total_materials': total_materials,
        'active_tasks': active_tasks,
        'pending_requests': pending_requests,
        'all_materials': all_materials,
        'technician_approved_materials': technician_approved_materials,
        'all_tasks': all_tasks,
        'all_requests': all_requests,
        'all_used_materials': all_used_materials,
        'role': role,
        'user': request.user,
        'my_stock_count': my_stock_count,
        'used_materials_count': used_materials_count,
        'used_material_form': used_material_form,
        'total_users': total_users,
    })


@login_required
def materials_view(request):
    # Base queryset
    materials = Material.objects.all()
    # Materials count normal/Low stock/Out of stock
    total_normal_stock = Material.objects.filter(status='Normal').count()
    total_low_stock = Material.objects.filter(status='Low Stock').count()
    total_out_of_stock = Material.objects.filter(status='Out of Stock').count()

    # Ensure a UserProfile exists and read role
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    #Pagination added
    paginator = Paginator(materials,10)  # Show 10 materials per page
    page_number = request.GET.get('page')
    materials_page = paginator.get_page(page_number)

    #search name,categoty,status
    search = request.GET.get('search', '').strip()
    if search:
        materials = materials.filter(
            Q(name__icontains=search) | Q(category__icontains=search) | Q(status__icontains=search)
        )

    #Filter by category and stock_status    
    category = request.GET.get('category', '')
    stock_status = request.GET.get('stock_status', '')
    if category:
        materials = materials.filter(category=category)
    if stock_status:
        # Map user-friendly status values to DB values
        status_map = {
            'low': 'Low Stock',
            'normal': 'Normal',
            'out_of_stock': 'Out of Stock'
        }
        db_status = status_map.get(stock_status, stock_status)
        materials = materials.filter(status=db_status)
    
    # Branch: only see their own rows (added_by stored as username)
    if role == 'Branch':
        materials = materials.filter(added_by=request.user.username)

    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        action = request.POST.get('action')

        # Delete action
        if action == 'delete' and role in ['Storekeeper', 'Branch']:
            material = get_object_or_404(Material, id=material_id)
            if role == 'Branch' and material.added_by != request.user.username:
                messages.error(request, "You can only delete your own materials!")
            else:
                material.delete()
                messages.success(request, "Material deleted!")
            return redirect('materials')

        # Branch 'use material' action (atomic, race-safe)
        if action == 'use_material':
            qty = request.POST.get('use_quantity')
            try:
                qty = int(qty)
            except (TypeError, ValueError):
                messages.error(request, "Invalid quantity specified.")
                return redirect('materials')

            # Role check (use profile computed above)
            if role != 'Branch':
                messages.error(request, "Only Branch users can use materials this way.")
                return redirect('materials')

            if qty <= 0:
                messages.error(request, "Quantity must be a positive integer.")
                return redirect('materials')

            # Use F-expression update to decrement safely
            try:
                with transaction.atomic():
                    updated = Material.objects.filter(pk=material_id, quantity__gte=qty).update(quantity=F('quantity') - qty)
                    if updated == 0:
                        messages.error(request, "Not enough stock to use that quantity or material not found.")
                        return redirect('materials')
                    # Refresh to show new value in message
                    mat = Material.objects.get(pk=material_id)
                    # Ensure status is recalculated by calling save() (update() bypasses save())
                    try:
                        mat.save()
                    except Exception:
                        # If save fails for some reason, continue and show quantity
                        pass
                    messages.success(request, f"Used {qty} of '{mat.name}'. New quantity: {mat.quantity}")
                    return redirect('materials')
            except Exception:
                messages.error(request, "An error occurred while updating stock. Try again.")
                return redirect('materials')
            
             # Add/edit material
        # Material model duplicate name not allowed massages show
        
        instance = None
        if material_id and material_id != 'undefined' and material_id.isdigit():
            instance = get_object_or_404(Material, id=material_id)
        
        form = MaterialForm(request.POST, user=request.user, instance=instance)
        if form.is_valid():
            material = form.save(commit=False)
            is_new = not material.id
            
            # Permission check: Only Storekeepers and Admins can add/edit
            if role not in ['Storekeeper', 'Admin']:
                messages.error(request, "Permission denied. Only Storekeepers can add or edit materials.")
                return redirect('materials')

            if is_new:
                material.added_by = request.user.username

            # Storekeepers may only update their own materials
            if not is_new and role == 'Storekeeper' and material.added_by != request.user.username:
                messages.error(request, "You can only update your own materials!")
                return redirect('materials')
            material.save()
            messages.success(request, "Material saved!")
            #Material model duplicate name not allowed massages show
            return redirect('materials')
        else:
            messages.error(request, "Material name already exists!")
            return redirect('materials')
    # render
    form = MaterialForm(user=request.user)
    context = {
        'category': category,
        'total_normal_stock': total_normal_stock,
        'total_low_stock': total_low_stock,
        'total_out_of_stock': total_out_of_stock,
        'stock_status': stock_status,
        'materials': materials,
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

    # Basic permission: Branch should only fetch their own materials
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'
    if role == 'Branch' and mat.added_by != request.user.username:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    data = {
        'name': mat.name,
        'category': mat.category,
        'quantity': mat.quantity,
        'min_stock_level': mat.min_stock_level,
        'notes': mat.notes or '',
        'added_by': mat.added_by or '',
    }
    return JsonResponse(data)

@login_required
@login_required
def tasks_view(request):
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'

    if role == 'Branch':
        tasks = Task.objects.filter(technician=request.user).order_by('-created_at')
    else:
        tasks = Task.objects.all().order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            if role == 'Branch':
                 messages.error(request, "Branch users cannot create tasks.")
                 return redirect('tasks')
            form = TaskForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Task created!")
                return redirect('tasks')
        
        elif action == 'update_status':
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('status')
            try:
                task = Task.objects.get(pk=task_id)
                # Permission check
                if role == 'Branch' and task.requester != request.user:
                    messages.error(request, "Permission denied.")
                else:
                    task.status = new_status
                    task.save()
                    messages.success(request, f"Task status updated to {new_status}")
            except Task.DoesNotExist:
                messages.error(request, "Task not found.")
            return redirect('tasks')

        elif action == 'delete':
            if role != 'Admin':
                messages.error(request, "Only Admins can delete tasks.")
                return redirect('tasks')
            task_id = request.POST.get('task_id')
            try:
                task = Task.objects.get(pk=task_id)
                task.delete()
                messages.success(request, "Task deleted.")
            except Task.DoesNotExist:
                messages.error(request, "Task not found.")
            return redirect('tasks')

    else:
        form = TaskForm()
        
    return render(request, 'inventory/tasks.html', {'tasks': tasks.order_by('-created_at'), 'form': form, 'role': role})

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
    # Get users for dropdown
    users = User.objects.all() if role in ['Admin', 'Storekeeper'] else User.objects.filter(userprofile__role='Branch')

    # Search Logic - apply BEFORE pagination
    search_query = request.GET.get('search', '').strip()
    if search_query:
        base_requests = base_requests.filter(
            Q(material__name__icontains=search_query) | 
            Q(user_note__icontains=search_query) | 
            Q(notes__icontains=search_query) |
            Q(requester__username__icontains=search_query)
        )

    # Separate advance requests from regular requests
    advance_requests = base_requests.filter(admin_note__icontains='advance').order_by('-requested_at')
    regular_requests = base_requests.exclude(admin_note__icontains='advance').order_by('-requested_at')

    # Pagination applied AFTER filtering
    paginator = Paginator(regular_requests, 10)  # Show 10 requests per page
    page_number = request.GET.get('page')
    requests_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Create Request
        if action == 'create':
            if role in ['Admin', 'Storekeeper']:
                 messages.error(request, "Only Branch users can submit requests.")
                 return redirect('requests')

            form = RequestForm(request.POST)
            if form.is_valid():
                req = form.save(commit=False)
                req.requester = request.user
                req.save()
                messages.success(request, "Request submitted!")
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
        'advance_requests': advance_requests,
    })

@login_required
def reports_view(request):
    # Get filter parameters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    report_type = request.GET.get('type', 'all')

    # Default: last 30 days
    if not from_date:
        from_date = (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
    if not to_date:
        to_date = timezone.now().strftime('%Y-%m-%d')

    # Convert to date objects
    start = datetime.strptime(from_date, '%Y-%m-%d').date()
    end = datetime.strptime(to_date, '%Y-%m-%d').date()

    # Filter requests by date
    requests_qs = MaterialRequest.objects.filter(
        requested_at__date__gte=start,
        requested_at__date__lte=end
    )

    # Summary Stats
    total_used = requests_qs.filter(status='Approved').aggregate(total=Sum('quantity'))['total'] or 0
    total_requests = requests_qs.count()
    approved_count = requests_qs.filter(status='Approved').count()
    pending_count = requests_qs.filter(status='Pending').count()
    low_stock = Material.objects.filter(quantity__lt=10).count()

    # Recent requests for table
    recent_requests = requests_qs.order_by('-requested_at')[:20]

    context = {
        'total_used': total_used,
        'total_requests': total_requests,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'low_stock': low_stock,
        'recent_requests': recent_requests,
        'from_date': from_date,
        'to_date': to_date,
        'report_type': report_type,
    }
    return render(request, 'inventory/reports.html', context)


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

    #pagination added
    used_materials = UsedMaterial.objects.filter(technician=request.user).order_by('-added_at')
    paginator = Paginator(used_materials, 10)  # Show 10 records per page
    page_number = request.GET.get('page')

    # Strict permission: Only Branch users can access this page
    if role != 'Branch':
        messages.error(request, "Access restricted to Branch users only.")
        return redirect('dashboard')
    
    # Fetch UsedMaterial records for this Branch on approval data can import material request link
    used_materials = UsedMaterial.objects.filter(technician=request.user).order_by('-added_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        
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
                    material__status='Normal'
                ).values_list('material', flat=True).distinct() # Get list of approved material IDs for this Branch
                
                if material and material.id in approved_material_ids:
                    um = form.save(commit=False)
                    um.technician = request.user
                    um.save()
                    messages.success(request, "Used Material recorded successfully!")
                    return redirect('used_materials')
                else:
                    messages.error(request, "You can only record usage for approved materials.")
                    return redirect('used_materials')
            else:
                messages.error(request, "Invalid data received. Please check the form.")
                
        elif action == 'edit':
            um_id = request.POST.get('um_id')
            try:
                um = UsedMaterial.objects.get(pk=um_id, technician=request.user)
                form = UsedMaterialForm(request.POST, instance=um, user=request.user)
                if form.is_valid():
                    # Additional security check: Verify material is approved for this Branch
                    material = form.cleaned_data.get('material')
                    
                    approved_material_ids = MaterialRequest.objects.filter(
                        requester=request.user,
                        material__status='Normal'  # Ensure only Normal stock materials can be used
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
            um_id = request.POST.get('um_id')
            try:
                um = UsedMaterial.objects.get(pk=um_id, technician=request.user)
                um.delete()
                messages.success(request, "Used Material deleted successfully.")
            except UsedMaterial.DoesNotExist:
                messages.error(request, "Record not found or access denied.")
            return redirect('used_materials')

    else:
        form = UsedMaterialForm(user=request.user)

    return render(request, 'inventory/used_materials.html', {
        'used_materials': used_materials,
        'form': form,
        'role': role,
        'page_obj': page_number,
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
def manage_used_material(request, pk):
    """Admin approval view for used materials.
    
    Allows Admin/Storekeeper to:
    - View pending used material records
    - Approve them (deduct from material stock if Normal status)
    - Reject them with notes
    """
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Branch'
    
    # Permission check: Only Admin and Storekeeper can approve
    if role not in ['Admin', 'Storekeeper']:
        messages.error(request, "Permission denied. Only Admin and Storekeeper can approve used materials.")
        return redirect('dashboard')
    
    try:
        used_material = UsedMaterial.objects.get(pk=pk)
    except UsedMaterial.DoesNotExist:
        messages.error(request, "Record not found.")
        return redirect('used_materials')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '').strip()
        
        try:
            if action == 'accept':
                if used_material.status == 'Accepted':
                    messages.warning(request, "This record is already approved.")
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
                            used_material.admin_note = admin_note
                            used_material.save()
                            
                            messages.success(
                                request, 
                                f"Used material approved. {used_material.quantity} units deducted from {material.name} ({material.status})."
                            )
                        else:
                            # Material is Low Stock or Out of Stock - don't deduct but mark as accepted
                            used_material.status = 'Accepted'
                            used_material.admin_note = admin_note
                            used_material.save()
                            messages.warning(
                                request, 
                                f"Used material approved but NOT deducted (material status: {material.status})."
                            )
                except Exception as e:
                    messages.error(request, f"Error during approval: {str(e)}")
                    return redirect('used_materials')
                    
            elif action == 'reject':
                if used_material.status == 'Rejected':
                    messages.warning(request, "This record is already rejected.")
                    return redirect('used_materials')
                
                used_material.status = 'Rejected'
                used_material.admin_note = admin_note
                used_material.save()
                messages.success(request, "Used material rejected.")
                
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        
        return redirect('used_materials')
    
    # GET request - show confirmation form
    return render(request, 'inventory/manage_used_material.html', {
        'used_material': used_material,
        'role': role,
    })


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
