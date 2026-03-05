from django.contrib import admin
from .models import Material, Task, MaterialRequest, UserProfile, SystemSetting, NotificationSetting, UsedMaterial
from .models import backupandrestore

# Custom admin classes for better display

class MaterialRequestAdmin(admin.ModelAdmin):
    """Admin interface for MaterialRequest with used materials display."""
    list_display = ['id', 'requester', 'material', 'quantity', 'status', 'used_materials_count', 'used_materials_display', 'requested_at']
    list_filter = ['status', 'requested_at', 'material__category']
    search_fields = ['requester__username', 'material__name', 'user_note']
    readonly_fields = ['requested_at', 'used_materials_display', 'used_materials_count']
    fieldsets = (
        ('Request Info', {
            'fields': ('requester', 'material', 'quantity', 'status', 'requested_at')
        }),
        ('Notes', {
            'fields': ('send_by', 'admin_note')
        }),
        ('Used Materials', {
            'fields': ('used_materials_count', 'used_materials_display'),
            'description': 'Shows materials that have been used under this request'
        }),
    )

class UsedMaterialAdmin(admin.ModelAdmin):
    """Admin interface for UsedMaterial with request linking."""
    list_display = ['id', 'technician', 'material_name', 'get_category', 'quantity', 'status', 'added_at']
    list_filter = ['status', 'added_at', 'material__category']
    search_fields = ['technician__username', 'material__name', 'client_name', 'material__category']
    readonly_fields = ['added_at', 'updated_at']
    fieldsets = (
        ('Material Usage', {
            'fields': ('technician', 'material', 'quantity', 'status')
        }),
        ('Client Info', {
            'fields': ('client_name', 'client_phone', 'client_address')
        }),
        ('Technical Details', {
            'fields': ('issue', 'admin_note')
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def material_name(self, obj):
        """Display material name from the Material model."""
        return obj.material.name if obj.material else '-'
    material_name.short_description = 'Material Name'
    
    def get_category(self, obj):
        """Display material category from the Material model."""
        return obj.material.category if obj.material else '-'
    get_category.short_description = 'Category'

# Register your models here.
class materialAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'quantity', 'min_stock_level', 'status']
    list_filter = ['category', 'status']
    search_fields = ['name', 'category']
admin.site.register(Material, materialAdmin)
admin.site.register(Task, admin.ModelAdmin)
class MaterialRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'material', 'quantity', 'status', 'requested_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['requester__username', 'material__name', 'user_note']
admin.site.register(MaterialRequest, MaterialRequestAdmin)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'role', 'is_active', 'is_verified', 'email_notifications']
    list_filter = ['role', 'is_active', 'is_verified', 'email_notifications']
    search_fields = ['username', 'email', 'role']
admin.site.register(UserProfile, UserProfileAdmin)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'description']
admin.site.register(SystemSetting, SystemSettingAdmin)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'low_stock_alert', 'new_request_alert', 'task_assignment_alert']
    search_fields = ['user__username']
admin.site.register(NotificationSetting, NotificationSettingAdmin)
admin.site.register(UsedMaterial, UsedMaterialAdmin)

class backupandrestoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'backup_file', 'created_at']
    search_fields = ['backup_file']
admin.site.register(backupandrestore, backupandrestoreAdmin)