from django.contrib import admin
from .models import (
    Material, MaterialRequest, UserProfile, SystemSetting, NotificationSetting,
    UsedMaterial, BackupRestore, ActivityLog, LogSettings, MacSerialNumber,
    MaterialMacSerialImport, RefundableMaterial, RefundableMaterialUsage, DamageMaterial
)

# Custom admin classes for better display

class MaterialRequestAdmin(admin.ModelAdmin):
    """Admin interface for MaterialRequest with role-based stock filtering."""
    list_display = ['id', 'requester', 'get_requester_role', 'material', 'quantity', 'rate', 'total_price', 'status', 'request_type', 'requested_at']
    list_filter = ['status', 'request_type', 'requester__userprofile__role', 'material__category', 'requested_at']
    list_select_related = ['requester', 'requester__userprofile', 'material']
    search_fields = ['requester__username', 'material__name', 'send_by', 'notes']
    readonly_fields = ['requested_at', 'pass_on_at', 'received_at']
    show_full_result_count = False
    
    def get_requester_role(self, obj):
        if hasattr(obj.requester, 'userprofile'):
            return obj.requester.userprofile.role
        return 'N/A'
    get_requester_role.short_description = 'User Role'
    get_requester_role.admin_order_field = 'requester__userprofile__role'

class UsedMaterialAdmin(admin.ModelAdmin):
    """Admin interface for UsedMaterial with request linking."""
    list_display = ['id', 'technician', 'material_name', 'get_category', 'quantity', 'status', 'added_at']
    list_filter = ['status', 'added_at', 'material__category']
    list_select_related = ['technician', 'technician__userprofile', 'material']
    search_fields = ['technician__username', 'material__name', 'client_name', 'material__category']
    readonly_fields = ['added_at', 'updated_at']
    show_full_result_count = False
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
    material_name.admin_order_field = 'material__name'
    
    def get_category(self, obj):
        """Display material category from the Material model."""
        return obj.material.category if obj.material else '-'
    get_category.short_description = 'Category'
    get_category.admin_order_field = 'material__category'

# Register your models here.
class materialAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'Type','quantity','Remaining_stock', 'min_stock_level', 'status', 'updated_at','rate','total_price']
    list_filter = ['category', 'status']
    list_select_related = ['created_by', 'created_by__userprofile']
    search_fields = ['name', 'category']
    show_full_result_count = False
admin.site.register(Material, materialAdmin)
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

class RefundableMaterialAdmin(admin.ModelAdmin):
    list_display = ['id', 'branch_user', 'material_name', 'mac_serial', 'quantity', 'get_available_quantity', 'added_at']
    list_filter = ['added_at', 'branch_user']
    list_select_related = ['branch_user', 'branch_user__userprofile']
    search_fields = ['branch_user__username', 'material_name', 'mac_serial']
    readonly_fields = ['added_at', 'updated_at']
    show_full_result_count = False
    
    def get_queryset(self, request):
        from django.db.models import Sum, F
        from django.db.models.functions import Coalesce
        return super().get_queryset(request).annotate(
            annotated_avail=F('quantity') - Coalesce(Sum('usages__materials_quantity'), 0)
        )
    
    def get_available_quantity(self, obj):
        return getattr(obj, 'annotated_avail', obj.available_quantity)
    get_available_quantity.short_description = 'Available Stock'
    get_available_quantity.admin_order_field = 'annotated_avail'

admin.site.register(RefundableMaterial, RefundableMaterialAdmin)


class RefundableMaterialUsageAdmin(admin.ModelAdmin):
    list_display = ['id', 'refundable_material', 'used_by', 'materials_quantity', 'client_name', 'dispatched_to', 'used_at']
    list_filter = ['used_at', 'used_by']
    list_select_related = ['used_by', 'refundable_material', 'refundable_material__branch_user']
    search_fields = ['used_by__username', 'client_name', 'client_phone', 'dispatched_to', 'issue']
    readonly_fields = ['used_at']
    show_full_result_count = False

admin.site.register(RefundableMaterialUsage, RefundableMaterialUsageAdmin)


class DamageMaterialAdmin(admin.ModelAdmin):
    list_display = ['id', 'branch_user', 'material', 'quantity', 'status', 'damage_reason', 'confirmed_by', 'added_at']
    list_filter = ['status', 'added_at', 'branch_user']
    list_select_related = ['branch_user', 'branch_user__userprofile', 'material', 'confirmed_by']
    search_fields = ['branch_user__username', 'material__name', 'damage_reason', 'admin_note']
    readonly_fields = ['added_at', 'updated_at', 'confirmed_at']
    show_full_result_count = False
    fieldsets = (
        ('Damage Info', {
            'fields': ('branch_user', 'material', 'quantity', 'mac_serial', 'damage_reason')
        }),
        ('Status & Approval', {
            'fields': ('status', 'admin_note', 'confirmed_by', 'confirmed_at')
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(DamageMaterial, DamageMaterialAdmin)

try:
    from .models import TrashItem
    class TrashItemAdmin(admin.ModelAdmin):
        list_display = ['id', 'item_name', 'item_type', 'user', 'user_role', 'is_restored', 'deleted_at', 'expires_at']
        list_filter = ['item_type', 'user_role', 'is_restored', 'deleted_at']
        list_select_related = ['user', 'user__userprofile']
        search_fields = ['item_name', 'user__username', 'model_name']
        readonly_fields = ['deleted_at', 'expires_at', 'serialized_data']
        show_full_result_count = False
    admin.site.register(TrashItem, TrashItemAdmin)
except Exception:
    pass
