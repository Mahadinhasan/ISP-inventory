from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from isp_inventory.models import UserProfile, Material, MaterialRequest, UsedMaterial, InternalMessage
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout

# Create your views here.

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def noc_role_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.userprofile.role == 'NOC':
            return view_func(request, *args, **kwargs)
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
    materials = Material.objects.filter(category='Internet', created_by=request.user).order_by('-added_at')
    return render(request, 'noc/materials.html', {'materials': materials})

@login_required
@noc_role_required
def add_material(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        min_stock = request.POST.get('min_stock_level')
        notes = request.POST.get('notes')
        
        Material.objects.create(
            name=name,
            category='Internet',
            quantity=quantity,
            Remaining_stock=quantity,
            min_stock_level=min_stock,
            notes=notes,
            created_by=request.user
        )
        messages.success(request, "Material added successfully.")
        return redirect('noc_materials')
    return render(request, 'noc/add_material.html')

@login_required
@noc_role_required
def edit_material(request, pk):
    material = get_object_or_404(Material, pk=pk, category='Internet', created_by=request.user)
    if request.method == 'POST':
        material.name = request.POST.get('name')
        material.quantity = request.POST.get('quantity')
        material.min_stock_level = request.POST.get('min_stock_level')
        material.notes = request.POST.get('notes')
        material.save()
        messages.success(request, "Material updated successfully.")
        return redirect('noc_materials')
    return render(request, 'noc/edit_material.html', {'material': material})

@login_required
@noc_role_required
def delete_material(request, pk):
    material = get_object_or_404(Material, pk=pk, category='Internet', created_by=request.user)
    if request.method == 'POST':
        material.delete()
        messages.success(request, "Material deleted successfully.")
        return redirect('noc_materials')
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
    return redirect('noc_requests')

@login_required
@noc_role_required
def reject_request(request, pk):
    mat_request = get_object_or_404(MaterialRequest, pk=pk, material__category='Internet', material__created_by=request.user)
    if request.method == 'POST':
        mat_request.status = 'Rejected'
        mat_request.save()
        messages.success(request, "Request rejected.")
    return redirect('noc_requests')

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
        try:
            from datetime import datetime as dt
            start = dt.strptime(from_date, '%Y-%m-%d').date()
            end   = dt.strptime(to_date,   '%Y-%m-%d').date()
        except Exception:
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
    from django.db.models import Sum, Count, Q
    from django.db.models.functions import TruncDate
    import json as _json

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