from django.contrib import admin
from .models import Material, MaterialRequest, UserProfile, SystemSetting, NotificationSetting, UsedMaterial, BackupRestore, ActivityLog, LogSettings, MacSerialNumber, MaterialMacSerialImport

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
    list_display = ['id', 'name', 'category', 'Type','quantity','Remaining_stock', 'min_stock_level', 'status', 'updated_at','rate','total_price']
    list_filter = ['category', 'status']
    search_fields = ['name', 'category']
admin.site.register(Material, materialAdmin)
# admin.site.register(Task, admin.ModelAdmin)
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


class MacSerialNumberAdmin(admin.ModelAdmin):
    list_display = ['id', 'mac_serial', 'material_name', 'quantity', 'assigned_to_username', 'created_at']
    list_filter = ['created_at', 'material']
    search_fields = ['mac_serial', 'material__name', 'assigned_to__username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Mac/Serial Info', {
            'fields': ('mac_serial', 'material', 'quantity')
        }),
        ('Assignment', {
            'fields': ('assigned_to',)
        }),
        ('Admin', {
            'fields': ('added_by',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'

admin.site.register(MacSerialNumber, MacSerialNumberAdmin)


class MaterialMacSerialImportAdmin(admin.ModelAdmin):
    list_display = ['id', 'material_name', 'branch_user_name', 'total_quantity', 'mac_serials_count', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'material']
    search_fields = ['material__name', 'assigned_to__username', 'noc_user__username']
    readonly_fields = ['created_at', 'approved_at']
    fieldsets = (
        ('Material & Assignment', {
            'fields': ('material', 'assigned_to', 'total_quantity', 'mac_serials_count')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
        ('Approval Info', {
            'fields': ('noc_user', 'approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'

admin.site.register(MaterialMacSerialImport, MaterialMacSerialImportAdmin)

# class RefundableMaterialAdmin(admin.ModelAdmin):
#     list_display = ['id', 'branch_user', 'material', 'quantity', 'status', 'created_at']
#     list_filter = ['status', 'created_at', 'material']
#     search_fields = ['branch_user__username', 'material__name']
#     readonly_fields = ['created_at']
#     fieldsets = (
#         ('Material Info', {
#             'fields': ('branch_user', 'material', 'quantity')
#         }),
#         ('Status', {
#             'fields': ('status', 'admin_note')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )
#     date_hierarchy = 'created_at'

# admin.site.register(RefundableMaterial, RefundableMaterialAdmin)

# class DamageMaterialAdmin(admin.ModelAdmin):
#     list_display = ['id', 'branch_user', 'material', 'quantity', 'damage_type', 'status', 'created_at']
#     list_filter = ['status', 'created_at', 'material', 'damage_type']
#     search_fields = ['branch_user__username', 'material__name']
#     readonly_fields = ['created_at']
#     fieldsets = (
#         ('Material Info', {
#             'fields': ('branch_user', 'material', 'quantity')
#         }),
#         ('Damage Info', {
#             'fields': ('damage_type', 'damage_description', 'photos', 'estimated_cost')
#         }),
#         ('Status', {
#             'fields': ('status', 'admin_note')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )
#     date_hierarchy = 'created_at'

# admin.site.register(DamageMaterial, DamageMaterialAdmin)
