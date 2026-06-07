from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from rest_framework_simplejwt.tokens import RefreshToken
from isp_inventory.models import UserProfile, Material, MaterialRequest, UsedMaterial, InternalMessage, MacSerialNumber, MaterialMacSerialImport, RefundableMaterial, DamageMaterial
from isp_inventory.utils import deduct_material_stock, restore_material_stock
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.contrib.auth.password_validation import validate_password
from functools import wraps
import json as _json
from isp_inventory.views import process_month_end_reset

# Create your views here.

def noc_login_view(request):
    """NOC-only login page"""
    tab_id = request.GET.get('tab_id') or request.POST.get('tab_id')

    if request.method == "POST":
        user = authenticate(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )

        if user:
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.role != 'NOC':
                    messages.error(request, "Access denied. This login page is for NOC role only.")
                    return render(request, 'noc/login.html')
                
                if not user.is_active:
                    messages.error(request, "Your account is inactive. Please contact administrator.")
                    return render(request, 'noc/login.html')
                
                # User is NOC and active - proceed with login
                if not tab_id:
                    import uuid
                    tab_id = uuid.uuid4().hex[:8]

                request.tab_id = tab_id # Set for middleware to catch and append to redirect
                
                # Update profile activity status
                profile.is_active = True
                profile.last_login = timezone.now()
                profile.save(update_fields=['is_active', 'last_login'])
                
                response = redirect('noc:dashboard')
                from isp_inventory.views import _set_jwt_cookies
                _set_jwt_cookies(response, user, tab_id)
                return response
                
            except UserProfile.DoesNotExist:
                messages.error(request, "User profile not found. Please contact administrator.")
                return render(request, 'noc/login.html')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    
    return render(request, 'noc/login.html')

def noc_logout_view(request):
    """NOC logout"""
    response = redirect('noc:login')
    tab_id = getattr(request, 'tab_id', None)
    
    if tab_id:
        response.delete_cookie(f'jwt_access_{tab_id}')
        response.delete_cookie(f'jwt_refresh_{tab_id}')
    else:
        # Fallback: if tab_id is missing, try to clear all JWT cookies
        for cookie_name in list(request.COOKIES.keys()):
            if cookie_name.startswith('jwt_access_') or cookie_name.startswith('jwt_refresh_'):
                response.delete_cookie(cookie_name)
    
    # Update profile activity status to False on logout
    try:
        profile = request.user.userprofile
        profile.is_active = False
        profile.save(update_fields=['is_active'])
    except Exception:
        pass
    
    # Also clear session just in case
    logout(request)
    return response

def noc_role_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            if request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'NOC':
                return view_func(request, *args, **kwargs)
        except (AttributeError, UserProfile.DoesNotExist):
            pass
        messages.error(request, "Access denied. NOC role required.")
        return redirect('dashboard')
    return _wrapped_view

@login_required
@noc_role_required
def noc_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('req_id')
        if action and req_id:
            mat_request = get_object_or_404(MaterialRequest, pk=req_id, material__category='Internet', material__created_by=request.user)
            if action == 'accept':
                if mat_request.status == 'Approved':
                    messages.warning(request, f"Request for {mat_request.material.name} is already approved.")
                elif mat_request.material.quantity + mat_request.material.Remaining_stock >= mat_request.quantity:
                    with transaction.atomic():
                        deduct_material_stock(mat_request.material, mat_request.quantity)
                        mat_request.status = 'Approved'
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} approved.")
                else:
                    messages.error(request, f"Insufficient stock for {mat_request.material.name}.")
            elif action == 'reject':
                if mat_request.status == 'Approved':
                    with transaction.atomic():
                        restore_material_stock(mat_request.material, mat_request.quantity)
                        mat_request.status = 'Rejected'
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected and stock returned.")
                else:
                    mat_request.status = 'Rejected'
                    mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected.")
            return redirect('noc:dashboard')

    process_month_end_reset()
    now = timezone.now()
    internet_materials = Material.objects.filter(category='Internet', created_by=request.user)
    all_internet_materials = internet_materials.order_by('-added_at')
    
    # Standardized card counters
    # total_materials = internet_materials.aggregate(total=Sum('quantity'))['total'] or 0
    total_materials = internet_materials.count()
    pending_requests = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user, 
        status='Pending',
        is_archived=False,
        requested_at__year=now.year,
        requested_at__month=now.month,
    ).count()
    used_materials_count = UsedMaterial.objects.filter(
        material__category='Internet', 
        material__created_by=request.user,
        status='Accepted'
    ).count()
    low_stock_materials = internet_materials.filter(Q(status='Low Stock') | Q(status='Out of Stock')).count()
    
    # Internal Communication: unread messages
    unread_messages_count = InternalMessage.objects.filter(receiver=request.user, is_read=False).count()

    # Specific for NOC role: MAC/Serial count (materials with serial info)
    mac_serial_count = internet_materials.filter(
        Q(notes__icontains='MAC') | Q(notes__icontains='Serial') | Q(name__icontains='MAC') | Q(name__icontains='Serial')
    ).count()

    # Report Shortcuts: Current month stats
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_qty_issued = MaterialRequest.objects.filter(
        material__category='Internet',
        material__created_by=request.user,
        status='Approved',
        requested_at__gte=month_start
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    advance_count = MaterialRequest.objects.filter(
        material__category='Internet',
        material__created_by=request.user,
        request_type='Advance',
        is_archived=False,
        requested_at__gte=month_start
    ).count()

    total_used_qty = UsedMaterial.objects.filter(
        material__category='Internet',
        material__created_by=request.user,
        status='Accepted',
        added_at__gte=month_start
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # Context for modals
    total_users = UserProfile.objects.count()
    all_users_list = UserProfile.objects.select_related('user').order_by('-user__date_joined')
    
    pending_requests_list = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user, 
        status='Pending',
        is_archived=False,
        requested_at__year=now.year,
        requested_at__month=now.month,
    ).order_by('-requested_at')
    
    advance_materials = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user, 
        request_type='Advance',
        is_archived=False,
        requested_at__year=now.year,
        requested_at__month=now.month,
    ).order_by('-requested_at')
    
    materials_monitoring = MaterialRequest.objects.filter(
        material__category='Internet',
        material__created_by=request.user,
        status='Approved',
        is_hidden_by_noc=False
    ).select_related('material', 'requester').order_by('-requested_at')
    
    all_used_materials = UsedMaterial.objects.filter(
        material__category='Internet',
        material__created_by=request.user
    ).select_related('technician', 'material').order_by('-added_at')[:100]
    
    technician_approved_materials = MaterialRequest.objects.filter(
        status='Approved',
        material__category='Internet',
        material__created_by=request.user,
        is_hidden_by_noc=False
    ).select_related('material')

    low_stock_material_list = internet_materials.filter(
        Q(status='Low Stock') | Q(status='Out of Stock')
    ).order_by('status', 'name')

    # Today's Used Materials for NOC Dashboard (Paginated)
    today = timezone.now().date()
    today_used_materials_all = UsedMaterial.objects.filter(
        material__category='Internet',
        material__created_by=request.user,
        added_at__date=today
    ).select_related('technician', 'material').order_by('-added_at')

    paginator = Paginator(today_used_materials_all, 10)
    page_number = request.GET.get('page')
    try:
        today_used_materials = paginator.page(page_number)
    except PageNotAnInteger:
        today_used_materials = paginator.page(1)
    except EmptyPage:
        today_used_materials = paginator.page(paginator.num_pages)

    recent_requests = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user,
        is_hidden_by_noc=False
    ).order_by('-requested_at')[:5]

    refundable_materials = RefundableMaterial.objects.filter(branch_user__userprofile__role='Branch').select_related('branch_user').order_by('-added_at')
    damaged_materials = DamageMaterial.objects.filter(material__category='Internet', material__created_by=request.user).select_related('branch_user', 'material', 'confirmed_by').order_by('-added_at')
    branch_users = User.objects.select_related('userprofile').filter(userprofile__role='Branch').order_by('username')
    
    refundable_form = NocRefundableMaterialForm(noc_user=request.user)
    damaged_form = NocDamageMaterialForm(noc_user=request.user)

    #Total price
    total_price_agg1 = Material.objects.aggregate(total=Sum('total_price'))['total']
    total_price1 = total_price_agg1 if total_price_agg1 is not None else 0

    context = {
        'total_materials': total_materials,
        'pending_requests': pending_requests,
        'used_materials_count': used_materials_count,
        'low_stock_materials': low_stock_materials,
        'mac_serial_count': mac_serial_count,
        'unread_messages_count': unread_messages_count,
        'total_qty_issued': total_qty_issued,
        'advance_count': advance_count,
        'total_used_qty': total_used_qty,
        'total_users': total_users,
        'all_users_list': all_users_list,
        'pending_requests_list': pending_requests_list,
        'advance_materials': advance_materials,
        'materials_monitoring': materials_monitoring,
        'all_used_materials': all_used_materials,
        'technician_approved_materials': technician_approved_materials,
        'low_stock_material_list': low_stock_material_list,
        'today_used_materials': today_used_materials,
        'recent_requests': recent_requests,
        'all_materials': all_internet_materials,
        'refundable_materials': refundable_materials,
        'damaged_materials': damaged_materials,
        'branch_users': branch_users,
        'refundable_form': refundable_form,
        'damaged_form': damaged_form,
        'total_price1':total_price1,
        'role': 'NOC'
    }
    
    return render(request, 'noc/dashboard.html', context)

@login_required
@noc_role_required
def noc_materials(request):
    # Get search query from GET parameters
    search_query = request.GET.get('search', '').strip()
    
    # Base queryset - all Internet materials created by the NOC user
    materials_qs = Material.objects.filter(category='Internet', created_by=request.user).order_by('-added_at')
    
    # Apply search filter if provided
    if search_query:
        materials_qs = materials_qs.filter(
            Q(name__icontains=search_query) | 
            Q(notes__icontains=search_query)
        )
    
    # Calculate stock summary statistics dynamically based on quantity and min_stock_level
    all_materials = Material.objects.filter(category='Internet', created_by=request.user)
    
    total_normal_stock = 0
    total_low_stock = 0
    total_out_of_stock = 0
    
    for material in all_materials:
        if material.quantity <= 0:
            total_out_of_stock += 1
        elif material.quantity < (material.min_stock_level or 0):
            total_low_stock += 1
        else:
            total_normal_stock += 1
    
    # Pagination setup
    paginator = Paginator(materials_qs, 20)  # Show 10 materials per page
    page = request.GET.get('page', 1)
    
    try:
        materials = paginator.page(page)
    except PageNotAnInteger:
        materials = paginator.page(1)
    except EmptyPage:
        materials = paginator.page(paginator.num_pages)
    
    context = {
        'materials': materials,
        'search_query': search_query,
        'total_normal_stock': total_normal_stock,
        'total_low_stock': total_low_stock,
        'total_out_of_stock': total_out_of_stock,
        'paginator': paginator,
        'page_obj': materials,
    }
    
    return render(request, 'noc/materials.html', context)

@login_required
@noc_role_required
def add_material(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = int(request.POST.get('quantity', 0))
        rate = int(request.POST.get('rate', 0))
        min_stock = int(request.POST.get('min_stock_level', 0))
        total_price = quantity * rate
        
        Material.objects.create(
            name=name,
            category='Internet',
            quantity=quantity,
            rate = rate,
            total_price = total_price,
            Remaining_stock=quantity,
            min_stock_level=min_stock,
            created_by=request.user
        )
        messages.success(request, "Material added successfully.")
        return redirect('noc:materials')
    return render(request, 'noc/add_material.html')

@login_required
@noc_role_required
def edit_material(request, pk):
    material = get_object_or_404(Material, pk=pk, category='Internet', created_by=request.user)
    if request.method == 'POST':
        # NOC can only edit quantity and min_stock_level, NOT the name
        material.quantity = int(request.POST.get('quantity', material.quantity))
        material.rate = int(request.POST.get('rate', material.rate))
        material.min_stock_level = int(request.POST.get('min_stock_level', material.min_stock_level))
        material.total_price = material.quantity * material.rate
        material.save()
        messages.success(request, "Material updated successfully.")
        return redirect('noc:materials')
    return render(request, 'noc/edit_material.html', {'material': material})

@login_required
@noc_role_required
def delete_material(request, pk):
    material = get_object_or_404(Material, pk=pk, category='Internet', created_by=request.user)
    if request.method == 'POST':
        material.delete()
        messages.success(request, "Material deleted successfully.")
        return redirect('noc:materials')
    return render(request, 'noc/delete_confirm.html', {'material': material})

@login_required
@noc_role_required
def noc_requests(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('req_id')
        if action and req_id:
            mat_request = get_object_or_404(MaterialRequest, pk=req_id, material__category='Internet', material__created_by=request.user)
            if action == 'accept':
                if mat_request.status == 'Approved':
                    messages.warning(request, f"Request for {mat_request.material.name} is already approved.")
                    return redirect('noc:requests')
                    
                # Check for quantity modification from the modal
                requested_qty = mat_request.quantity
                try:
                    new_qty = int(request.POST.get('quantity', requested_qty))
                    if new_qty > 0:
                        requested_qty = new_qty
                except (ValueError, TypeError):
                    pass

                if mat_request.material.quantity + mat_request.material.Remaining_stock >= requested_qty:
                    with transaction.atomic():
                        deduct_material_stock(mat_request.material, requested_qty)
                        mat_request.quantity = requested_qty
                        mat_request.status = 'Approved'
                        mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} approved.")
                else:
                    messages.error(request, f"Insufficient stock for {mat_request.material.name}.")
            elif action == 'reject':
                if mat_request.status in ['Approved', 'Received']:
                    with transaction.atomic():
                        restore_material_stock(mat_request.material, mat_request.quantity)
                        mat_request.status = 'Rejected'
                        mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected and stock returned.")
                else:
                    mat_request.status = 'Rejected'
                    mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
                    mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected.")
            elif action == 'save_note':
                mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
                mat_request.save()
                messages.success(request, "Note updated successfully.")
            elif action == 'delete':
                if mat_request.status in ['Received', 'Dispatched']:
                    mat_request.is_hidden_by_noc = True
                    mat_request.save()
                    messages.success(request, "Request hidden from your view (Branch data preserved).")
                elif mat_request.status == 'Approved':
                    with transaction.atomic():
                        restore_material_stock(mat_request.material, mat_request.quantity)
                        mat_request.delete()
                    messages.success(request, "Request deleted and stock returned.")
                else:
                    mat_request.delete()
                    messages.success(request, "Request permanently deleted.")
        return redirect('noc:requests')

    # GET logic: searching and filtering
    search_query = request.GET.get('search', '')
    user_filter = request.GET.get('user', '')
    
    requests_qs = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user,
        is_hidden_by_noc=False
    )
    
    if search_query:
        requests_qs = requests_qs.filter(
            Q(material__name__icontains=search_query) | 
            Q(requester__username__icontains=search_query) |
            Q(send_by__icontains=search_query)
        )
    
    if user_filter:
        requests_qs = requests_qs.filter(requester_id=user_filter)
        
    requests_qs = requests_qs.select_related('material', 'requester').order_by('-requested_at')
    
    # Summary counts for the top cards
    pending_count = requests_qs.filter(status='Pending').count()
    approved_count = requests_qs.filter(status='Approved').count()
    rejected_count = requests_qs.filter(status='Rejected').count()
    received_count = requests_qs.filter(status='Received').count()
    
    # Pagination
    paginator = Paginator(requests_qs, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Unique list of branches who have made requests for NOC materials
    users_with_requests = User.objects.filter(
        material_requests__material__category='Internet', 
        material_requests__material__created_by=request.user
    ).distinct()
    
    context = {
        'requests': page_obj,
        'page_obj': page_obj,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'received_count': received_count,
        'users': users_with_requests,
        'role': 'NOC'
    }
    return render(request, 'noc/requests.html', context)

@login_required
@noc_role_required
def approve_request(request, pk):
    mat_request = get_object_or_404(MaterialRequest, pk=pk, material__category='Internet', material__created_by=request.user)
    if request.method == 'POST':
        if mat_request.status == 'Approved':
            messages.warning(request, "Request already approved.")
        elif mat_request.material.quantity + mat_request.material.Remaining_stock >= mat_request.quantity:
            with transaction.atomic():
                deduct_material_stock(mat_request.material, mat_request.quantity)
                mat_request.status = 'Approved'
                mat_request.save()
            messages.success(request, "Request approved.")
        else:
            messages.error(request, "Insufficient stock.")
    return redirect('noc:requests')

@login_required
@noc_role_required
def reject_request(request, pk):
    mat_request = get_object_or_404(MaterialRequest, pk=pk, material__category='Internet', material__created_by=request.user)
    if request.method == 'POST':
        if mat_request.status == 'Approved':
            with transaction.atomic():
                restore_material_stock(mat_request.material, mat_request.quantity)
                mat_request.status = 'Rejected'
                mat_request.save()
            messages.success(request, "Request rejected and stock returned.")
        else:
            mat_request.status = 'Rejected'
            mat_request.save()
            messages.success(request, "Request rejected.")
    return redirect('noc:requests')

@login_required
@noc_role_required
def noc_used_materials(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        used_id = request.POST.get('used_id')
        if action and used_id:
            used_mat = get_object_or_404(UsedMaterial, pk=used_id, material__created_by=request.user)
            if action == 'accept':
                if used_mat.status == 'Accepted':
                    messages.warning(request, "Usage record already accepted.")
                elif used_mat.material.quantity + used_mat.material.Remaining_stock >= used_mat.quantity:
                    with transaction.atomic():
                        deduct_material_stock(used_mat.material, used_mat.quantity)
                        used_mat.status = 'Accepted'
                        used_mat.admin_note = request.POST.get('admin_note', used_mat.admin_note)
                        used_mat.save()
                    messages.success(request, "Usage record accepted and stock deducted.")
                else:
                    messages.error(request, f"Insufficient stock for {used_mat.material.name}.")
            elif action == 'reject':
                if used_mat.status == 'Accepted':
                    with transaction.atomic():
                        restore_material_stock(used_mat.material, used_mat.quantity)
                        used_mat.status = 'Rejected'
                        used_mat.admin_note = request.POST.get('admin_note', used_mat.admin_note)
                        used_mat.save()
                    messages.success(request, "Usage record rejected and stock returned.")
                else:
                    used_mat.status = 'Rejected'
                    used_mat.admin_note = request.POST.get('admin_note', used_mat.admin_note)
                    used_mat.save()
                    messages.success(request, "Usage record rejected.")
            elif action == 'delete':
                used_mat.delete()
                messages.success(request, "Usage record deleted.")
        return redirect('noc:used_materials')

    # GET Logic
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    used_qs = UsedMaterial.objects.filter(
        material__category='Internet',
        material__created_by=request.user
    ).select_related('technician', 'material').order_by('-added_at')
    
    if search_query:
        used_qs = used_qs.filter(
            Q(material__name__icontains=search_query) |
            Q(technician__username__icontains=search_query) |
            Q(client_name__icontains=search_query)
        )
    
    if status_filter:
        used_qs = used_qs.filter(status=status_filter)
        
    # Stats
    total_count = used_qs.count()
    accepted_count = used_qs.filter(status='Accepted').count()
    pending_count = used_qs.filter(status='Pending').count()
    rejected_count = used_qs.filter(status='Rejected').count()
    
    # Pagination
    paginator = Paginator(used_qs, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Unique list of technicians/branches who have reported usage for NOC materials
    users_with_usage = User.objects.filter(
        used_materials__material__category='Internet',
        used_materials__material__created_by=request.user
    ).distinct()
    
    context = {
        'used_materials': page_obj,
        'page_obj': page_obj,
        'total_count': total_count,
        'accepted_count': accepted_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'search_query': search_query,
        'status_filter': status_filter,
        'users': users_with_usage,
        'role': 'NOC'
    }
    return render(request, 'noc/used_materials.html', context)

@login_required
@noc_role_required
def noc_materials_monitoring(request):
    """Real-time materials monitoring for NOC: branch users and used materials they added."""
    ws_scheme = 'wss' if request.scheme == 'https' else 'ws'
    ws_host = request.get_host()
    ws_path = '/ws/inventory/materials-monitoring/'
    ws_url = f'{ws_scheme}://{ws_host}{ws_path}'
    return render(request, 'noc/materials_monitoring.html', {
        'ws_url': ws_url,
    })

@login_required
@noc_role_required
def noc_reports(request):
    """Logic for NOC specific reports - only their own materials."""
    role = request.user.userprofile.role
    
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

    # ── Base queryset (NOC specific) ────────
    # We only care about materials created by THIS NOC user
    noc_materials_qs = Material.objects.filter(category='Internet', created_by=request.user)
    
    requests_qs = MaterialRequest.objects.filter(
        material__in=noc_materials_qs,
        requested_at__date__gte=start,
        requested_at__date__lte=end,
        is_hidden_by_noc=False
    ).select_related('material', 'requester')

    # ── Summary Stats ────────
    total_requests   = requests_qs.count()
    approved_count   = requests_qs.filter(status='Approved').count()
    pending_count    = requests_qs.filter(status='Pending').count()
    rejected_count   = requests_qs.filter(status='Rejected').count()
    total_qty_issued = requests_qs.filter(status='Approved').aggregate(total=Sum('quantity'))['total'] or 0
    advance_count    = requests_qs.filter(request_type='Advance').count()

    # Material stock summary
    total_materials  = noc_materials_qs.count()
    low_stock_items  = noc_materials_qs.filter(status='Low Stock').count()
    out_of_stock     = noc_materials_qs.filter(status='Out of Stock').count()
    normal_stock     = noc_materials_qs.filter(status='Normal').count()

    # Used materials in period
    used_qs = UsedMaterial.objects.filter(
        material__in=noc_materials_qs,
        added_at__date__gte=start,
        added_at__date__lte=end
    )
    total_used_records = used_qs.count()
    total_used_qty     = used_qs.aggregate(total=Sum('quantity'))['total'] or 0

    # ── Top 10 materials by approved quantity ────────
    top_materials = (
        requests_qs.filter(status='Approved')
        .values('material__name')
        .annotate(total_qty=Sum('quantity'), req_count=Count('id'))
        .order_by('-total_qty')[:10]
    )

    # ── Chart data: daily request counts ────────
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

    # Material category breakdown (For NOC, usually all Internet, but we show by individual material names for better visualization)
    category_data = (
        requests_qs.filter(status='Approved')
        .values('material__name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')
    )
    cat_labels = [d['material__name'] or 'Unknown' for d in category_data][:10]
    cat_values = [d['qty'] or 0 for d in category_data][:10]

    # ── Recent requests (up to 50 for table) ────────
    recent_requests = requests_qs.order_by('-requested_at')[:50]

    # ── Low-stock materials list ────────
    low_stock_list = noc_materials_qs.filter(
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
    return render(request, 'noc/reports.html', context)

@login_required
@noc_role_required
def noc_notifications(request):
    # This could be handled by a generic notification system if one exists,
    # but for now we can show recent activities or messages.
    messages_list = InternalMessage.objects.filter(receiver=request.user).order_by('-created_at')
    return render(request, 'noc/notifications.html', {'messages': messages_list})

@login_required
@noc_role_required
def noc_profile(request):
    user = request.user
    profile = user.userprofile

    if request.method == 'POST':
        # Update User fields
        if profile.role == 'Admin': # Admin role can change username
            new_username = request.POST.get('username')
            if new_username and new_username != user.username:
                if User.objects.filter(username=new_username).exists():
                    messages.error(request, "Username already exists.")
                else:
                    user.username = new_username

        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        # Profile fields
        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.zip_code = request.POST.get('zip_code', '')
        
        # Image handling
        if 'image' in request.FILES:
            image = request.FILES['image']
            if image.size > 2 * 1024 * 1024:
                messages.error(request, "Profile image must be under 2 MB.")
                return redirect('noc:profile')
            
            allowed = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
            if not image.name.lower().endswith(allowed):
                messages.error(request, "Allowed image formats: PNG, JPG, JPEG, WEBP, GIF.")
                return redirect('noc:profile')
                
            profile.image = image
            
        # Password handling
        password = request.POST.get('password')
        if password:
            try:
                validate_password(password, user)
                user.set_password(password)
                messages.success(request, "Password updated successfully.")
            except Exception as e:
                messages.error(request, f"Password error: {e}")

        user.save()
        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('noc:profile')

    return render(request, 'noc/profile.html', {'profile': profile})

def custom_404_view(request, exception=None):
    """Render a beautiful custom 404 page."""
    context = {
        'request_path': request.path,
    }
    return render(request, '404.html', context, status=404)


@login_required
@noc_role_required
def add_mac_serials(request):
    """NOC view to add Mac/Serial numbers for materials and assign to branch users"""
    from isp_inventory.forms import MacSerialImportForm
    
    # Check for request_id in GET to pre-populate
    request_id = request.GET.get('request_id')
    initial_data = {}
    if request_id:
        try:
            mat_req = MaterialRequest.objects.get(
                pk=request_id, 
                status='Approved',
                material__created_by__userprofile__role='NOC'
            )
            initial_data = {
                'assigned_to': mat_req.requester.id,
                'material': mat_req.id,
                'quantity': mat_req.quantity
            }
        except MaterialRequest.DoesNotExist:
            messages.warning(request, "Selected request not found or not approved.")

    if request.method == 'POST':
        form = MacSerialImportForm(request.POST, noc_user=request.user)
        if form.is_valid():
            # In the improved form, 'material' field now returns the MaterialRequest object
            mat_req = form.cleaned_data['material']
            assigned_to = form.cleaned_data['assigned_to']
            quantity = form.cleaned_data['quantity']
            
            try:
                material = mat_req.material
                
                # Double check that the requester matches the assigned_to
                if mat_req.requester != assigned_to:
                    messages.error(request, "Selected material request does not match the branch user.")
                else:
                    with transaction.atomic():
                        # Create the import record
                        import_record = MaterialMacSerialImport.objects.create(
                            material=material,
                            assigned_to=assigned_to,
                            noc_user=request.user,
                            total_quantity=quantity,
                            mac_serials_count=quantity,
                            status='Pending'
                        )
                        
                        # Store data in session for the next step
                        request.session['mac_serial_import_id'] = import_record.id
                        request.session['mac_serial_quantity'] = quantity
                        
                        messages.success(request, f"Import initialized for {material.name}. Please enter Mac/Serial numbers.")
                        return redirect('noc:edit_mac_serials', pk=import_record.id)
            except MaterialRequest.DoesNotExist:
                messages.error(request, "Invalid material request selected.")
            except Exception as e:
                messages.error(request, f"Error initializing import: {str(e)}")
    else:
        form = MacSerialImportForm(initial=initial_data, noc_user=request.user)
    
    return render(request, 'noc/add_mac_serials.html', {'form': form})


@login_required
@noc_role_required
def edit_mac_serials(request, pk):
    """Edit mac/serial numbers for an import"""
    import_record = get_object_or_404(MaterialMacSerialImport, pk=pk, noc_user=request.user)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get all mac/serial data from POST
                mac_serials_data = []
                for i in range(1, import_record.mac_serials_count + 1):
                    mac_serial = request.POST.get(f'mac_serial_{i}', '').strip()
                    quantity = request.POST.get(f'quantity_{i}', '1')
                    
                    if mac_serial:
                        mac_serials_data.append({
                            'mac_serial': mac_serial,
                            'quantity': int(quantity) if quantity.isdigit() else 1
                        })
                
                if not mac_serials_data:
                    messages.error(request, "Please enter at least one mac/serial number.")
                    return render(request, 'noc/edit_mac_serials.html', {
                        'import_record': import_record,
                        'mac_serials_range': range(1, import_record.mac_serials_count + 1)
                    })
                
                # Create MacSerialNumber records
                for data in mac_serials_data:
                    MacSerialNumber.objects.create(
                        material=import_record.material,
                        mac_serial=data['mac_serial'],
                        quantity=data['quantity'],
                        assigned_to=import_record.assigned_to,
                        added_by=request.user
                    )
                
                # Update import record
                import_record.status = 'Approved'
                import_record.approved_at = timezone.now()
                import_record.approved_by = request.user
                import_record.save()
                
                messages.success(request, f"Mac/Serial numbers added successfully for {import_record.material.name}!")
                return redirect('noc:list_mac_serials')
        except Exception as e:
            messages.error(request, f"Error saving mac/serial numbers: {str(e)}")
    
    context = {
        'import_record': import_record,
        'mac_serials_range': range(1, import_record.mac_serials_count + 1)
    }
    return render(request, 'noc/edit_mac_serials.html', context)


@login_required
@noc_role_required
def list_mac_serials(request):
    """View all Mac/Serial numbers managed by NOC"""
    mac_serials = MacSerialNumber.objects.filter(added_by=request.user).select_related('material', 'assigned_to').order_by('-created_at')
    
    # Filter by Branch User
    user_filter = request.GET.get('user_id')
    if user_filter:
        try:
            mac_serials = mac_serials.filter(assigned_to_id=int(user_filter))
        except (ValueError, TypeError):
            pass

    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        mac_serials = mac_serials.filter(
            Q(mac_serial__icontains=search_query) |
            Q(material__name__icontains=search_query) |
            Q(assigned_to__username__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(mac_serials, 20)
    page = request.GET.get('page')
    try:
        mac_serials_page = paginator.page(page)
    except PageNotAnInteger:
        mac_serials_page = paginator.page(1)
    except EmptyPage:
        mac_serials_page = paginator.page(paginator.num_pages)
    
    # Get all branch users for the dropdown filter
    branch_users = User.objects.filter(userprofile__role='Branch').order_by('username')
    
    # Summary statistics
    total_count = mac_serials.count()
    
    context = {
        'mac_serials': mac_serials_page,
        'search_query': search_query,
        'user_filter': user_filter,
        'branch_users': branch_users,
        'total_count': total_count,
        'page_title': 'Mac/Serial Numbers'
    }
    return render(request, 'noc/list_mac_serials.html', context)


@login_required
@noc_role_required
def delete_mac_serial(request, pk):
    """Delete a Mac/Serial number"""
    mac_serial = get_object_or_404(MacSerialNumber, pk=pk, added_by=request.user)
    
    if request.method == 'POST':
        material_name = mac_serial.material.name
        mac_serial.delete()
        messages.success(request, f"Mac/Serial number deleted for {material_name}.")
        return redirect('noc:list_mac_serials')
    
    return render(request, 'noc/confirm_delete_mac_serial.html', {'mac_serial': mac_serial})
    
@login_required
@noc_role_required
def get_branch_materials(request):
    """AJAX view to get approved NOC material requests for a branch user"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'User ID required'}, status=400)
        
    # Get approved requests for materials created by NOC role for this user
    requests = MaterialRequest.objects.filter(
        requester_id=user_id,
        status='Approved',
        material__created_by__userprofile__role='NOC'
    ).select_related('material')
    
    data = []
    for req in requests:
        data.append({
            'id': req.id,
            'material_name': req.material.name,
            'quantity': req.quantity,
            'date': req.requested_at.strftime('%Y-%m-%d'),
            'display_text': f"{req.material.name} (Approved: {req.quantity}) - {req.requested_at.strftime('%Y-%m-%d')}"
        })
        
    return JsonResponse({'materials': data})


# ── NOC Custom Forms for Refundable & Damaged Materials ───────────────────
from django import forms
from isp_inventory.models import RefundableMaterial, DamageMaterial

class NocRefundableMaterialForm(forms.ModelForm):
    branch_user = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='Branch').order_by('username'),
        label="Branch User",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
            'id': 'noc_id_branch_user'
        })
    )
    material_name = forms.CharField(
        label="Material Name",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
            'id': 'noc_id_material_name',
            'placeholder': 'Enter material name'
        })
    )

    class Meta:
        model = RefundableMaterial
        fields = ['branch_user', 'material_name', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
                'min': '1',
                'id': 'noc_id_quantity'
            }),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('noc_user', None)
        super().__init__(*args, **kwargs)


class NocDamageMaterialForm(forms.ModelForm):
    branch_user = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='Branch').order_by('username'),
        label="Branch User",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
            'id': 'noc_id_dm_branch_user'
        })
    )
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(category='Internet').order_by('name'),
        label="Material Name",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
            'id': 'noc_id_dm_material'
        })
    )

    class Meta:
        model = DamageMaterial
        fields = ['branch_user', 'material', 'quantity', 'damage_reason', 'mac_serial', 'status']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
                'min': '1',
                'id': 'noc_id_dm_quantity'
            }),
            'damage_reason': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
                'rows': 3,
                'placeholder': 'Reason for damage...',
                'id': 'noc_id_dm_reason'
            }),
            'mac_serial': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
                'id': 'noc_id_dm_mac_serial'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-midnight-950 dark:text-white dark:border-midnight-800',
                'id': 'noc_id_dm_status'
            })
        }

    def __init__(self, *args, **kwargs):
        self.noc_user = kwargs.pop('noc_user', None)
        super().__init__(*args, **kwargs)
        if self.noc_user:
            self.fields['material'].queryset = Material.objects.filter(category='Internet', created_by=self.noc_user).order_by('name')


# ── NOC Custom Views for Refundable & Damaged Materials ───────────────────

@login_required
@noc_role_required
def noc_log_refundable(request):
    messages.error(request, "Access denied. NOC role is not allowed to log refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_edit_refundable(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to edit refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_delete_refundable(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to delete refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_process_refundable(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to process refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_log_damaged(request):
    messages.error(request, "Access denied. NOC role is not allowed to log damaged materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_edit_damaged(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to edit damaged materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_delete_damaged(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to delete damaged materials directly.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_process_damaged(request, pk):
    dm = get_object_or_404(DamageMaterial, pk=pk, material__category='Internet', material__created_by=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '').strip()
        if action == 'confirm':
            dm.status = 'Confirmed'
            dm.confirmed_by = request.user
            dm.confirmed_at = timezone.now()
        elif action == 'reject':
            dm.status = 'Rejected'
        dm.admin_note = admin_note

        # Maintain serial status on review actions so rejected items return to available stock
        if dm.mac_serial:
            if action == 'confirm':
                dm.mac_serial.status = 'Retired'
            else:
                dm.mac_serial.status = 'Active'
            dm.mac_serial.save()

        dm.save()
        messages.success(request, f"Damaged material request has been {dm.status.lower()}.")
    return redirect('noc:dashboard')

@login_required
@noc_role_required
def noc_get_refundable_api(request, pk):
    rf = get_object_or_404(RefundableMaterial, pk=pk)
    return JsonResponse({
        'id': rf.id,
        'branch_user': rf.branch_user_id,
        'material_name': rf.material_name,
        'mac_serial': rf.mac_serial,
        'quantity': rf.quantity,
    })

@login_required
@noc_role_required
def noc_get_damaged_api(request, pk):
    dm = get_object_or_404(DamageMaterial, pk=pk, material__category='Internet', material__created_by=request.user)
    return JsonResponse({
        'id': dm.id,
        'branch_user': dm.branch_user_id,
        'material': dm.material_id,
        'quantity': dm.quantity,
        'damage_reason': dm.damage_reason,
        'severity': dm.severity,
        'status': dm.status,
        'admin_note': dm.admin_note
    })

@login_required
@noc_role_required
def noc_refundable_materials_view(request):
    refundable_qs = RefundableMaterial.objects.select_related('branch_user').order_by('-added_at')
    branch_users = User.objects.select_related('userprofile').filter(userprofile__role='Branch').order_by('username')
    
    selected_user_id = request.GET.get('user_id')
    if selected_user_id:
        try:
            selected_user = User.objects.select_related('userprofile').get(id=selected_user_id, userprofile__role='Branch')
            refundable_qs = refundable_qs.filter(branch_user=selected_user)
        except User.DoesNotExist:
            messages.error(request, 'Selected user not found.')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        refundable_qs = refundable_qs.filter(
            Q(material_name__icontains=search_query) |
            Q(branch_user__username__icontains=search_query) |
            Q(branch_user__first_name__icontains=search_query) |
            Q(branch_user__last_name__icontains=search_query)
        ).distinct()

    paginator = Paginator(refundable_qs, 20)
    page_number = request.GET.get('page')
    refundable_page = paginator.get_page(page_number)

    return render(request, 'noc/refundable_materials.html', {
        'refundable_materials': refundable_page,
        'role': 'NOC',
        'page_obj': refundable_page,
        'branch_users': branch_users,
        'search_query': search_query,
    })

@login_required
@noc_role_required
def noc_damaged_materials_view(request):
    damaged_qs = DamageMaterial.objects.filter(material__category='Internet', material__created_by=request.user).select_related('branch_user', 'material', 'confirmed_by').order_by('-added_at')
    branch_users = User.objects.select_related('userprofile').filter(userprofile__role='Branch').order_by('username')
    
    selected_user_id = request.GET.get('user_id')
    if selected_user_id:
        try:
            selected_user = User.objects.select_related('userprofile').get(id=selected_user_id, userprofile__role='Branch')
            damaged_qs = damaged_qs.filter(branch_user=selected_user)
        except User.DoesNotExist:
            messages.error(request, 'Selected user not found.')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        damaged_qs = damaged_qs.filter(
            Q(material__name__icontains=search_query) |
            Q(branch_user__username__icontains=search_query) |
            Q(branch_user__first_name__icontains=search_query) |
            Q(branch_user__last_name__icontains=search_query) |
            Q(damage_reason__icontains=search_query)
        ).distinct()

    paginator = Paginator(damaged_qs, 20)
    page_number = request.GET.get('page')
    damaged_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['confirm', 'reject']:
            dm_id = request.POST.get('dm_id')
            admin_note = request.POST.get('admin_note', '').strip()
            try:
                dm = DamageMaterial.objects.get(pk=dm_id, material__category='Internet', material__created_by=request.user)
                dm.status = 'Confirmed' if action == 'confirm' else 'Rejected'
                dm.admin_note = admin_note
                if action == 'confirm':
                    dm.confirmed_by = request.user
                    dm.confirmed_at = timezone.now()
                dm.save()
                messages.success(request, f'Damaged Material record has been {dm.status.lower()}!')
                return redirect('noc:damaged_materials')
            except DamageMaterial.DoesNotExist:
                messages.error(request, 'Record not found.')
                return redirect('noc:damaged_materials')

    return render(request, 'noc/damaged_materials.html', {
        'damaged_materials': damaged_page,
        'role': 'NOC',
        'page_obj': damaged_page,
        'branch_users': branch_users,
        'search_query': search_query,
    })