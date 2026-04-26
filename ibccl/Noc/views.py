from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from rest_framework_simplejwt.tokens import RefreshToken
from isp_inventory.models import UserProfile, Material, MaterialRequest, UsedMaterial, InternalMessage
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from functools import wraps
import json as _json

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
                        if mat_request.quantity <= mat_request.material.quantity:
                            mat_request.material.quantity -= mat_request.quantity
                        else:
                            diff = mat_request.quantity - mat_request.material.quantity
                            mat_request.material.quantity = 0
                            mat_request.material.Remaining_stock -= diff
                        mat_request.material.save()
                        mat_request.status = 'Approved'
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} approved.")
                else:
                    messages.error(request, f"Insufficient stock for {mat_request.material.name}.")
            elif action == 'reject':
                if mat_request.status == 'Approved':
                    with transaction.atomic():
                        mat_request.material.quantity += mat_request.quantity
                        mat_request.material.save()
                        mat_request.status = 'Rejected'
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected and stock returned.")
                else:
                    mat_request.status = 'Rejected'
                    mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected.")
            return redirect('noc:dashboard')

    from isp_inventory.views import process_month_end_reset
    process_month_end_reset()
    internet_materials = Material.objects.filter(category='Internet', created_by=request.user)
    all_internet_materials = internet_materials.order_by('-added_at')
    
    # Standardized card counters
    # total_materials = internet_materials.aggregate(total=Sum('quantity'))['total'] or 0
    total_materials = internet_materials.count()
    pending_requests = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user, 
        status='Pending'
    ).count()
    used_materials_count = UsedMaterial.objects.filter(
        material__category='Internet', 
        material__created_by=request.user
    ).count()
    low_stock_materials = internet_materials.filter(status='Low Stock').count()
    
    # Specific for NOC role: MAC/Serial count (materials with serial info)
    mac_serial_count = internet_materials.filter(
        Q(notes__icontains='MAC') | Q(notes__icontains='Serial') | Q(name__icontains='MAC') | Q(name__icontains='Serial')
    ).count()

    # Context for modals
    total_users = UserProfile.objects.count()
    all_users_list = UserProfile.objects.select_related('user').order_by('-user__date_joined')
    
    pending_requests_list = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user, 
        status='Pending'
    ).order_by('-requested_at')
    
    advance_materials = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user, 
        request_type='Advance'
    ).order_by('-requested_at')
    
    materials_monitoring = MaterialRequest.objects.filter(
        material__category='Internet',
        material__created_by=request.user,
        status='Approved'
    ).select_related('material', 'requester').order_by('-requested_at')
    
    all_used_materials = UsedMaterial.objects.filter(
        material__category='Internet',
        material__created_by=request.user
    ).select_related('technician', 'material').order_by('-added_at')[:100]
    
    technician_approved_materials = MaterialRequest.objects.filter(
        status='Approved',
        material__category='Internet',
        material__created_by=request.user
    ).select_related('material')

    low_stock_material_list = internet_materials.filter(
        Q(status='Low Stock') | Q(status='Out of Stock')
    ).order_by('status', 'name')

    recent_requests = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user
    ).order_by('-requested_at')[:5]

    context = {
        'total_materials': total_materials,
        'pending_requests': pending_requests,
        'used_materials_count': used_materials_count,
        'low_stock_materials': low_stock_materials,
        'mac_serial_count': mac_serial_count,
        'total_users': total_users,
        'all_users_list': all_users_list,
        'pending_requests_list': pending_requests_list,
        'advance_materials': advance_materials,
        'materials_monitoring': materials_monitoring,
        'all_used_materials': all_used_materials,
        'technician_approved_materials': technician_approved_materials,
        'low_stock_material_list': low_stock_material_list,
        'recent_requests': recent_requests,
        'all_materials': all_internet_materials,
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
        min_stock = int(request.POST.get('min_stock_level', 0))
        
        Material.objects.create(
            name=name,
            category='Internet',
            quantity=quantity,
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
        material.min_stock_level = int(request.POST.get('min_stock_level', material.min_stock_level))
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
                        if requested_qty <= mat_request.material.quantity:
                            mat_request.material.quantity -= requested_qty
                        else:
                            diff = requested_qty - mat_request.material.quantity
                            mat_request.material.quantity = 0
                            mat_request.material.Remaining_stock -= diff
                        mat_request.material.save()
                        mat_request.quantity = requested_qty
                        mat_request.status = 'Approved'
                        mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} approved.")
                else:
                    messages.error(request, f"Insufficient stock for {mat_request.material.name}.")
            elif action == 'reject':
                if mat_request.status == 'Approved':
                    with transaction.atomic():
                        mat_request.material.quantity += mat_request.quantity
                        mat_request.material.save()
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
                mat_request.delete()
                messages.success(request, "Request permanently deleted.")
        return redirect('noc:requests')

    # GET logic: searching and filtering
    search_query = request.GET.get('search', '')
    user_filter = request.GET.get('user', '')
    
    requests_qs = MaterialRequest.objects.filter(
        material__category='Internet', 
        material__created_by=request.user
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
                if mat_request.quantity <= mat_request.material.quantity:
                    mat_request.material.quantity -= mat_request.quantity
                else:
                    diff = mat_request.quantity - mat_request.material.quantity
                    mat_request.material.quantity = 0
                    mat_request.material.Remaining_stock -= diff
                mat_request.material.save()
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
                mat_request.material.quantity += mat_request.quantity
                mat_request.material.save()
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
                        if used_mat.quantity <= used_mat.material.quantity:
                            used_mat.material.quantity -= used_mat.quantity
                        else:
                            diff = used_mat.quantity - used_mat.material.quantity
                            used_mat.material.quantity = 0
                            used_mat.material.Remaining_stock -= diff
                        used_mat.material.save()
                        used_mat.status = 'Accepted'
                        used_mat.admin_note = request.POST.get('admin_note', used_mat.admin_note)
                        used_mat.save()
                    messages.success(request, "Usage record accepted and stock deducted.")
                else:
                    messages.error(request, f"Insufficient stock for {used_mat.material.name}.")
            elif action == 'reject':
                if used_mat.status == 'Accepted':
                    with transaction.atomic():
                        used_mat.material.quantity += used_mat.quantity
                        used_mat.material.save()
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
        requested_at__date__lte=end
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
            profile.image = request.FILES['image']
            
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