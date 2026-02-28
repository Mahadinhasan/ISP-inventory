from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Material, Task, MaterialRequest, SystemSetting, NotificationSetting, UsedMaterial,backupandrestore
from .utils import ensure_userprofile

class RegisterForm(UserCreationForm):
    ROLE_CHOICES = [('Branch', 'Branch'), ('Storekeeper', 'Storekeeper'), ('Admin', 'Admin'), ('NOC', 'NOC')]
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    class Meta:
        model = User
        fields = ['username', 'first_name', 'password1', 'password2', 'role']

# select field for material category (piece/meter)
class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'category', 'quantity', 'min_stock_level', 'status']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Determine user's role if available
        role = None
        if self.user:
            try:
                profile = ensure_userprofile(self.user)
                role = profile.role if profile else None
            except Exception:
                pass
        
        # Check if this is a new instance
        is_new = not (self.instance and self.instance.pk)
        
        # Handle role-based field modifications (before styling loop)
        if role == 'Storekeeper':
            # Storekeeper cannot edit the name of existing materials
            if not is_new:
                self.fields['name'].disabled = True
                self.fields['name'].help_text = "Name cannot be changed by Storekeeper."
            
            # Storekeeper cannot set status when adding new materials
            if is_new and 'status' in self.fields:
                del self.fields['status']
        
        # Branch cannot edit status at all
        if role == 'Branch':
            if 'status' in self.fields:
                self.fields['status'].disabled = True
        
        # Add black border styling to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border-2 border-black rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            })

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'customer', 'address', 'Branch']

class RequestForm(forms.ModelForm):
    class Meta:
        model = MaterialRequest
        fields = ['material', 'quantity', 'request_type', 'send_by', 'received_by']
        labels = {
            'user_note': 'User Notes',
            'request_type': 'Request Type',
            'send_by': 'Send By',
            'received_by': 'Received By',
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
        fields = ['email_notifications', 'low_stock_alert', 'new_request_alert', 'task_assignment_alert']
#Materials name filter for Branch use only approved materials
class UsedMaterialForm(forms.ModelForm):
    class Meta:
        model = UsedMaterial
        fields = ['material', 'client_name', 'client_phone', 'client_address', 'quantity', 'issue', 'status']
        labels = {
            'material': 'Material Name',
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
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Branch':
                    # Filter to only show materials that have been approved for this Branch
                    approved_requests = MaterialRequest.objects.filter(
                        requester=user, 
                        status='Approved'
                    )
                    approved_material_ids = approved_requests.values_list('material', flat=True).distinct()
                    
                    # Filter material queryset to only approved materials with Normal status
                    self.fields['material'].queryset = Material.objects.filter(
                        id__in=approved_material_ids,
                        status='Normal'
                    ).select_related().order_by('name')
                    
                    self.fields['material'].help_text = 'Only approved materials with Normal stock are available'
                else:
                    # Admin/Storekeeper can see Normal status materials only
                    self.fields['material'].queryset = Material.objects.filter(
                        status='Normal'
                    ).order_by('name')
                    self.fields['material'].help_text = 'Only materials with Normal stock are available'
            except Exception:
                # Fallback to Normal status materials if profile check fails
                self.fields['material'].queryset = Material.objects.filter(
                    status='Normal'
                ).order_by('name')
    
    
    def clean_material(self):
        """Validate that Branch only selects approved materials with Normal status"""
        material = self.cleaned_data.get('material')
        
        if not material:
            raise forms.ValidationError("Material is required.")
        
        # Check if material status is Normal
        if material.status != 'Normal':
            raise forms.ValidationError(
                f"Can only use materials with Normal status. '{material.name}' has status: {material.status}"
            )
        
        # Only validate approval for Branch
        if self.user:
            try:
                profile = ensure_userprofile(self.user)
                if profile and profile.role == 'Branch':
                    # For edit: allow the currently selected material even if no longer approved
                    if self.instance and self.instance.pk:
                        if material.id == self.instance.material.id:
                            return material
                    
                    # Check if the selected material is in approved materials for this Branch
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

class backupandrestoreForm(forms.ModelForm):
    class Meta:
        model = backupandrestore
        fields = ['backup_file']