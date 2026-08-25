from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login as django_login
from rest_framework_simplejwt.tokens import RefreshToken
from isp_inventory.models import UserProfile, Material, MaterialRequest, UsedMaterial, InternalMessage, MacSerialNumber, MaterialMacSerialImport, RefundableMaterial, RefundableMaterialUsage, DamageMaterial, TrashItem
from isp_inventory.utils import ensure_userprofile, deduct_material_stock, restore_material_stock, sync_mac_serial_status, move_to_trash, restore_trash_item, cleanup_expired_trash
from django.db.models import Sum, Count, Q, Case, When, IntegerField, Value
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
from django.core.exceptions import ValidationError
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.contrib.auth.password_validation import validate_password
from functools import wraps
import json as _json
from isp_inventory.views import process_month_end_reset, trash_view

# Create your views here.

def noc_login_view(request):
    """NOC-only login page using Django standard session login"""
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role == 'NOC':
                return redirect('noc:dashboard')
        except UserProfile.DoesNotExist:
            pass

    if request.method == "POST":
        remember_me = request.POST.get('remember_me')  # checkbox value
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
                
                # Standard Django login
                django_login(request, user)

                # Session expiry: if "Remember me" unchecked, expire on browser close
                if not remember_me:
                    request.session.set_expiry(0)         # expires when browser closes
                else:
                    request.session.set_expiry(60 * 60 * 24)  # 24 hours
                
                # Update profile activity status
                profile.is_active = True
                profile.last_login = timezone.now()
                profile.save(update_fields=['is_active', 'last_login'])
                
                return redirect('noc:dashboard')
                
            except UserProfile.DoesNotExist:
                messages.error(request, "User profile not found. Please contact administrator.")
                return render(request, 'noc/login.html')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    
    return render(request, 'noc/login.html')


def noc_logout_view(request):
    """NOC logout using Django standard session logout"""
    # Update profile activity status to False on logout
    try:
        profile = request.user.userprofile
        profile.is_active = False
        profile.save(update_fields=['is_active'])
    except Exception:
        pass
    
    # Standard Django logout
    logout(request)
    return redirect('noc:login')

def noc_dashboard(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('req_id')
        if action and req_id:
            mat_request = get_object_or_404(MaterialRequest, pk=req_id, material__category='Internet')
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
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today = now.date()

    noc_mats_q = Q(category='Internet')
    internet_materials = Material.objects.filter(noc_mats_q)
    in_stock_q = Q(quantity__gt=0) & ~Q(status='Out of Stock')
    all_internet_materials = internet_materials.filter(in_stock_q).order_by('-added_at')

    # Batch DB aggregation for all dashboard card counters — single DB query
    mat_stats = internet_materials.aggregate(
        total_materials=Count(Case(When(status='Normal', quantity__gt=0, then=Value(1)), output_field=IntegerField())),
        low_stock_materials=Count(Case(When(Q(status='Low Stock') | Q(status='Out of Stock'), then=Value(1)), output_field=IntegerField())),
        mac_serial_count=Count(Case(
            When(Q(notes__icontains='MAC') | Q(notes__icontains='Serial') | Q(name__icontains='MAC') | Q(name__icontains='Serial'), then=Value(1)),
            output_field=IntegerField()
        )),
        total_price1=Sum('total_price'),
    )
    total_materials = mat_stats['total_materials'] or 0
    low_stock_materials = mat_stats['low_stock_materials'] or 0
    mac_serial_count = mat_stats['mac_serial_count'] or 0
    total_price1 = mat_stats['total_price1'] or 0

    # Batch MaterialRequest count queries — single DB query
    mat_req_base = MaterialRequest.objects.filter(
        material__category='Internet',
        is_archived=False,
    )
    req_stats = mat_req_base.aggregate(
        pending_requests=Count(Case(
            When(status='Pending', requested_at__year=now.year, requested_at__month=now.month, then=Value(1)),
            output_field=IntegerField()
        )),
        total_req_count=Count(Case(When(requested_at__gte=month_start, then=Value(1)), output_field=IntegerField())),
        advance_count=Count(Case(
            When(request_type='Advance', requested_at__gte=month_start, then=Value(1)),
            output_field=IntegerField()
        )),
    )
    pending_requests = req_stats['pending_requests'] or 0
    total_req_count = req_stats['total_req_count'] or 0
    advance_count = req_stats['advance_count'] or 0

    # UsedMaterial counts — single DB query
    used_stats = UsedMaterial.objects.filter(
        material__category='Internet',
        status='Accepted',
    ).aggregate(
        used_materials_count=Count('id'),
        total_used_qty=Count(Case(When(added_at__gte=month_start, then=Value(1)), output_field=IntegerField())),
    )
    used_materials_count = used_stats['used_materials_count'] or 0
    total_used_qty = used_stats['total_used_qty'] or 0

    # Damaged materials count
    total_qty_issued = DamageMaterial.objects.filter(
        status='Confirmed',
        material__category='Internet',
        confirmed_at__gte=month_start
    ).count()

    # Internal Communication: unread messages
    unread_messages_count = InternalMessage.objects.filter(receiver=request.user, is_read=False).count()

    # Context for modals
    total_users = UserProfile.objects.count()
    all_users_list = UserProfile.objects.select_related('user').order_by('-user__date_joined')

    pending_requests_list = mat_req_base.filter(
        status='Pending',
        requested_at__year=now.year,
        requested_at__month=now.month,
    ).select_related('material', 'requester').order_by('-requested_at')

    advance_materials = mat_req_base.filter(
        request_type='Advance',
        requested_at__year=now.year,
        requested_at__month=now.month,
    ).select_related('material', 'requester').order_by('-requested_at')

    materials_monitoring = MaterialRequest.objects.filter(
        material__category='Internet',
        status='Approved',
        is_hidden_by_noc=False
    ).select_related('material', 'requester').order_by('-requested_at')

    all_used_materials = UsedMaterial.objects.filter(
        material__category='Internet'
    ).select_related('technician', 'material').order_by('-added_at')[:50]

    technician_approved_materials = MaterialRequest.objects.filter(
        status='Approved',
        material__category='Internet',
        is_hidden_by_noc=False
    ).select_related('material')

    low_stock_material_list = internet_materials.filter(
        Q(status='Low Stock') | Q(status='Out of Stock')
    ).order_by('status', 'name')

    # Today's Used Materials for NOC Dashboard (Paginated)
    today_used_materials_all = UsedMaterial.objects.filter(
        material__category='Internet',
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
        is_hidden_by_noc=False
    ).select_related('material', 'requester').order_by('-requested_at')[:5]

    refundable_materials = RefundableMaterial.objects.filter(branch_user__userprofile__role='Branch').select_related('branch_user').order_by('-added_at')
    damaged_materials = DamageMaterial.objects.filter(material__category='Internet').select_related('branch_user', 'material', 'confirmed_by').order_by('-added_at')
    branch_users = User.objects.select_related('userprofile').filter(userprofile__role='Branch').order_by('username')

    refundable_form = NocRefundableMaterialForm(noc_user=request.user)
    damaged_form = NocDamageMaterialForm(noc_user=request.user)

    context = {
        'total_materials': total_materials,
        'pending_requests': pending_requests,
        'used_materials_count': used_materials_count,
        'low_stock_materials': low_stock_materials,
        'mac_serial_count': mac_serial_count,
        'unread_messages_count': unread_messages_count,
        'total_qty_issued': total_qty_issued,
        'total_req_count': total_req_count,
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
def noc_materials(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    # Get search query & stock status from GET parameters
    search_query = request.GET.get('search', '').strip()
    stock_status = request.GET.get('stock_status', '').strip()
    
    # Base queryset - all Internet materials for NOC role
    noc_mats_q = Q(category='Internet')
    all_materials = Material.objects.filter(noc_mats_q)
    materials_qs = all_materials.select_related('created_by__userprofile').order_by('-added_at')

    # Single DB aggregation query - replaces Python for-loop over all 2000+ materials
    stats = all_materials.aggregate(
        total_normal_stock=Count(
            Case(When(status='Normal', then=Value(1)), output_field=IntegerField())
        ),
        total_low_stock=Count(
            Case(When(status='Low Stock', then=Value(1)), output_field=IntegerField())
        ),
        total_out_of_stock=Count(
            Case(When(status='Out of Stock', then=Value(1)), output_field=IntegerField())
        ),
        total_materials_count=Count('id'),
        total_price=Sum('total_price'),
    )

    total_normal_stock = stats['total_normal_stock'] or 0
    total_low_stock = stats['total_low_stock'] or 0
    total_out_of_stock = stats['total_out_of_stock'] or 0
    total_materials_count = stats['total_materials_count'] or 0
    total_price = stats['total_price'] or 0

    # Apply search filter if provided
    if search_query:
        materials_qs = materials_qs.filter(
            Q(name__icontains=search_query) | 
            Q(notes__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    # Apply stock_status filter matching Storekeeper style
    if stock_status == 'low':
        materials_qs = materials_qs.filter(status='Low Stock')
    elif stock_status == 'normal':
        materials_qs = materials_qs.filter(status='Normal')
    elif stock_status == 'out_of_stock':
        materials_qs = materials_qs.filter(status='Out of Stock')

    # Pagination setup (20 materials per page)
    paginator = Paginator(materials_qs, 20)
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
        'stock_status': stock_status,
        'total_normal_stock': total_normal_stock,
        'total_low_stock': total_low_stock,
        'total_out_of_stock': total_out_of_stock,
        'total_materials_count': total_materials_count,
        'paginator': paginator,
        'page_obj': materials,
        'total_price': total_price,
    }
    
    return render(request, 'noc/materials.html', context)

def _safe_int(val, default=0):
    """Safely convert float/int strings like '2915.0' or 2915 to integer."""
    try:
        if val is None or str(val).strip() == '':
            return int(float(default)) if default is not None else 0
        return int(float(val))
    except (ValueError, TypeError):
        return int(float(default)) if default is not None else 0

def _safe_float(val, default=0.0):
    """Safely convert float/int strings like '2915.5' or 2915 to float."""
    try:
        if val is None or str(val).strip() == '':
            return float(default) if default is not None else 0.0
        return float(val)
    except (ValueError, TypeError):
        return float(default) if default is not None else 0.0

def check_noc_permission(request):
    """Check if logged in user strictly has NOC role ONLY."""
    if not request.user.is_authenticated:
        messages.error(request, "Please log in first.")
        return False
    profile = ensure_userprofile(request.user)
    role = getattr(profile, 'role', '') if profile else ''
    if role and role.upper() == 'NOC':
        return True
    messages.error(request, "Access denied. NOC role required.")
    return False

@login_required
def add_material(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        quantity = _safe_int(request.POST.get('quantity'), 0)
        rate = _safe_float(request.POST.get('rate'), 0.0)
        min_stock = _safe_int(request.POST.get('min_stock_level'), 0)
        total_price = quantity * rate
        material = Material(
            name=name,
            category='Internet',
            quantity=quantity,
            rate=rate,
            total_price=total_price,
            Remaining_stock=0,
            min_stock_level=min_stock,
            created_by=request.user
        )
        try:
            # validate and save; Material.clean() will enforce unique name
            material.full_clean()
            material.save()
            messages.success(request, "Material added successfully.")
            return redirect('noc:materials')
        except ValidationError as ve:
            # Show field-specific validation errors to the user
            errs = []
            if hasattr(ve, 'message_dict'):
                for field, msgs in ve.message_dict.items():
                    for m in msgs:
                        errs.append(f"{field}: {m}")
            else:
                errs = ve.messages
            messages.error(request, ' '.join(errs))
            return render(request, 'noc/add_material.html', {'form_data': request.POST})
        except Exception as e:
            messages.error(request, f"Error saving material: {str(e)}")
            return render(request, 'noc/add_material.html', {'form_data': request.POST})
    return render(request, 'noc/add_material.html')

@login_required
def edit_material(request, pk):
    if not check_noc_permission(request):
        return redirect('dashboard')
    noc_mats_q = Q(category='Internet')
    material = get_object_or_404(Material, noc_mats_q, pk=pk)
    if request.method == 'POST':
        # NOC can edit quantity, rate, and min_stock_level
        material.quantity = _safe_int(request.POST.get('quantity'), material.quantity)
        material.rate = _safe_float(request.POST.get('rate'), material.rate)
        material.min_stock_level = _safe_int(request.POST.get('min_stock_level'), material.min_stock_level)
        material.total_price = material.quantity * material.rate
        material.updated_at = timezone.now()
        material.save()
        messages.success(request, "Material updated successfully.")
        return redirect('noc:materials')
    return render(request, 'noc/edit_material.html', {'material': material})

@login_required
def delete_material(request, pk):
    if not check_noc_permission(request):
        return redirect('dashboard')
    noc_mats_q = Q(category='Internet')
    material = get_object_or_404(Material, noc_mats_q, pk=pk)
    if request.method == 'POST':
        material.delete()
        messages.success(request, "Material deleted successfully.")
        return redirect('noc:materials')
    return render(request, 'noc/delete_confirm.html', {'material': material})

@login_required
def noc_requests(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('req_id')
        if action and req_id:
            noc_req_q = Q(material__category='Internet')
            mat_request = get_object_or_404(MaterialRequest, noc_req_q, pk=req_id)
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
                if mat_request.status == 'Received':
                    messages.error(request, f"Cannot reject request for {mat_request.material.name} after it has been received.")
                    return redirect('noc:requests')
                if mat_request.status == 'Approved':
                    with transaction.atomic():
                        restore_material_stock(mat_request.material, mat_request.quantity)
                        mat_request.status = 'Rejected'
                        mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
                        mat_request.save()
                    messages.success(request, f"Request for {mat_request.material.name} rejected and stock returned.")
        mat_request = get_object_or_404(MaterialRequest, pk=req_id)

        if action in ['Dispatched', 'Rejected']:
            mat_request.status = action
            mat_request.admin_note = request.POST.get('admin_note', mat_request.admin_note)
            mat_request.save()
            messages.success(request, f"Request status updated to {action}.")
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
                    move_to_trash(request.user, "Material Request", f"{mat_request.material.name} ({mat_request.quantity} units)", instance=mat_request)
                    mat_request.delete()
                messages.success(request, "Request deleted and moved to trash.")
            else:
                move_to_trash(request.user, "Material Request", f"{mat_request.material.name} ({mat_request.quantity} units)", instance=mat_request)
                mat_request.delete()
                messages.success(request, "Request moved to trash.")
        return redirect('noc:requests')

    # ── Month-end archive logic ─────────────────────────────────────────────
    # When a new month starts, archive all previous months' NOC requests for
    # this NOC user's Internet materials (is_archived=True).
    # Monthly reset does NOT apply to NOC materials/stock — only the requests
    # are archived for historical reference.
    now = timezone.now()
    noc_archive_key = f"noc_requests_archive_{request.user.id}_{now.year}_{now.month}"
    archived_count = 0
    from isp_inventory.models import SystemSetting as _SysSetting
    already_archived = _SysSetting.objects.filter(key=noc_archive_key).exists()
    if not already_archived:
        with transaction.atomic():
            # Archive all requests from months BEFORE the current month
            old_requests_qs = MaterialRequest.objects.filter(
                material__category='Internet',
                is_archived=False,
            ).exclude(
                requested_at__year=now.year,
                requested_at__month=now.month,
            )
            archived_count = old_requests_qs.count()
            if archived_count:
                old_requests_qs.update(is_archived=True, archived_at=now)
            # Mark this month's archive pass as done
            _SysSetting.objects.update_or_create(
                key=noc_archive_key,
                defaults={
                    'value': str(now),
                    'description': (
                        f"NOC month-end archive for user {request.user.id} "
                        f"processed for {now.strftime('%B %Y')} — "
                        f"{archived_count} request(s) archived."
                    )
                }
            )
    # ── GET logic: searching and filtering ─────────────────────────────────
    search_query = request.GET.get('search', '').strip()
    user_filter = request.GET.get('user', '').strip()
    status_filter = request.GET.get('status', '').strip()
    show_archived = request.GET.get('archived', '') == '1'

    noc_req_q = Q(material__category='Internet')

    base_requests_qs = MaterialRequest.objects.filter(
        noc_req_q,
        is_hidden_by_noc=False,
        is_archived=show_archived,  # Default: show current month (not archived)
    )

    # Summary counts for the top cards (calculated on base queryset before search/status filter)
    pending_count = base_requests_qs.filter(status='Pending').count()
    approved_count = base_requests_qs.filter(status='Approved').count()
    rejected_count = base_requests_qs.filter(status='Rejected').count()
    received_count = base_requests_qs.filter(status='Received').count()

    requests_qs = base_requests_qs

    if search_query:
        requests_qs = requests_qs.filter(
            Q(material__name__icontains=search_query) |
            Q(requester__username__icontains=search_query) |
            Q(send_by__icontains=search_query)
        )

    if user_filter:
        requests_qs = requests_qs.filter(requester_id=user_filter)

    if status_filter:
        requests_qs = requests_qs.filter(status__iexact=status_filter)

    requests_qs = requests_qs.select_related('material', 'requester').order_by('-requested_at')

    # Pagination
    paginator = Paginator(requests_qs, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    # All Branch users for filter dropdown
    all_branch_users = User.objects.filter(
        Q(userprofile__role='Branch') | Q(groups__name='Branch')
    ).distinct().order_by('username')

    context = {
        'requests': page_obj,
        'page_obj': page_obj,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'received_count': received_count,
        'users': all_branch_users,
        'show_archived': show_archived,
        'archived_count': archived_count,  # > 0 means archiving just happened this session
        'role': 'NOC',
    }
    return render(request, 'noc/requests.html', context)

@login_required
def approve_request(request, pk):
    if not check_noc_permission(request):
        return redirect('dashboard')
    mat_request = get_object_or_404(MaterialRequest, pk=pk, material__category='Internet')
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
def reject_request(request, pk):
    if not check_noc_permission(request):
        return redirect('dashboard')
    mat_request = get_object_or_404(MaterialRequest, pk=pk, material__category='Internet')
    if request.method == 'POST':
        if mat_request.status == 'Received':
            messages.error(request, "Cannot reject a request after it has been received.")
        elif mat_request.status == 'Approved':
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
def noc_used_materials(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        used_id = request.POST.get('used_id')
        if action and used_id:
            used_mat = get_object_or_404(UsedMaterial, pk=used_id, material__category='Internet')
            if action == 'accept':
                if used_mat.status == 'Accepted':
                    messages.warning(request, "Usage record already accepted.")
                elif used_mat.mac_serial and used_mat.mac_serial.is_ever_accepted:
                    messages.error(request, f"This MAC/Serial ({used_mat.mac_serial.mac_serial}) has already been used at a client site. It cannot be accepted again.")
                elif used_mat.material.quantity + used_mat.material.Remaining_stock >= used_mat.quantity:
                    with transaction.atomic():
                        deduct_material_stock(used_mat.material, used_mat.quantity)
                        used_mat.status = 'Accepted'
                        used_mat.admin_note = request.POST.get('admin_note', used_mat.admin_note)
                        used_mat.save()
                        sync_mac_serial_status(used_mat.mac_serial)
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
                        sync_mac_serial_status(used_mat.mac_serial)
                    messages.success(request, "Usage record rejected, stock returned, and serial status synchronized.")
                else:
                    with transaction.atomic():
                        used_mat.status = 'Rejected'
                        used_mat.admin_note = request.POST.get('admin_note', used_mat.admin_note)
                        used_mat.save()
                        sync_mac_serial_status(used_mat.mac_serial)
                    messages.success(request, "Usage record rejected and serial status synchronized.")

            elif action == 'delete':
                used_ids_str = request.POST.get('used_ids', '') or request.POST.get('used_id', '') or request.POST.get('um_id', '')
                used_ids = [int(i.strip()) for i in used_ids_str.split(',') if i.strip().isdigit()]
                if used_ids:
                    try:
                        with transaction.atomic():
                            used_materials = list(UsedMaterial.objects.filter(pk__in=used_ids, material__category='Internet'))
                            count = len(used_materials)
                            macs_to_sync = [um.mac_serial for um in used_materials if um.mac_serial]
                            
                            for um in used_materials:
                                move_to_trash(request.user, "Used Material", f"{um.material.name} ({um.quantity} units)", instance=um)

                            UsedMaterial.objects.filter(pk__in=[um.pk for um in used_materials]).delete()
                            
                            for mac in set(macs_to_sync):
                                sync_mac_serial_status(mac)
                            messages.success(request, f"Successfully moved {count} consumption record(s) to trash.")
                    except Exception as e:
                        messages.error(request, f"Delete error: {str(e)}")
                else:
                    messages.error(request, "No record selected for deletion.")

        return redirect('noc:used_materials')

    # GET Logic
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    user_id = request.GET.get('user_id', '')
    
    used_qs = UsedMaterial.objects.filter(
        material__category='Internet'
    ).select_related('technician', 'material', 'mac_serial').order_by('-added_at')
    
    if user_id:
        used_qs = used_qs.filter(technician_id=user_id)
        
    if search_query:
        used_qs = used_qs.filter(
            Q(material__name__icontains=search_query) |
            Q(mac_serial__mac_serial__icontains=search_query) |
            Q(technician__username__icontains=search_query) |
            Q(client_name__icontains=search_query) |
            Q(client_phone__icontains=search_query) |
            Q(client_address__icontains=search_query)|
            Q(client_address__icontains=search_query)
        )
    
    # Stats calculated before status filter
    total_count = used_qs.count()
    accepted_count = used_qs.filter(status='Accepted').count()
    pending_count = used_qs.filter(status='Pending').count()
    rejected_count = used_qs.filter(status='Rejected').count()
    
    if status_filter:
        used_qs = used_qs.filter(status=status_filter)
        
    used_qs = used_qs.order_by('-added_at')
    
    # Pagination
    paginator = Paginator(used_qs, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # All Branch users for filter dropdown
    all_branch_users = User.objects.filter(
        Q(userprofile__role='Branch') | Q(groups__name='Branch')
    ).distinct().order_by('username')
    
    context = {
        'used_materials': page_obj,
        'page_obj': page_obj,
        'total_count': total_count,
        'accepted_count': accepted_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'search_query': search_query,
        'status_filter': status_filter,
        'selected_user_id': user_id,
        'users': all_branch_users,
        'role': 'NOC'
    }
    return render(request, 'noc/used_materials.html', context)

@login_required
def noc_materials_monitoring(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    """Real-time materials monitoring for NOC: branch users and used materials they added."""
    ws_scheme = 'wss' if request.scheme == 'https' else 'ws'
    ws_host = request.get_host()
    ws_path = '/ws/inventory/materials-monitoring/'
    ws_url = f'{ws_scheme}://{ws_host}{ws_path}'
    return render(request, 'noc/materials_monitoring.html', {
        'ws_url': ws_url,
    })

@login_required
def noc_reports(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
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
    noc_materials_qs = Material.objects.filter(category='Internet')
    
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

    # ── Top materials by approved quantity - Paginated at 10 per page ────────
    top_materials_qs = (
        requests_qs.filter(status='Approved')
        .values('material__name')
        .annotate(total_qty=Sum('quantity'), req_count=Count('id'))
        .order_by('-total_qty')
    )
    top_qty_paginator = Paginator(top_materials_qs, 10)
    top_qty_page_obj = top_qty_paginator.get_page(request.GET.get('top_qty_page'))
    top_materials = top_qty_page_obj.object_list

    top_qty_gp = request.GET.copy()
    if 'top_qty_page' in top_qty_gp:
        del top_qty_gp['top_qty_page']
    top_qty_query_string = top_qty_gp.urlencode()

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

    # Daily activity for UsedMaterial (preferred for "Daily Used Materials Activity")
    used_daily_data = (
        used_qs
        .annotate(day=TruncDate('added_at'))
        .values('day')
        .annotate(
            accepted=Count('id', filter=Q(status='Accepted')),
            pending=Count('id', filter=Q(status='Pending')),
            rejected=Count('id', filter=Q(status='Rejected')),
        )
        .order_by('day')
    )
    used_chart_labels   = [str(d['day']) for d in used_daily_data]
    used_chart_accepted = [d['accepted'] for d in used_daily_data]
    used_chart_pending  = [d['pending']  for d in used_daily_data]
    used_chart_rejected = [d['rejected'] for d in used_daily_data]

    # Confirmed / Accepted Damaged Materials calculations (NOC Specific)
    damaged_qs = DamageMaterial.objects.filter(
        material__in=noc_materials_qs,
        added_at__date__gte=start,
        added_at__date__lte=end
    ).select_related('material', 'branch_user', 'confirmed_by')

    daily_damaged_qs = damaged_qs.filter(status='Confirmed')
    daily_damaged_summary = (
        daily_damaged_qs
        .values('branch_user__username')
        .annotate(total=Sum('quantity'))
        .order_by('-total')
    )
    daily_damaged_materials = [
        {'branch_name': item['branch_user__username'], 'damaged_materials': item['total']}
        for item in daily_damaged_summary
    ]

    damage_paginator = Paginator(daily_damaged_materials, 5)
    damage_page_obj = damage_paginator.get_page(request.GET.get('damage_page'))
    daily_damaged_materials_display = damage_page_obj.object_list

    damage_gp = request.GET.copy()
    if 'damage_page' in damage_gp:
        del damage_gp['damage_page']
    damage_query_string = damage_gp.urlencode()

    damaged_daily_data = (
        daily_damaged_qs
        .annotate(day=TruncDate('added_at'))
        .values('day')
        .annotate(total=Sum('quantity'))
        .order_by('day')
    )
    damaged_chart_labels = [str(d['day']) for d in damaged_daily_data]
    damaged_chart_values = [d['total'] for d in damaged_daily_data]

    # Material category breakdown (For NOC, usually all Internet, but we show by individual material names for better visualization)
    category_data = (
        requests_qs.filter(status='Approved')
        .values('material__name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')
    )
    cat_labels = [d['material__name'] or 'Unknown' for d in category_data][:10]
    cat_values = [d['qty'] or 0 for d in category_data][:10]

    # ── Recent requests (Paginated at 10 per page) ────────
    recent_requests_qs = requests_qs.order_by('-requested_at')
    paginator = Paginator(recent_requests_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    recent_requests = page_obj.object_list

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    query_string = get_params.urlencode()

    # ── Low-stock materials list (Paginated at 10 per page) ────────
    low_stock_qs = noc_materials_qs.filter(
        status__in=['Low Stock', 'Out of Stock']
    ).order_by('status', 'name')
    low_stock_paginator = Paginator(low_stock_qs, 10)
    low_stock_page_number = request.GET.get('low_stock_page')
    low_stock_page_obj = low_stock_paginator.get_page(low_stock_page_number)
    low_stock_list_display = low_stock_page_obj.object_list

    low_stock_get_params = request.GET.copy()
    if 'low_stock_page' in low_stock_get_params:
        del low_stock_get_params['low_stock_page']
    low_stock_query_string = low_stock_get_params.urlencode()

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
        # Tables with 10-item pagination
        'top_materials':    top_materials,
        'top_qty_page_obj': top_qty_page_obj,
        'top_qty_query_string': top_qty_query_string,

        'recent_requests':  recent_requests,
        'page_obj':         page_obj,
        'query_string':     query_string,

        'low_stock_list':   low_stock_list_display,
        'low_stock_page_obj': low_stock_page_obj,
        'low_stock_query_string': low_stock_query_string,

        # Damaged materials
        'daily_damaged_materials': daily_damaged_materials_display,
        'damage_page_obj': damage_page_obj,
        'damage_query_string': damage_query_string,
        # Chart data (serialised for JS)
        'chart_labels_json':   _json.dumps(chart_labels),
        'chart_approved_json': _json.dumps(chart_approved),
        'chart_pending_json':  _json.dumps(chart_pending),
        'chart_rejected_json': _json.dumps(chart_rejected),
        'used_chart_labels_json':   _json.dumps(used_chart_labels),
        'used_chart_accepted_json': _json.dumps(used_chart_accepted),
        'used_chart_pending_json':  _json.dumps(used_chart_pending),
        'used_chart_rejected_json': _json.dumps(used_chart_rejected),
        'damaged_chart_labels_json': _json.dumps(damaged_chart_labels),
        'damaged_chart_values_json': _json.dumps(damaged_chart_values),
        'cat_labels_json':     _json.dumps(cat_labels),
        'cat_values_json':     _json.dumps(cat_values),
    }
    return render(request, 'noc/reports.html', context)

@login_required
def noc_notifications(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    # This could be handled by a generic notification system if one exists,
    # but for now we can show recent activities or messages.
    messages_list = InternalMessage.objects.filter(receiver=request.user).order_by('-created_at')
    return render(request, 'noc/notifications.html', {'messages': messages_list})

@login_required
def noc_profile(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
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
def add_mac_serials(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
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
def edit_mac_serials(request, pk):
    if not check_noc_permission(request):
        return redirect('dashboard')
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
def list_mac_serials(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    """View all Mac/Serial numbers managed by NOC"""
    mac_serials = MacSerialNumber.objects.filter(
        Q(material__category='Internet') | Q(added_by__userprofile__role='NOC')
    ).select_related('material', 'assigned_to').order_by('-created_at')
    
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
def delete_mac_serial(request, pk):
    if not check_noc_permission(request):
        return redirect('dashboard')
    """Delete a Mac/Serial number"""
    mac_serial = get_object_or_404(MacSerialNumber, pk=pk)
    
    if request.method == 'POST':
        material_name = mac_serial.material.name if mac_serial.material else 'N/A'
        move_to_trash(request.user, "MAC/Serial Number", f"{mac_serial.mac_serial} ({material_name})", instance=mac_serial)
        mac_serial.delete()
        messages.success(request, f"Mac/Serial number moved to trash for {material_name}.")
        return redirect('noc:list_mac_serials')
    
    return render(request, 'noc/confirm_delete_mac_serial.html', {'mac_serial': mac_serial})
    
@login_required
def get_branch_materials(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
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
        self.fields['material'].queryset = Material.objects.filter(category='Internet').order_by('name')


# ── NOC Custom Views for Refundable & Damaged Materials ───────────────────

@login_required
def noc_log_refundable(request):
    messages.error(request, "Access denied. NOC role is not allowed to log refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_edit_refundable(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to edit refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_delete_refundable(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to delete refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_process_refundable(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to process refundable materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_log_damaged(request):
    messages.error(request, "Access denied. NOC role is not allowed to log damaged materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_edit_damaged(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to edit damaged materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_delete_damaged(request, pk):
    messages.error(request, "Access denied. NOC role is not allowed to delete damaged materials directly.")
    return redirect('noc:dashboard')

@login_required
def noc_process_damaged(request, pk):
    dm = get_object_or_404(DamageMaterial, pk=pk, material__category='Internet')
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '').strip()

        # Rejected records are permanently locked — cannot be changed
        if dm.status == 'Rejected':
            messages.error(request, "This damage record has already been Rejected and is permanently locked. No further changes are allowed.")
            return redirect('noc:dashboard')

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
def noc_get_damaged_api(request, pk):
    dm = get_object_or_404(DamageMaterial, pk=pk, material__category='Internet')
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
def noc_refundable_materials_view(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    refundable_qs = RefundableMaterial.objects.select_related('branch_user').order_by('-added_at')
    branch_users = User.objects.select_related('userprofile').filter(userprofile__role='Branch').order_by('username')

    selected_user_id = request.GET.get('user_id')
    selected_user = None
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

    # Usage records (Used Materials table) — apply same filters
    refundable_usages_qs = RefundableMaterialUsage.objects.select_related(
        'refundable_material', 'refundable_material__branch_user', 'used_by'
    ).order_by('-used_at')

    # Filter by selected branch user
    if selected_user:
        refundable_usages_qs = refundable_usages_qs.filter(
            refundable_material__branch_user=selected_user
        )

    # Filter by search query
    if search_query:
        refundable_usages_qs = refundable_usages_qs.filter(
            Q(refundable_material__material_name__icontains=search_query) |
            Q(refundable_material__branch_user__username__icontains=search_query) |
            Q(refundable_material__branch_user__first_name__icontains=search_query) |
            Q(refundable_material__branch_user__last_name__icontains=search_query) |
            Q(client_name__icontains=search_query)
        ).distinct()

    usage_paginator = Paginator(refundable_usages_qs, 20)
    usage_page = usage_paginator.get_page(request.GET.get('usage_page'))

    # Compute refundable and used material statistics
    from django.db.models.functions import Coalesce
    from django.db.models import Sum, F
    
    annotated_qs = refundable_qs.annotate(
        used_total=Coalesce(Sum('usages__materials_quantity'), 0),
        available_quantity=F('quantity') - F('used_total')
    )
    total_refundable_qty = sum(r.available_quantity for r in annotated_qs)
    refundable_count = annotated_qs.filter(available_quantity__gt=0).count()
    
    used_count = refundable_usages_qs.count()
    total_used_qty = refundable_usages_qs.aggregate(s=Sum('materials_quantity'))['s'] or 0

    return render(request, 'noc/refundable_materials.html', {
        'refundable_materials': refundable_page,
        'role': 'NOC',
        'page_obj': refundable_page,
        'branch_users': branch_users,
        'search_query': search_query,
        'usage_page': usage_page,
        'refundable_count': refundable_count,
        'total_refundable_qty': total_refundable_qty,
        'used_count': used_count,
        'total_used_qty': total_used_qty,
    })



@login_required
def noc_damaged_materials_view(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    damaged_qs = DamageMaterial.objects.filter(material__category='Internet').select_related('branch_user', 'material', 'confirmed_by').order_by('-added_at')
    branch_users = User.objects.filter(Q(userprofile__role='Branch') | Q(groups__name='Branch')).distinct().order_by('username')
    
    selected_user_id = request.GET.get('user_id')
    if selected_user_id:
        try:
            selected_user = User.objects.get(id=selected_user_id)
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

    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['confirm', 'reject']:
            dm_id = request.POST.get('dm_id')
            admin_note = request.POST.get('admin_note', '').strip()
            try:
                dm = DamageMaterial.objects.get(pk=dm_id, material__category='Internet')
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

    # Damaged materials count stats before status filter
    total_damaged_count = damaged_qs.count()
    pending_count = damaged_qs.filter(status='Pending').count()
    confirmed_count = damaged_qs.filter(status='Confirmed').count()
    rejected_count = damaged_qs.filter(status='Rejected').count()
    total_damaged_qty = damaged_qs.aggregate(s=Sum('quantity'))['s'] or 0

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        damaged_qs = damaged_qs.filter(status=status_filter)

    paginator = Paginator(damaged_qs, 20)
    page_number = request.GET.get('page')
    damaged_page = paginator.get_page(page_number)

    return render(request, 'noc/damaged_materials.html', {
        'damaged_materials': damaged_page,
        'role': 'NOC',
        'page_obj': damaged_page,
        'branch_users': branch_users,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_damaged_count': total_damaged_count,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'rejected_count': rejected_count,
        'total_damaged_qty': total_damaged_qty,
    })


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

@login_required
def noc_logs(request):
    if not check_noc_permission(request):
        return redirect('dashboard')
    """Dedicated logs view for the NOC role, showing only their own actions."""
    user = request.user
    profile = user.userprofile
    
    if profile.role != 'NOC':
        messages.error(request, "Access restricted to NOC role.")
        return redirect('noc:dashboard')
        
    from isp_inventory.models import ActivityLog
    from django.core.paginator import Paginator
    from django.utils import timezone
    from datetime import datetime
    
    now = timezone.now()
    current_month_start = datetime(now.year, now.month, 1)
    if timezone.is_aware(now):
        current_month_start = timezone.make_aware(datetime(now.year, now.month, 1))

    # Auto-purge logs from previous months at month end
    ActivityLog.objects.filter(timestamp__lt=current_month_start).delete()

    # Fetch logs for the logged-in user for current month only
    base_logs = ActivityLog.objects.filter(user=request.user, timestamp__gte=current_month_start)
    
    login_count = base_logs.filter(activity_type='login').count()
    logout_count = base_logs.filter(activity_type='logout').count()
    create_count = base_logs.filter(activity_type='create').count()
    edit_count = base_logs.filter(activity_type='edit').count()
    delete_count = base_logs.filter(activity_type='delete').count()
    total_logs_count = base_logs.count()

    logs_qs = base_logs.select_related('user').order_by('-timestamp')
    
    # Filter by search/activity type if provided
    log_type_filter = request.GET.get('log_type', '').strip()
    if log_type_filter:
        logs_qs = logs_qs.filter(activity_type=log_type_filter)
        
    # Paginate by 30 records per page
    paginator = Paginator(logs_qs, 30)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'log_type_filter': log_type_filter,
        'profile': profile,
        'login_count': login_count,
        'logout_count': logout_count,
        'create_count': create_count,
        'edit_count': edit_count,
        'delete_count': delete_count,
        'total_logs_count': total_logs_count,
    }
    return render(request, 'noc/logs.html', context)
