from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .forms import RegisterForm, MaterialForm, TaskForm, RequestForm, VendorForm, SystemSettingForm, NotificationSettingForm, UsedMaterialForm
from .models import Material, Task, MaterialRequest, UserProfile, Vendor, SystemSetting, NotificationSetting, UsedMaterial
from .utils import ensure_userprofile
from django.db.models import Sum, Q, F
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
import json
from io import StringIO
from . Serializer import MaterialSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def material_list_api(request):
    materials = Material.objects.all()
    serializer = MaterialSerializer(materials, many=True)
    return Response(serializer.data)
def material_detail_api(request, pk):
    try:
        material = Material.objects.get(pk=pk)
    except Material.DoesNotExist:
        return Response({'error': 'Material not found'}, status=404)

    if request.method == 'GET':
        serializer = MaterialSerializer(material)
        return Response(serializer.data)

    elif request.method == 'PUT':
        data = json.loads(request.body)
        serializer = MaterialSerializer(material, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    elif request.method == 'DELETE':
        material.delete()
        return Response(status=204)

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure role groups exist and add user to selected group
            role = form.cleaned_data.get('role')
            for r in ['Admin', 'Storekeeper', 'Technician']:
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
    role = profile.role if profile else 'Technician'

    total_materials = Material.objects.count()
    active_tasks = Task.objects.filter(status='In Progress').count()
    pending_requests = MaterialRequest.objects.filter(status='Pending').count()
    
    # Data for dashboard modals
    all_materials = Material.objects.all().order_by('-added_at')
    all_tasks = Task.objects.all().order_by('-created_at')
    all_requests = MaterialRequest.objects.all().order_by('-requested_at')
    all_used_materials = UsedMaterial.objects.all().select_related('technician', 'material').order_by('-added_at')

    if role == 'Technician':
        pass

    return render(request, 'inventory/dashboard.html', {
        'total_materials': total_materials,
        'active_tasks': active_tasks,
        'pending_requests': pending_requests,
        'all_materials': all_materials,
        'all_tasks': all_tasks,
        'all_requests': all_requests,
        'all_used_materials': all_used_materials,
        'role': role,
        'user': request.user,
    })

@login_required
def materials_view(request):
    # Base queryset
    materials = Material.objects.all()

    # Ensure a UserProfile exists and read role
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Technician'

    # Search: name, category, notes, added_by
    search = request.GET.get('search', '').strip()
    if search:
        materials = materials.filter(
            Q(name__icontains=search) | Q(category__icontains=search) | Q(notes__icontains=search) | Q(added_by__icontains=search)
        )

    # Stock status filtering using F() expressions
    stock_status = request.GET.get('stock_status')
    if stock_status == 'low':
        materials = materials.filter(quantity__lt=F('min_stock_level'))
    elif stock_status == 'normal':
        materials = materials.filter(quantity__gte=F('min_stock_level'))

    # status field on model now captures low/normal/out-of-stock state

    # Technician: only see their own rows (added_by stored as username)
    if role == 'Technician':
        materials = materials.filter(added_by=request.user.username)

    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        action = request.POST.get('action')

        # Delete action
        if action == 'delete' and role in ['Storekeeper', 'Technician']:
            material = get_object_or_404(Material, id=material_id)
            if role == 'Technician' and material.added_by != request.user.username:
                messages.error(request, "You can only delete your own materials!")
            else:
                material.delete()
                messages.success(request, "Material deleted!")
            return redirect('materials')

        # Technician 'use material' action (atomic, race-safe)
        if action == 'use_material':
            qty = request.POST.get('use_quantity')
            try:
                qty = int(qty)
            except (TypeError, ValueError):
                messages.error(request, "Invalid quantity specified.")
                return redirect('materials')

            # Role check (use profile computed above)
            if role != 'Technician':
                messages.error(request, "Only Technicians can use materials this way.")
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
        form = MaterialForm(request.POST, user=request.user, instance=material_id and get_object_or_404(Material, id=material_id) or None)
        if form.is_valid():
            material = form.save(commit=False)
            is_new = not material.id
            if is_new:
                if role != 'Storekeeper':
                    messages.error(request, "Only Storekeepers can add materials!")
                    return redirect('materials')
                material.added_by = request.user.username

            # Storekeepers may only update their own materials
            if not is_new and role == 'Storekeeper' and material.added_by != request.user.username:
                messages.error(request, "You can only update your own materials!")
                return redirect('materials')

            material.save()
            messages.success(request, "Material saved!")
            return redirect('materials')

    # render
    form = MaterialForm(user=request.user)
    context = {
        'materials': materials,
        'form': form,
        'role': role,
        'user': request.user,
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

    # Basic permission: Technicians should only fetch their own materials
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Technician'
    if role == 'Technician' and mat.added_by != request.user.username:
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
    role = profile.role if profile else 'Technician'

    # Filter permissions
    if role == 'Technician':
        # Technicians see tasks assigned to them
        tasks = Task.objects.filter(technician=request.user)
    else:
        # Admin/Storekeeper see all
        tasks = Task.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            if role == 'Technician':
                 messages.error(request, "Technicians cannot create tasks.")
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
                if role == 'Technician' and task.technician != request.user:
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
    requests = MaterialRequest.objects.all().order_by('-requested_at')
    
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Technician'

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Create Request
        if action == 'create':
            if role in ['Admin', 'Storekeeper']:
                 messages.error(request, "Only Technicians can submit requests.")
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
                    req.delete()
                    messages.success(request, "Request deleted successfully.")
                except MaterialRequest.DoesNotExist:
                    messages.error(request, "Request not found.")
                return redirect('requests')

            note = request.POST.get('note', '')
            try:
                req = MaterialRequest.objects.get(pk=req_id)
                
                if action == 'accept':
                    if req.status == 'Approved':
                        messages.warning(request, "Request already approved.")
                        return redirect('requests')
                        
                    # Deduct Quantity Logic
                    if req.quantity > req.material.quantity:
                        messages.error(request, f"Insufficient stock for {req.material.name}. Available: {req.material.quantity}")
                        return redirect('requests')
                    
                    try:
                        with transaction.atomic():
                            # Refresh material to be safe
                            mat = Material.objects.select_for_update().get(pk=req.material.id)
                            if mat.quantity < req.quantity:
                                raise ValueError("Insufficient stock")
                            
                            mat.quantity -= req.quantity
                            mat.save()
                            
                            req.status = 'Approved'
                            req.admin_note = note
                            req.save()
                            messages.success(request, f"Request approved. {req.quantity} units deducted from {mat.name}.")
                    except Exception as e:
                         messages.error(request, f"Transaction failed: {str(e)}")
                         return redirect('requests')

                elif action == 'reject':
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
        'requests': requests, 
        'form': form,
        'role': role
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
def manage_request(request, pk):
    # Backward compatibility if needed, but requests_view now handles it via POST
    return redirect('requests')

@login_required
def approve_request(request, pk):
    # Deprecated by manage_request logic
    return redirect('requests')

@login_required
def settings_view(request):
    # Ensure role groups exist
    ROLE_GROUPS = ['Admin', 'Storekeeper', 'Technician']
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
    default_group = Group.objects.get(name='Technician')
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

    vendors = Vendor.objects.all()
    system_settings = SystemSetting.objects.all()

    # Notification form for current user
    notif_obj, _ = NotificationSetting.objects.get_or_create(user=request.user)
    notif_form = NotificationSettingForm(instance=notif_obj)

    vendor_form = VendorForm()
    setting_form = SystemSettingForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_vendor':
            form = VendorForm(request.POST)
            if form.is_valid():
                vendor = form.save(commit=False)
                vendor.created_by = request.user
                vendor.save()
                messages.success(request, f"Vendor '{vendor.name}' added!")

        elif action == 'add_setting':
            form = SystemSettingForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "System setting saved!")

        elif action == 'update_notifications':
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
        'vendors': vendors,
        'vendor_form': vendor_form,
        'system_settings': system_settings,
        'setting_form': setting_form,
        'notif_form': notif_form,
    }
    return render(request, 'inventory/settings.html', context)


@login_required
def used_materials_view(request):
    profile = ensure_userprofile(request.user)
    role = profile.role if profile else 'Technician'

    # Filter permissions? 
    # "All these three types of users can see all the templates." (from initial prompt)
    used_materials = UsedMaterial.objects.all().select_related('technician', 'material').order_by('-added_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            if role != 'Technician':
                messages.error(request, "Only Technicians can add Used Models.")
                return redirect('used_materials')
            
            form = UsedMaterialForm(request.POST)
            if form.is_valid():
                um = form.save(commit=False)
                um.technician = request.user
                um.save()
                messages.success(request, "Used Model added successfully!")
                return redirect('used_materials')
            else:
                 messages.error(request, "Invalid data received.")
                
        elif action == 'edit':
            um_id = request.POST.get('um_id')
            try:
                um = UsedMaterial.objects.get(pk=um_id)
                # "This Used Model can only be edited by Teac User."
                if role == 'Technician' and um.technician == request.user:
                     form = UsedMaterialForm(request.POST, instance=um)
                     if form.is_valid():
                         form.save()
                         messages.success(request, "Used Model updated.")
                     else:
                         messages.error(request, "Invalid data.")
                else:
                     messages.error(request, "Permission denied.")
            except UsedMaterial.DoesNotExist:
                messages.error(request, "Record not found.")
            return redirect('used_materials')

    else:
        form = UsedMaterialForm()

    return render(request, 'inventory/used_materials.html', {
        'used_materials': used_materials,
        'form': form,
        'role': role
    })

@login_required
def manage_used_material(request, pk):
    # Backward compatibility stub - logic removed as Admin no longer approves UsedModel
    return redirect('used_materials')
