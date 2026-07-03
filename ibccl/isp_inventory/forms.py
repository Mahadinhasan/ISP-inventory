from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Sum
# pyrefly: ignore [missing-import]
from .models import Material, MaterialRequest, SystemSetting, NotificationSetting, UsedMaterial, BackupRestore, ActivityLog, LogSettings, MacSerialNumber, MaterialMacSerialImport, UserProfile, RefundableMaterial, RefundableMaterialUsage, DamageMaterial
# pyrefly: ignore [missing-import]
from .utils import ensure_userprofile

class RegisterForm(UserCreationForm):
    """Registration form that creates a Django User and populates UserProfile fields."""

    ROLE_CHOICES = [
        ('Branch', 'Branch'),
        ('Storekeeper', 'Storekeeper'),
        ('Admin', 'Admin'),
        ('NOC', 'NOC'),
    ]
    # Extra fields that live on UserProfile (not User)
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    city = forms.CharField(max_length=100, required=False)
    zip_code = forms.CharField(max_length=20, required=False)
    image = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    # ── Validation ──────

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_role(self):
        role = self.cleaned_data.get('role')
        valid = [r[0] for r in self.ROLE_CHOICES]
        if role not in valid:
            raise forms.ValidationError('Invalid role selected.')
        return role

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Profile image must be under 2 MB.')
            allowed = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
            if not image.name.lower().endswith(allowed):
                raise forms.ValidationError('Allowed formats: PNG, JPG, JPEG, WEBP, GIF.')
        return image

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user

# select field for material category (piece/meter)
class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'category', 'quantity', 'min_stock_level','rate','Type']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add black border styling to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            })
        
        if self.user:
            try:
                profile = ensure_userprofile(self.user)
                role = profile.role if profile else None
            except Exception:
                role = None
            
            is_new = not (self.instance and self.instance.pk)
            
            if role == 'Storekeeper':
                # Storekeeper cannot edit the name of existing materials
                # Use readonly (not disabled) so the field is still submitted in POST
                if not is_new:
                    self.fields['name'].widget.attrs['readonly'] = True
                    self.fields['name'].help_text = "Name cannot be changed by Storekeeper."
                # Status is auto-calculated by Material.save()

# class TaskForm(forms.ModelForm):
#     class Meta:
#         model = Task
#         fields = ['title', 'customer', 'address', 'Branch']

class RequestForm(forms.ModelForm):
    class Meta:
        model = MaterialRequest
        fields = ['material', 'quantity', 'request_type', 'pass_on', 'send_by']
        labels = {
            'send_by': 'User Notes',
            'request_type': 'Request Type',
            'send_by': 'Send By',
            'pass_on': 'Pass On',
        }
        widgets = {
            'material': forms.Select(attrs={
                'class': 'w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 border p-2'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 border p-2'
            }),
            'send_by': forms.Textarea(attrs={
                'class': 'w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 border p-2',
                'rows': 3
            }),
            'received_by': forms.Textarea(attrs={
                'class': 'w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 border p-2',
                'rows': 3
            }),
            'request_type': forms.HiddenInput(),
        }

class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['key', 'value', 'description']
        widgets = {
            'value': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

class NotificationSettingForm(forms.ModelForm):
    class Meta:
        model = NotificationSetting
        fields = [
            'email_notifications', 'in_app_notifications',
            'request_approved_alert', 'request_rejected_alert', 'new_request_alert',
            'low_stock_alert', 'out_of_stock_alert', 'material_destroyed_alert',
            'task_assignment_alert', 'task_completed_alert',
            'message_alert', 'backup_alert', 'system_alert'
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'in_app_notifications': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'request_approved_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'request_rejected_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'new_request_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'low_stock_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'out_of_stock_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'material_destroyed_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'task_assignment_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'task_completed_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'message_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'backup_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'system_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
        }

class LogSettingsForm(forms.ModelForm):
    class Meta:
        model = LogSettings
        fields = ['log_level', 'enable_file_logging', 'enable_database_logging', 'log_user_activities']
        widgets = {
            'log_level': forms.Select(attrs={'class': 'w-full px-4 py-3 border-2 border-yellow-200 dark:border-yellow-900/30 rounded-xl focus:border-yellow-500 focus:ring-2 focus:ring-yellow-100'}),
            'enable_file_logging': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'enable_database_logging': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
            'log_user_activities': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'}),
        }


#Materials name filter for Branch use only approved materials
class UsedMaterialForm(forms.ModelForm):
    # Combined selection field for material and mac/serial
    material_selection = forms.ChoiceField(
        label="Material Name",
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200 transition',
            'id': 'id_material_selection'
        }),
        help_text="Select from your approved in-stock materials"
    )

    class Meta:
        model = UsedMaterial
        fields = ['material_selection', 'client_name', 'client_phone', 'client_address', 'quantity', 'issue', 'status']
        labels = {
            'client_name': 'Client Name',
            'client_phone': 'Client Phone',
            'client_address': 'Client Address',
            'quantity': 'Quantity Used',
            'issue': 'Technical Issue / Notes',
            'status': 'Status',
        }
        widgets = {
            'material': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'client_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter client name'
            }),
            'client_address': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Enter client address'
            }),
            'client_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter client phone number'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '1'
            }),
            'issue': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Describe the technical issue or notes'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Store user for validation
        self.user = user
        
        if user:
            choices = [('', 'Select Material')]
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Branch':
                    # 1. Add Serialized Items (assigned to this user and Active)
                    active_serials = MacSerialNumber.objects.filter(
                        assigned_to=user,
                        status='Active'
                    ).select_related('material')
                    for s in active_serials:
                        choices.append((f"s:{s.id}", f"{s.material.name} - {s.mac_serial}"))

                    # 2. Add Non-Serialized Items (approved for this branch)
                    serialized_material_ids = MacSerialNumber.objects.filter(
                        assigned_to=user
                    ).values_list('material_id', flat=True).distinct()

                    approved_materials = MaterialRequest.objects.filter(
                        requester=user,
                        status='Received',
                        is_archived=False
                    ).values(
                        'material_id', 'material__name'
                    ).annotate(total_received=Sum('quantity'))

                    used_query = UsedMaterial.objects.filter(
                        technician=user
                    ).exclude(status='Rejected')
                    if self.instance and self.instance.pk:
                        used_query = used_query.exclude(pk=self.instance.pk)
                    used_totals = used_query.values('material_id').annotate(total_used=Sum('quantity'))
                    used_by_material = {u['material_id']: u['total_used'] or 0 for u in used_totals}

                    damaged_totals = DamageMaterial.objects.filter(
                        branch_user=user,
                        status__in=['Pending', 'Confirmed']
                    ).values('material_id').annotate(total_damaged=Sum('quantity'))
                    damaged_by_material = {d['material_id']: d['total_damaged'] or 0 for d in damaged_totals}

                    refundable_totals = RefundableMaterial.objects.filter(
                        branch_user=user
                    ).values('material_name').annotate(total_refundable=Sum('quantity'))
                    refundable_by_name = {r['material_name']: r['total_refundable'] or 0 for r in refundable_totals}

                    for item in approved_materials:
                        mat_id = item['material_id']
                        mat_name = item['material__name']
                        used_qty = used_by_material.get(mat_id, 0)
                        damaged_qty = damaged_by_material.get(mat_id, 0)
                        refundable_qty = refundable_by_name.get(mat_name, 0)
                        available = item['total_received'] - used_qty - damaged_qty - refundable_qty
                        if available > 0:
                            choices.append((
                                f"m:{mat_id}",
                                f"{mat_name} ({available} available)"
                            ))

                    if len(choices) == 1:
                        choices = [('', 'No approved in-stock materials available')]
                else:
                    # Admin/Storekeeper can see all materials
                    all_mats = Material.objects.all().order_by('name')
                    for m in all_mats:
                        choices.append((f"m:{m.id}", m.name))

                # When EDITING an existing record, pre-select the current material/serial
                if self.instance and self.instance.pk:
                    if self.instance.mac_serial_id:
                        # Serialized item — the current serial may be Retired, inject it back
                        try:
                            current_serial = MacSerialNumber.objects.select_related('material').get(pk=self.instance.mac_serial_id)
                            serial_key = f"s:{current_serial.id}"
                            existing_keys = [c[0] for c in choices]
                            if serial_key not in existing_keys:
                                choices.insert(1, (serial_key, f"{current_serial.material.name} - {current_serial.mac_serial} (current)"))
                            self.fields['material_selection'].initial = serial_key
                        except Exception:
                            pass
                    elif self.instance.material_id:
                        # Non-serialized — pre-select by material ID
                        self.fields['material_selection'].initial = f"m:{self.instance.material_id}"

                self.fields['material_selection'].choices = choices
            except Exception:
                self.fields['material_selection'].choices = [('', 'No materials available')]
        else:
            self.fields['material_selection'].choices = [('', 'Select User first')]

    
    
    def clean(self):
        cleaned_data = super().clean()
        selection = cleaned_data.get('material_selection')
        quantity = cleaned_data.get('quantity')

        if not self.user or not selection or quantity is None:
            return cleaned_data

        try:
            profile = ensure_userprofile(self.user)
            if profile and profile.role == 'Branch':
                prefix, pk = selection.split(':', 1)
                if prefix == 's':
                    if quantity != 1:
                        raise forms.ValidationError(
                            "Serialized items must be used one at a time. Quantity must be 1."
                        )
                elif prefix == 'm':
                    try:
                        material = Material.objects.get(id=int(pk))
                    except (Material.DoesNotExist, ValueError):
                        raise forms.ValidationError("Selected material not found.")

                    total_approved = MaterialRequest.objects.filter(
                        requester=self.user,
                        material=material,
                        status='Received',
                        is_archived=False
                    ).aggregate(total=Sum('quantity'))['total'] or 0

                    used_query = UsedMaterial.objects.filter(
                        technician=self.user,
                        material=material
                    )
                    if self.instance and self.instance.pk:
                        used_query = used_query.exclude(pk=self.instance.pk)

                    total_used = used_query.exclude(status='Rejected').aggregate(total=Sum('quantity'))['total'] or 0

                    damaged_qty = DamageMaterial.objects.filter(
                        branch_user=self.user,
                        material=material,
                        status__in=['Pending', 'Confirmed']
                    ).aggregate(total=Sum('quantity'))['total'] or 0

                    refundable_qty = RefundableMaterial.objects.filter(
                        branch_user=self.user,
                        material_name=material.name
                    ).aggregate(total=Sum('quantity'))['total'] or 0

                    available = total_approved - total_used - damaged_qty - refundable_qty

                    if available <= 0:
                        raise forms.ValidationError(
                            f"No approved stock available for {material.name}."
                        )
                    if quantity > available:
                        raise forms.ValidationError(
                            f"Insufficient approved stock for {material.name}. "
                            f"Total Approved: {total_approved}, Already Used: {total_used}, "
                            f"Available: {available}. You tried to use: {quantity}."
                        )
                else:
                    raise forms.ValidationError("Invalid material selection type.")
        except forms.ValidationError:
            raise
        except Exception:
            pass

        return cleaned_data

    def clean_material_selection(self):
        selection = self.cleaned_data.get('material_selection')
        if not selection:
            raise forms.ValidationError("Material selection is required.")

        try:
            prefix, pk = selection.split(':', 1)
        except ValueError:
            raise forms.ValidationError("Invalid material selection format.")

        if prefix == 's':
            try:
                serial = MacSerialNumber.objects.get(id=int(pk), assigned_to=self.user)
                # When creating: only allow Active serials.
                # When editing the SAME record: allow the serial regardless of status
                # (it may be Used/Retired but still legitimately belongs to this record).
                is_editing_same = (
                    self.instance and
                    self.instance.pk and
                    self.instance.mac_serial_id == serial.id
                )
                if not is_editing_same and serial.status != 'Active':
                    raise forms.ValidationError("Selected Mac/Serial is not active.")
            except (MacSerialNumber.DoesNotExist, ValueError):
                raise forms.ValidationError("Selected Mac/Serial is not assigned to you or does not exist.")
            return selection

        if prefix == 'm':
            try:
                material = Material.objects.get(id=int(pk))
            except (Material.DoesNotExist, ValueError):
                raise forms.ValidationError("Selected material not found.")

            if self.user:
                profile = ensure_userprofile(self.user)
                if profile and profile.role == 'Branch':
                    approved_material_ids = MaterialRequest.objects.filter(
                        requester=self.user,
                        status='Received',
                        is_archived=False
                    ).values_list('material', flat=True).distinct()

                    if material.id not in approved_material_ids:
                        raise forms.ValidationError(
                            "You can only use materials that have been approved for you."
                        )
            return selection

        raise forms.ValidationError("Invalid material selection type.")

class BackupRestoreForm(forms.ModelForm):
    class Meta:
        model = BackupRestore
        fields = ['backup_file', 'backup_type', 'description']


class MacSerialImportForm(forms.Form):
    """Form for NOC to add Mac/Serial numbers for materials and assign to branch users.
    Only 3 fields: Assign to User (Branch), Material (approved requests), Number of Items.
    Materials are filtered to only show the NOC user's own materials that the branch user has approved requests for.
    """
    
    assigned_to = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-indigo-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white dark:border-indigo-600 transition-all duration-200',
            'id': 'mac_serial_user'
        }),
        label='Assign to User (Branch)'
    )
    
    material = forms.ChoiceField(
        choices=[('', '-- Select a Branch User first --')],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-indigo-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white dark:border-indigo-600 transition-all duration-200',
            'id': 'mac_serial_material',
            'disabled': 'disabled'
        }),
        label='Material'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border border-indigo-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white dark:border-indigo-600 transition-all duration-200',
            'id': 'mac_serial_quantity',
            'placeholder': 'Enter number of items (max 50)',
            'min': '1',
            'max': '50'
        }),
        label='Number of Items',
        help_text='Number of mac/serial entries to add (max 50)'
    )
    
    def __init__(self, *args, **kwargs):
        self.noc_user = kwargs.pop('noc_user', None)
        super().__init__(*args, **kwargs)
        
        # Build branch user choices
        branch_profiles = UserProfile.objects.filter(role='Branch').select_related('user').order_by('user__username')
        user_choices = [('', '-- Select Branch User --')]
        for profile in branch_profiles:
            display = profile.user.get_full_name() or profile.user.username
            user_choices.append((profile.user.id, f"{display} ({profile.user.username})"))
        self.fields['assigned_to'].choices = user_choices
        
        # If form is bound (POST) or has initial data, populate material choices from the selected user's
        # approved requests — but ONLY for materials created by this NOC role
        assigned_to_id = self.data.get('assigned_to') or self.initial.get('assigned_to')
        if assigned_to_id:
            try:
                user_id = int(assigned_to_id)
                # Only show approved requests for materials created by a user with the NOC role
                requests = MaterialRequest.objects.filter(
                    requester_id=user_id,
                    status='Approved',
                    material__created_by__userprofile__role='NOC'
                ).select_related('material')
                
                material_choices = [('', '-- Select Approved Request/Material --')]
                for req in requests:
                    material_choices.append((req.id, f"{req.material.name} (Approved Qty: {req.quantity}) - Requested {req.requested_at.strftime('%Y-%m-%d')}"))
                
                self.fields['material'].choices = material_choices
                self.fields['material'].widget.attrs.pop('disabled', None)
                self.fields['material'].label = 'Approved Material Request'
            except (ValueError, TypeError):
                pass
    
    def clean_assigned_to(self):
        user_id = self.cleaned_data.get('assigned_to')
        if not user_id:
            raise forms.ValidationError("Please select a branch user.")
        try:
            user = User.objects.get(id=int(user_id))
            profile = UserProfile.objects.get(user=user, role='Branch')
            return user
        except (User.DoesNotExist, UserProfile.DoesNotExist, ValueError):
            raise forms.ValidationError("Invalid branch user selected.")
    
    def clean_material(self):
        mat_req_id = self.cleaned_data.get('material')
        if not mat_req_id:
            raise forms.ValidationError("Please select an approved material request.")
        try:
            return MaterialRequest.objects.get(id=int(mat_req_id), status='Approved')
        except (MaterialRequest.DoesNotExist, ValueError):
            raise forms.ValidationError("Invalid material request selected.")


class MacSerialNumberForm(forms.ModelForm):
    """Form for adding individual mac/serial numbers"""
    class Meta:
        model = MacSerialNumber
        fields = ['mac_serial', 'quantity']
        widgets = {
            'mac_serial': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-indigo-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white',
                'placeholder': 'Enter mac/serial number'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-indigo-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white',
                'min': '1',
                'value': '1'
            }),
        }

class RefundableMaterialForm(forms.ModelForm):
    """Form for Branch users to mark materials as refundable."""

    material_name = forms.CharField(
        label="Material Name",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200 transition',
            'id': 'id_refundable_material_name',
            'placeholder': 'Enter material name'
        }),
        help_text="Type the material name you want to mark as refundable."
    )

    mac_serial = forms.CharField(
        label="Mac/Serial",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200 transition',
            'id': 'id_refundable_mac_serial',
            'placeholder': 'Enter mac/serial number or leave as N/A'
        }),
        help_text="Enter the mac/serial number for this refundable item, or leave as N/A."
    )

    class Meta:
        model = RefundableMaterial
        fields = ['material_name', 'mac_serial', 'quantity']
        labels = {
            'material_name': 'Material Name',
            'quantity': 'Quantity',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '1',
                'placeholder': 'Enter quantity'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_material_name(self):
        material_name = self.cleaned_data.get('material_name', '').strip()
        if not material_name:
            raise forms.ValidationError('Material name is required.')
        return material_name

    def clean_mac_serial(self):
        mac = self.cleaned_data.get('mac_serial', '')
        if mac:
            mac = mac.strip()
            if mac.upper() in ['N/A', 'NA', 'NONE', 'NIL', '']:
                return None
            
            # Check unique constraint manually
            qs = RefundableMaterial.objects.filter(mac_serial__iexact=mac)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('This MAC/Serial is already logged for a refundable material.')
            return mac
        return None

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None or quantity < 1:
            raise forms.ValidationError('Quantity must be at least 1.')

        if self.instance and self.instance.pk:
            used_total = self.instance.usages.aggregate(total=Sum('materials_quantity'))['total'] or 0
            if quantity < used_total:
                raise forms.ValidationError(
                    f'Quantity cannot be less than the already used amount ({used_total}).'
                )
        return quantity

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.branch_user = self.user

        instance.material_name = self.cleaned_data.get('material_name', '').strip()
        mac = self.cleaned_data.get('mac_serial', '')
        mac = mac.strip() if mac is not None else ''
        instance.mac_serial = mac or None

        if commit:
            instance.save()
        return instance


class RefundableMaterialUsageForm(forms.ModelForm):
    material_selection = forms.ChoiceField(
        label="Refundable Material",
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200 transition',
            'id': 'id_refundable_usage_selection'
        }),
        help_text="Select one of your refundable materials to record usage against."
    )

    class Meta:
        model = RefundableMaterialUsage
        fields = ['material_selection', 'materials_quantity', 'client_name', 'client_phone', 'client_address', 'issue']
        labels = {
            'material_selection': 'Refundable Material',
            'materials_quantity': 'Quantity Used',
            'client_name': 'Client Name',
            'client_phone': 'Client Phone',
            'client_address': 'Client Address',
            'issue': 'Technical Issue / Notes',
        }
        widgets = {
            'materials_quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '1',
                'placeholder': 'Enter quantity used'
            }),
            'client_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter client name'
            }),
            'client_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter client phone number'
            }),
            'client_address': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Enter client address'
            }),
            'issue': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Describe the technical issue or notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        choices = [('', 'Select Refundable Material')]
        try:
            if user:
                refundable_qs = RefundableMaterial.objects.filter(branch_user=user).order_by('-added_at')
                for rf in refundable_qs:
                    used_total = rf.usages.aggregate(total=Sum('materials_quantity'))['total'] or 0
                    available = rf.quantity - used_total
                    if available > 0 or (self.instance and self.instance.pk and self.instance.refundable_material_id == rf.id):
                        if rf.mac_serial:
                            label = f"{rf.material_name} - {rf.mac_serial} (Available: {available})"
                        else:
                            label = f"{rf.material_name} (Available: {available})"
                        choices.append((f"r:{rf.id}", label))
        except Exception:
            pass
        self.fields['material_selection'].choices = choices
        if self.instance and self.instance.pk:
            self.fields['material_selection'].initial = f"r:{self.instance.refundable_material_id}"

    def clean(self):
        cleaned_data = super().clean()
        material_selection = cleaned_data.get('material_selection')
        quantity = cleaned_data.get('materials_quantity')

        if not material_selection or quantity is None:
            return cleaned_data

        if not material_selection.startswith('r:'):
            raise forms.ValidationError('Please select a valid refundable material.')

        try:
            rf_id = int(material_selection.split(':', 1)[1])
            refundable_material = RefundableMaterial.objects.get(pk=rf_id)
            cleaned_data['refundable_material'] = refundable_material

            if self.user and refundable_material.branch_user != self.user:
                raise forms.ValidationError('Invalid refundable material selected.')

            used_total = refundable_material.usages.aggregate(total=Sum('materials_quantity'))['total'] or 0
            if self.instance and self.instance.pk and self.instance.refundable_material_id == refundable_material.id:
                used_total -= self.instance.materials_quantity

            available = refundable_material.quantity - used_total
            if quantity > available:
                raise forms.ValidationError(
                    f"Insufficient refundable quantity for {refundable_material.material_name}. Available: {available}, requested: {quantity}."
                )
        except RefundableMaterial.DoesNotExist:
            raise forms.ValidationError('Invalid refundable material selected.')
        except forms.ValidationError:
            raise
        except Exception:
            pass

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.used_by = self.user
        if hasattr(self, 'cleaned_data') and 'refundable_material' in self.cleaned_data:
            instance.refundable_material = self.cleaned_data['refundable_material']
        if commit:
            instance.save()
        return instance


# ── Refundable Materials Form ──
class DamageMaterialForm(forms.ModelForm):
    """Form for Branch users to report damaged materials.
    Only Branch users can mark materials as damaged from their approved stock.
    """
    
    material_selection = forms.ChoiceField(
        label="Material Name",
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200 transition',
            'id': 'id_damaged_material_selection'
        }),
        help_text="Select from your approved in-stock materials"
    )

    class Meta:
        model = DamageMaterial
        fields = ['material_selection', 'quantity', 'damage_reason', 'mac_serial', 'status']
        labels = {
            'material_selection': 'Material Name',
            'quantity': 'Quantity Damaged',
            'damage_reason': 'Reason for Damage',
            'mac_serial': 'Mac/Serial Number (if applicable)',
            'status': 'Status',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '1',
                'placeholder': 'Enter quantity'
            }),
            'damage_reason': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Describe how/when the damage occurred'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Store user for validation
        self.user = user
        
        # Hide mac_serial as it is set automatically from selection prefix
        self.fields['mac_serial'].widget = forms.HiddenInput()
        self.fields['mac_serial'].required = False
        
        # Branch users can only use Pending status (Admin confirms/rejects)
        if user:
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Branch':
                    self.fields['status'].widget = forms.HiddenInput()
                    self.fields['status'].initial = 'Pending'
            except Exception:
                pass
        
        # Populate material choices
        if user:
            choices = [('', 'Select Material from Stock')]
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Branch':
                    # Add approved materials for this branch
                    # 1. Add Serialized Items (assigned to this user and Active)
                    from django.db.models import Q
                    active_serials_query = Q(assigned_to=user, status='Active')
                    if self.instance and self.instance.pk and self.instance.mac_serial:
                        active_serials_query |= Q(id=self.instance.mac_serial.id)
                        
                    active_serials = MacSerialNumber.objects.filter(
                        active_serials_query
                    ).exclude(material__category='Internet').select_related('material')
                    
                    for s in active_serials:
                        choices.append((f"s:{s.id}", f"{s.material.name} (MAC: {s.mac_serial})"))
                    
                    # 2. Add Non-Serialized Items (approved for this branch)
                    serialized_material_ids = MacSerialNumber.objects.filter(
                        assigned_to=user
                    ).values_list('material_id', flat=True).distinct()
                    
                    approved_requests = MaterialRequest.objects.filter(
                        requester=user, 
                        status='Received'
                    ).exclude(material__category='Internet').exclude(material_id__in=serialized_material_ids).select_related('material')
                    
                    mats_added = set()
                    for req in approved_requests:
                        if req.material.id not in mats_added:
                            choices.append((f"m:{req.material.id}", f"{req.material.name}"))
                            mats_added.add(req.material.id)
                else:
                    # Admin/Storekeeper/NOC can see all materials
                    if profile and profile.role == 'NOC':
                        all_mats = Material.objects.filter(category='Internet', created_by=user).order_by('name')
                    else:
                        all_mats = Material.objects.exclude(category='Internet').order_by('name')
                    
                    for m in all_mats:
                        choices.append((f"m:{m.id}", m.name))
                
                # Ensure current selection is present
                if self.instance and self.instance.pk:
                    curr_val = f"s:{self.instance.mac_serial.id}" if self.instance.mac_serial else f"m:{self.instance.material.id}"
                    if not any(c[0] == curr_val for c in choices):
                        label = f"{self.instance.material.name} (MAC: {self.instance.mac_serial.mac_serial})" if self.instance.mac_serial else self.instance.material.name
                        choices.append((curr_val, label))
                
                self.fields['material_selection'].choices = choices
            except Exception:
                self.fields['material_selection'].choices = [('', 'No materials available')]
        else:
            self.fields['material_selection'].choices = [('', 'Select User first')]

    def clean(self):
        cleaned_data = super().clean()
        material_selection = cleaned_data.get('material_selection')
        quantity = cleaned_data.get('quantity')
        
        if not self.user or not material_selection or not quantity:
            return cleaned_data
        
        # Parse material_selection
        prefix, pk = material_selection.split(':')
        
        if prefix == 's':
            try:
                from django.db.models import Q
                mac_query = Q(id=pk, assigned_to=self.user)
                if self.instance and self.instance.pk and self.instance.mac_serial:
                    mac_query |= Q(id=self.instance.mac_serial.id)
                
                mac = MacSerialNumber.objects.get(mac_query)
                material = mac.material
                mac_serial = mac
                # Force quantity to 1 for serialized items
                quantity = 1
                cleaned_data['quantity'] = 1
                cleaned_data['mac_serial'] = mac_serial
                cleaned_data['material'] = material
            except MacSerialNumber.DoesNotExist:
                raise forms.ValidationError("Selected Mac/Serial not found or not assigned to you.")
        else:
            try:
                material = Material.objects.get(id=pk)
                cleaned_data['mac_serial'] = None
                cleaned_data['material'] = material
            except Material.DoesNotExist:
                raise forms.ValidationError("Selected material not found.")
        
        # Validate Branch user has sufficient approved quantity
        try:
            profile = ensure_userprofile(self.user)
            if profile and profile.role == 'Branch':
                from django.db.models import Sum
                total_approved = MaterialRequest.objects.filter(
                    requester=self.user,
                    material=material,
                    status='Received'
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # Calculate total refundable/damaged for this material using free-text material name
                refundable_qty = RefundableMaterial.objects.filter(
                    branch_user=self.user,
                    material_name=material.name
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                damaged_qty = DamageMaterial.objects.filter(
                    branch_user=self.user,
                    material=material,
                    status__in=['Pending', 'Confirmed']
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # Exclude current instance if editing
                if self.instance and self.instance.pk:
                    damaged_qty -= self.instance.quantity
                
                # Deduct UsedMaterial quantity (excluding Rejected)
                used_material_qty = UsedMaterial.objects.filter(
                    technician=self.user,
                    material=material
                ).exclude(status='Rejected').aggregate(total=Sum('quantity'))['total'] or 0
                
                used_qty = refundable_qty + damaged_qty + used_material_qty
                available = total_approved - used_qty
                
                if quantity > available:
                    raise forms.ValidationError(
                        f"Insufficient available stock for {material.name}. "
                        f"Total Approved: {total_approved}, Already Refundable/Damaged: {used_qty}, "
                        f"Available: {available}. You tried to mark as damaged: {quantity}."
                    )
        except forms.ValidationError:
            raise
        except Exception as e:
            pass
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.branch_user = self.user
        # Extract material and mac_serial from cleaned_data if available
        if hasattr(self, 'cleaned_data'):
            if 'material' in self.cleaned_data:
                instance.material = self.cleaned_data['material']
            if 'mac_serial' in self.cleaned_data:
                instance.mac_serial = self.cleaned_data['mac_serial']
            if 'quantity' in self.cleaned_data:
                instance.quantity = self.cleaned_data['quantity']
        if commit:
            instance.save()
        return instance