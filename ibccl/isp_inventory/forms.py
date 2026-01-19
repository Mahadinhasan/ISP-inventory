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
        fields = ['name', 'category', 'quantity', 'min_stock_level', 'notes', 'added_by']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Make notes field a larger textarea for better editing
        self.fields['notes'].widget = forms.Textarea(attrs={'rows': 4})
        # Only Admin can edit notes; non-Admins have readonly/disabled notes
        if self.user:
            try:
                profile = ensure_userprofile(self.user)
                role = profile.role if profile else None
            except Exception:
                role = None
            if role != 'Admin':
                self.fields['notes'].widget.attrs['readonly'] = True
                self.fields['notes'].widget.attrs['disabled'] = True   

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'customer', 'address', 'technician']

class RequestForm(forms.ModelForm):
    class Meta:
        model = MaterialRequest
        fields = ['material', 'quantity', 'notes']
 
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
        fields = ['material', 'quantity']   
