from django.contrib import admin
from .models import Material, Task, MaterialRequest, UserProfile, SystemSetting, NotificationSetting, UsedMaterial, BackupRestore, ActivityLog, LogSettings

# Custom admin classes for better display

class MaterialRequestAdmin(admin.ModelAdmin):
    """Admin interface for MaterialRequest with used materials display."""
    list_display = ['id', 'requester', 'material', 'quantity', 'status', 'used_materials_count', 'used_materials_display', 'requested_at']
    list_filter = ['status', 'requested_at', 'material__category']
    search_fields = ['requester__username', 'material__name', 'send_by']
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
    list_display = ['id', 'name', 'category', 'quantity','Remaining_stock', 'min_stock_level', 'status', 'updated_at']
    list_filter = ['category', 'status']
    search_fields = ['name', 'category']
admin.site.register(Material, materialAdmin)
admin.site.register(Task, admin.ModelAdmin)
class MaterialRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'material', 'quantity', 'status', 'requested_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['requester__username', 'material__name', 'send_by']
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
    list_display = ['user', 'email_notifications', 'in_app_notifications', 'request_approved_alert', 'new_request_alert', 'low_stock_alert']
    list_filter = ['email_notifications', 'in_app_notifications', 'request_approved_alert', 'low_stock_alert', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email & General', {
            'fields': ('email_notifications', 'in_app_notifications')
        }),
        ('Requests & Approvals', {
            'fields': ('request_approved_alert', 'request_rejected_alert', 'new_request_alert')
        }),
        ('Stock & Inventory', {
            'fields': ('low_stock_alert', 'out_of_stock_alert', 'material_destroyed_alert')
        }),
        ('Tasks', {
            'fields': ('task_assignment_alert', 'task_completed_alert')
        }),
        ('Other', {
            'fields': ('message_alert', 'backup_alert', 'system_alert')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(NotificationSetting, NotificationSettingAdmin)


class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'timestamp', 'ip_address', 'get_description']
    list_filter = ['activity_type', 'timestamp', 'user']
    search_fields = ['user__username', 'description', 'ip_address']
    readonly_fields = ['timestamp', 'user', 'activity_type', 'description', 'ip_address', 'user_agent']
    date_hierarchy = 'timestamp'
    
    def get_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    get_description.short_description = 'Description'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(ActivityLog, ActivityLogAdmin)


class LogSettingsAdmin(admin.ModelAdmin):
    list_display = ['log_level', 'enable_file_logging', 'enable_database_logging', 'log_user_activities', 'updated_at']
    list_filter = ['log_level', 'enable_file_logging', 'enable_database_logging', 'log_user_activities']
    readonly_fields = ['updated_at']
    fieldsets = (
        ('Log Level', {
            'fields': ('log_level',),
            'description': 'Select the logging level: DEBUG, INFO, WARNING, ERROR, or CRITICAL'
        }),
        ('Logging Options', {
            'fields': ('enable_file_logging', 'enable_database_logging', 'log_user_activities')
        }),
        ('File Configuration', {
            'fields': ('log_file_path', 'max_log_file_size', 'backup_count'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(LogSettings, LogSettingsAdmin)
admin.site.register(UsedMaterial, UsedMaterialAdmin)

class BackupRestoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_by', 'backup_type', 'status', 'created_at', 'data_records_count', 'get_backup_size']
    list_filter = ['backup_type', 'status', 'created_at']
    search_fields = ['created_by__username', 'description']
    readonly_fields = ['checksum', 'created_at', 'deleted_at', 'restored_at']
    date_hierarchy = 'created_at'
    
    def get_backup_size(self, obj):
        return f"{obj.backup_size / (1024*1024):.2f} MB"
    get_backup_size.short_description = "Backup Size"

admin.site.register(BackupRestore, BackupRestoreAdmin)