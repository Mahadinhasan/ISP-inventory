from django.contrib import admin
from .models import Material, Task, MaterialRequest, UserProfile, Vendor, SystemSetting, NotificationSetting, UsedMaterial

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
            'fields': ('user_note', 'admin_note')
        }),
        ('Used Materials', {
            'fields': ('used_materials_count', 'used_materials_display'),
            'description': 'Shows materials that have been used under this request'
        }),
    )

class UsedMaterialAdmin(admin.ModelAdmin):
    """Admin interface for UsedMaterial with request linking."""
    list_display = ['id', 'technician', 'material', 'quantity', 'material_request', 'status', 'added_at']
    list_filter = ['status', 'added_at', 'material__category']
    search_fields = ['technician__username', 'material__name', 'client_name']
    readonly_fields = ['added_at', 'updated_at']
    fieldsets = (
        ('Material Usage', {
            'fields': ('technician', 'material', 'quantity', 'material_request', 'status')
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

# Register your models here.
admin.site.register(Material)
admin.site.register(Task)
admin.site.register(MaterialRequest, MaterialRequestAdmin)
admin.site.register(UserProfile)
admin.site.register(Vendor)
admin.site.register(SystemSetting)
admin.site.register(NotificationSetting)
admin.site.register(UsedMaterial, UsedMaterialAdmin)
