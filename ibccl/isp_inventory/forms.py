from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Material, Task, MaterialRequest, Vendor, SystemSetting, NotificationSetting, UsedMaterial
from .utils import ensure_userprofile

class RegisterForm(UserCreationForm):
    ROLE_CHOICES = [('Technician', 'Technician'), ('Storekeeper', 'Storekeeper'), ('Admin', 'Admin')]
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    class Meta:
        model = User
        fields = ['username', 'first_name', 'password1', 'password2', 'role']

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'category', 'quantity', 'min_stock_level', 'status', 'added_by']
    
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
                if not is_new:
                    self.fields['name'].disabled = True
                    self.fields['name'].help_text = "Name cannot be changed by Storekeeper."
                
                # Storekeeper cannot set status when adding new materials
                # But can edit status for existing materials
                if is_new and 'status' in self.fields:
                    del self.fields['status']
            
            # Technicians cannot edit status at all
            if role == 'Technician':
                if 'status' in self.fields:
                    self.fields['status'].disabled = True

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'customer', 'address', 'technician']

class RequestForm(forms.ModelForm):
    class Meta:
        model = MaterialRequest
        fields = ['material', 'quantity', 'user_note'] 
        labels = {
            'user_note': 'User Notes',
        }
 
class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}

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
        fields = ['email_notifications', 'low_stock_alert', 'new_request_alert', 'task_assignment_alert']
#Materials name filter for technician use only approved materials
class UsedMaterialForm(forms.ModelForm):
    # Add a read-only category field
    category = forms.CharField(
        label='Category',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'readonly': 'readonly'
        })
    )
    
    class Meta:
        model = UsedMaterial
        fields = ['material', 'material_request', 'client_name', 'client_address', 'client_phone', 'quantity', 'issue', 'status']
        labels = {
            'material': 'Material Name',
            'material_request': 'Material Request (Optional)',
            'client_name': 'Client Name',
            'client_address': 'Client Address',
            'client_phone': 'Client Phone',
            'quantity': 'Quantity Used',
            'issue': 'Technical Issue / Notes',
            'status': 'Status/Authorize',
        }
        widgets = {
            'material': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'material_request': forms.Select(attrs={
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
        
        # Set initial category value if instance has a material
        if self.instance and self.instance.pk and self.instance.material:
            self.fields['category'].initial = self.instance.material.category
        
        if user:
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Technician':
                    # Filter to only show materials that have been approved for this technician
                    # Approved materials are from MaterialRequest objects with status='Approved'
                    approved_requests = MaterialRequest.objects.filter(
                        requester=user, 
                        status='Approved'
                    )
                    approved_material_ids = approved_requests.values_list('material', flat=True).distinct()
                    
                    # Filter material queryset to only approved materials with Normal status
                    self.fields['material'].queryset = Material.objects.filter(
                        id__in=approved_material_ids,
                        status='Normal'  # Only show Normal status materials
                    ).select_related().order_by('name')
                    
                    # Filter material_request to only show approved requests for this technician
                    self.fields['material_request'].queryset = approved_requests.select_related('material').order_by('-requested_at')
                    
                    # Add help text for clarity
                    self.fields['material'].help_text = 'Only approved materials with Normal stock are available'
                    self.fields['material_request'].help_text = 'Link to an approved material request (optional)'
                else:
                    # Admin/Storekeeper can see Normal status materials only
                    self.fields['material'].queryset = Material.objects.filter(
                        status='Normal'  # Only show Normal status materials
                    ).order_by('name')
                    self.fields['material_request'].queryset = MaterialRequest.objects.filter(status='Approved').select_related('material').order_by('-requested_at')
                    self.fields['material'].help_text = 'Only materials with Normal stock are available'
            except Exception:
                # Fallback to Normal status materials if profile check fails
                self.fields['material'].queryset = Material.objects.filter(
                    status='Normal'  # Only show Normal status materials
                ).order_by('name')
                self.fields['material'].help_text = 'Only materials with Normal stock are available'
                self.fields['material_request'].queryset = MaterialRequest.objects.filter(status='Approved').select_related('material').order_by('-requested_at')
    
    
    def clean_material(self):
        """Validate that technician only selects approved materials with Normal status"""
        material = self.cleaned_data.get('material')
        
        if not material:
            raise forms.ValidationError("Material is required.")
        
        # Check if material status is Normal
        if material.status != 'Normal':
            raise forms.ValidationError(
                f"Can only use materials with Normal status. '{material.name}' has status: {material.status}"
            )
        
        # Only validate approval for Technicians
        if self.user:
            try:
                profile = ensure_userprofile(self.user)
                if profile and profile.role == 'Technician':
                    # Check if the selected material is in approved materials for this technician
                    approved_material_ids = MaterialRequest.objects.filter(
                        requester=self.user,
                        status='Approved'
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
    
    def clean(self):
        """Update category field when material is selected"""
        cleaned_data = super().clean()
        material = cleaned_data.get('material')
        
        if material:
            cleaned_data['category'] = material.category
        
        return cleaned_data
