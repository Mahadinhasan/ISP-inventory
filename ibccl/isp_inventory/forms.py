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

class UsedMaterialForm(forms.ModelForm):
    class Meta:
        model = UsedMaterial
        fields = ['material', 'quantity', 'address', 'issue']
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            try:
                profile = ensure_userprofile(user)
                if profile and profile.role == 'Technician':
                    # Filter to only show materials that have been approved for this technician
                    approved_material_ids = MaterialRequest.objects.filter(
                        requester=user, 
                        status='Approved'
                    ).values_list('material', flat=True).distinct()
                    self.fields['material'].queryset = Material.objects.filter(id__in=approved_material_ids)
            except Exception:
                pass
