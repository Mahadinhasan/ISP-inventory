from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from isp_inventory.models import UserProfile, Material, MaterialRequest, UsedMaterial, InternalMessage
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
from functools import wraps
import json as _json

# Create your views here.

def noc_login_view(request):
    """NOC-only login page"""
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
                login(request, user)

                if not request.POST.get('remember_me'):
                    request.session.set_expiry(0)  # browser close
                else:
                    request.session.set_expiry(60 * 60 * 1)  # 1 hour

                return redirect('noc:dashboard')
            except UserProfile.DoesNotExist:
                messages.error(request, "User profile not found. Please contact administrator.")
                return render(request, 'noc/login.html')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    
    return render(request, 'noc/login.html')

def noc_logout_view(request):
    """NOC logout"""
    logout(request)
    return redirect('noc:login')

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
    internet_materials = Material.objects.filter(category='Internet', created_by=request.user)
    
    stats = {
        'in_stock': internet_materials.filter(quantity__gt=0).count(),
        'pending_requests': MaterialRequest.objects.filter(material__category='Internet', material__created_by=request.user, status='Pending').count(),
        'used_materials': UsedMaterial.objects.filter(material__category='Internet', material__created_by=request.user).count(),
        'low_stock': internet_materials.filter(status='Low Stock').count(),
        'messages_count': InternalMessage.objects.filter(receiver=request.user, is_read=False).count(),
        'total_materials_value': internet_materials.aggregate(total=Sum('quantity'))['total'] or 0
    }
    
    recent_requests = MaterialRequest.objects.filter(material__category='Internet', material__created_by=request.user).order_by('-requested_at')[:5]
    
    return render(request, 'noc/dashboard.html', {
        'stats': stats,
        'recent_requests': recent_requests
    })

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
    requests = MaterialRequest.objects.filter(material__category='Internet', material__created_by=request.user).order_by('-requested_at')
    return render(request, 'noc/requests.html', {'requests': requests})

@login_required
@noc_role_required
def approve_request(request, pk):
    mat_request = get_object_or_404(MaterialRequest, pk=pk, material__category='Internet', material__created_by=request.user)
    if request.method == 'POST':
        if mat_request.material.quantity >= mat_request.quantity:
            mat_request.material.quantity -= mat_request.quantity
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
        mat_request.status = 'Rejected'
        mat_request.save()
        messages.success(request, "Request rejected.")
    return redirect('noc:requests')

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
    profile = request.user.userprofile
    return render(request, 'noc/profile.html', {'profile': profile})

def custom_404_view(request, exception=None):
    """Render a beautiful custom 404 page."""
    context = {
        'request_path': request.path,
    }
    return render(request, '404.html', context, status=404)