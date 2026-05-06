from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Material, MaterialRequest, SystemSetting, NotificationSetting, UsedMaterial, BackupRestore, ActivityLog, LogSettings, MacSerialNumber, MaterialMacSerialImport, UserProfile
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
    mac_serial = forms.ModelChoiceField(
        queryset=MacSerialNumber.objects.none(),
        required=False,
        label="Mac/Serial Number",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'id': 'used_material_mac_serial'
        }),
        help_text="Required for serialized items like ONUs"
    )

    class Meta:
        model = UsedMaterial
        fields = ['material', 'mac_serial', 'client_name', 'client_phone', 'client_address', 'quantity', 'issue', 'status']
        labels = {
            'material': 'Material Name',
            'mac_serial': 'Mac/Serial (Optional)',
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
            # Filter Mac/Serials for this user
            self.fields['mac_serial'].queryset = MacSerialNumber.objects.filter(
                assigned_to=user,
                status='Active'
            ).order_by('mac_serial')
            
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Branch':
                    # Filter to only show materials that have been approved for this Branch
                    approved_requests = MaterialRequest.objects.filter(
                        requester=user, 
                        status='Received'
                    )
                    approved_material_ids = approved_requests.values_list('material', flat=True).distinct()
                    
                    # Filter material queryset to only approved materials
                    self.fields['material'].queryset = Material.objects.filter(
                        id__in=approved_material_ids
                    ).select_related().order_by('name')
                    
                    self.fields['material'].help_text = 'Only approved materials are available'
                else:
                    # Admin/Storekeeper can see all materials
                    self.fields['material'].queryset = Material.objects.all().order_by('name')
                    self.fields['material'].help_text = 'All materials are available'
            except Exception:
                # Fallback to all materials
                self.fields['material'].queryset = Material.objects.all().order_by('name')
    
    
    def clean(self):
        cleaned_data = super().clean()
        material = cleaned_data.get('material')
        quantity = cleaned_data.get('quantity')
        
        if not self.user or not material or not quantity:
            return cleaned_data
            
        try:
            profile = ensure_userprofile(self.user)
            if profile and profile.role == 'Branch':
                # Calculate total approved for this material
                from django.db.models import Sum
                total_approved = MaterialRequest.objects.filter(
                    requester=self.user,
                    material=material,
                    status='Received'
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # Calculate total used/pending for this material
                # We exclude the current instance if we're editing
                used_query = UsedMaterial.objects.filter(
                    technician=self.user,
                    material=material
                )
                if self.instance and self.instance.pk:
                    used_query = used_query.exclude(pk=self.instance.pk)
                    
                total_used = used_query.aggregate(total=Sum('quantity'))['total'] or 0
                
                available = total_approved - total_used
                
                if quantity > available:
                    raise forms.ValidationError(
                        f"Insufficient approved stock for {material.name}. "
                        f"Total Approved: {total_approved}, Already Used: {total_used}, "
                        f"Available: {available}. You tried to use: {quantity}."
                    )
        except forms.ValidationError:
            raise
        except Exception as e:
            # For general exceptions, we can log or just let it pass
            pass
            
        return cleaned_data

    def clean_material(self):
        """Validate that Branch only selects approved materials with Normal status"""
        material = self.cleaned_data.get('material')
        
        if not material:
            raise forms.ValidationError("Material is required.")
        
        # Status check removed to allow use of Low Stock materials already in possession
        # Only validate approval for Branch
        if self.user:
            try:
                profile = ensure_userprofile(self.user)
                if profile and profile.role == 'Branch':
                    # Check if the selected material is in approved materials for this Branch
                    approved_material_ids = MaterialRequest.objects.filter(
                        requester=self.user,
                        status='Received'
                    ).values_list('material', flat=True).distinct()
                    
                    if material.id not in approved_material_ids:
                        raise forms.ValidationError(
                            "You can only use materials that have been approved for you."
                        )
            except forms.ValidationError:
                raise
            except Exception:
                pass
        
        return material

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