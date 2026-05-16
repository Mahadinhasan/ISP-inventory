from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime

from django.core.validators import FileExtensionValidator

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Storekeeper', 'Storekeeper'),
        ('Branch', 'Branch'),
        ('NOC', 'NOC'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile',unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Branch')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    image = models.ImageField(
        upload_to='profile_pics/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'  ])]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    @property
    def username(self):
        return self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    @property
    def profile_image_url(self):
        if self.image:
            return self.image.url
        return '/static/images/default_profile.png'

    @property
    def role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    @property
    def is_admin(self):
        return self.role == 'Admin'

    @property
    def is_storekeeper(self):
        return self.role == 'Storekeeper'

    @property
    def is_branch(self):
        return self.role == 'Branch'

    @property
    def is_noc(self):
        return self.role == 'NOC'

    def get_permissions(self):
        permissions = {
            'Admin': ['create', 'read', 'update', 'delete', 'manage_users', 'manage_settings'],
            'Storekeeper': ['create', 'read', 'update', 'manage_inventory', 'approve_requests'],
            'Branch': ['read', 'create_request', 'use_material'],
            'NOC': ['read', 'create_task', 'update_task'],
        }
        return permissions.get(self.role, [])

    def has_permission(self, permission):
        return permission in self.get_permissions()

    def update_last_login(self):
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])

    def save(self, *args, **kwargs):
        if not self.last_login and self.user.last_login:
            self.last_login = self.user.last_login
        super().save(*args, **kwargs)

class Material(models.Model):
    CATEGORY_CHOICES = [
        ('Internet', 'Internet'),
        ('Dish', 'Dish'),
        ('Fiber', 'Fiber'),
        ('Common item', 'Common item'),
        ('Work shop', 'Work shop'),
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    TYPE_CHOICES = [
        ('Meter', 'Meter'),
        ('Piece', 'Piece'),
    ]
    Type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='Piece')
    quantity = models.IntegerField(default=0)
    rate = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0, blank=True)
    Remaining_stock = models.IntegerField(default=0)
    min_stock_level = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    STATUS_CHOICES = [
        ('Normal', 'Normal'),
        ('Low Stock', 'Low Stock'),
        ('Out of Stock', 'Out of Stock'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Normal')
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_materials')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        stock_indicator = " (in stock)" if self.quantity > 0 else ""
        return f"{self.name}{stock_indicator}"

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    @property
    def stock_status(self):
        """Map the display status to a code used for filtering/styling."""
        if self.status == 'Low Stock': return 'low'
        if self.status == 'Normal': return 'normal'
        if self.status == 'Out of Stock': return 'out_of_stock'
        return 'normal'
    
    @property
    def is_in_stock(self):
        """Check if material has quantity greater than 0."""
        return self.quantity > 0
    
    def get_monthly_count(self):
        """Get or create monthly count for current month."""
        now = timezone.now()  # For testing, we can set this to a specific date. In production, use timezone.now()
        current_month = datetime(now.year, now.month, 1)
        
        monthly_count, created = MaterialMonthlyCount.objects.get_or_create(
            material=self,
            month=current_month,
            defaults={'count': 0}
        )
        
        # Reset count if it's a new month, unless role is NOC
        if created:
            is_noc = self.created_by and hasattr(self.created_by, 'userprofile') and self.created_by.userprofile.role == 'NOC'
            if is_noc:
                prev = self.get_previous_month_count()
                monthly_count.count = prev.count if prev else self.quantity
            else:
                monthly_count.count = 0
            monthly_count.save()
        
        return monthly_count
    
    def increment_monthly_count(self, increment_by=1):
        """Increment monthly count."""
        monthly_count = self.get_monthly_count()
        monthly_count.count += increment_by
        monthly_count.save()
        return monthly_count
    
    def reset_monthly_count(self):
        """Reset monthly count to 0."""
        # For NOC materials, do not reset
        if self.created_by and hasattr(self.created_by, 'userprofile') and self.created_by.userprofile.role == 'NOC':
            return self.get_monthly_count()
            
        monthly_count = self.get_monthly_count()
        monthly_count.count = 0
        monthly_count.save()
        return monthly_count
    
    def get_previous_month_count(self):
        """Get previous month's count."""
        now = timezone.now()
        previous_month = now - relativedelta(months=1)
        previous_month_date = datetime(previous_month.year, previous_month.month, 1)
        
        try:
            monthly_count = MaterialMonthlyCount.objects.get(
                material=self,
                month=previous_month_date
            )
            return monthly_count.count
        except MaterialMonthlyCount.DoesNotExist:
            return 0

    def save(self, *args, **kwargs):
        """Synchronize `status` with `quantity` vs `min_stock_level`.

        Rules:
        - quantity <= 0 -> 'Out of Stock'
        - 0 < quantity < min_stock_level -> 'Low Stock'
        - quantity >= min_stock_level -> 'Normal' (unless status is Reserved/Deprecated)
        """
        try:
            if self.quantity is None:
                self.quantity = 0
            
            # Calculate total price
            if self.rate is None:
                self.rate = 0
            self.total_price = self.quantity * self.rate

            if self.quantity <= 0:
                self.status = 'Out of Stock'
            elif self.quantity < (self.min_stock_level or 0):
                self.status = 'Low Stock'
            else:
                if self.status not in ('Reserved', 'Deprecated'):
                    self.status = 'Normal'
        except Exception:
            pass
        super().save(*args, **kwargs)

# class Task(models.Model):
#     STATUS_CHOICES = [('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Completed', 'Completed')]
#     title = models.CharField(max_length=200)
#     customer = models.CharField(max_length=100)
#     address = models.TextField()
#     Branch = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title


class MaterialMonthlyCount(models.Model):
    """Track monthly quantity count for materials with auto-reset functionality."""
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='monthly_counts')
    month = models.DateField(help_text="First day of the month for which count is tracked")
    count = models.IntegerField(default=0, help_text="Monthly count that resets at month end")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('material', 'month')
        ordering = ['-month']
        verbose_name = 'Material Monthly Count'
        verbose_name_plural = 'Material Monthly Counts'
        indexes = [
            models.Index(fields=['material', '-month']),
            models.Index(fields=['month']),
        ]
    
    def __str__(self):
        return f"{self.material.name} - {self.month.strftime('%B %Y')} (Count: {self.count})"
    
    def reset(self):
        """Reset count to 0 for month end."""
        self.count = 0
        self.save()
        return self
    
    @property
    def month_display(self):
        """Return month in readable format."""
        return self.month.strftime('%B %Y')
    
    @property
    def is_current_month(self):
        """Check if this is the current month."""
        now = timezone.now()
        return self.month.year == now.year and self.month.month == now.month

class MaterialRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Dispatched', 'Dispatched'),
        ('Received', 'Received'),
        ('Rejected', 'Rejected')
    ]
    REQUEST_TYPE_CHOICES = [('Regular', 'Regular'), ('Advance', 'Advance')]
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='material_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='material_requests')
    quantity = models.IntegerField()
    rate = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0, blank=True)
    notes = models.TextField(blank=True) # Deprecated logic potentially, but keeping for compatibility
    send_by = models.TextField(blank=True) # Explicit User Note
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='Regular')  # Regular or Advance
    admin_note = models.CharField(max_length=200, blank=True) #material quantity update note
    pass_on = models.TextField(blank=True) # Who transmitted the material (filled by storekeeper when approved)
    pass_on_at = models.DateTimeField(null=True, blank=True) # When the pass_on was last updated
    received_by = models.TextField(blank=True) # Who received the material (filled by branch user when approved)
    received_at = models.DateTimeField(null=True, blank=True) # When the received_by was last updated
    requested_at = models.DateTimeField(auto_now_add=True)
    # Track where stock was deducted from for accurate returns on rejection
    deducted_from_quantity = models.IntegerField(default=0)
    deducted_from_remaining = models.IntegerField(default=0)
    # Archive System Fields
    is_archived = models.BooleanField(default=False, help_text="Auto-archived for previous months")
    archived_at = models.DateTimeField(null=True, blank=True, help_text="When the request was archived")

    def __str__(self):
        return f"{self.requester} - {self.material.name}"
    
    @property
    def can_receive(self):
        """Branch can receive only if status is Approved and pass_on is filled by storekeeper."""
        return self.status == 'Approved' and bool(self.pass_on.strip())
    
    @property
    def used_materials_count(self):
        """Return count of used materials linked to this request."""
        return self.used_materials.filter(status='Accepted').count()
    
    @property
    def used_materials_display(self):
        """Return comma-separated list of used material quantities."""
        items = self.used_materials.all()
        if not items:
            return '-'
        return ', '.join([f"{item.quantity}x {item.material.name}" for item in items])

    @property
    def estimated_amount(self):
        """Estimated amount = approved quantity × material rate."""
        try:
            return self.quantity * (self.material.rate or 0)
        except Exception:
            return 0

    def save(self, *args, **kwargs):
        # Automatically update status to Dispatched when storekeeper adds pass_on
        if self.pk:
            try:
                old_request = MaterialRequest.objects.get(pk=self.pk)
                if (old_request.status == 'Approved' and 
                    not old_request.pass_on.strip() and 
                    self.pass_on.strip()):
                    self.status = 'Dispatched'
                    self.pass_on_at = timezone.now()
                elif old_request.pass_on.strip() != self.pass_on.strip():
                    self.pass_on_at = timezone.now()
                if old_request.received_by.strip() != self.received_by.strip():
                    self.received_at = timezone.now()
            except MaterialRequest.DoesNotExist:
                pass
        elif self.pass_on.strip():
            self.pass_on_at = timezone.now()
        if self.received_by.strip():
            self.received_at = timezone.now()
        super().save(*args, **kwargs)


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.key

class NotificationSetting(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_setting')
    
    # Email & General
    email_notifications = models.BooleanField(default=True, help_text="Receive email notifications")
    in_app_notifications = models.BooleanField(default=True, help_text="Show in-app notifications")
    
    # Request & Approval
    request_approved_alert = models.BooleanField(default=True, help_text="Notify when request is approved")
    request_rejected_alert = models.BooleanField(default=True, help_text="Notify when request is rejected")
    new_request_alert = models.BooleanField(default=True, help_text="Notify on new material requests")
    
    # Stock & Inventory
    low_stock_alert = models.BooleanField(default=True, help_text="Alert when stock is low")
    out_of_stock_alert = models.BooleanField(default=True, help_text="Alert when item is out of stock")
    material_destroyed_alert = models.BooleanField(default=True, help_text="Notify when material is destroyed")
    
    # Tasks & Assignments
    task_assignment_alert = models.BooleanField(default=True, help_text="Notify when task is assigned")
    task_completed_alert = models.BooleanField(default=True, help_text="Notify when task is completed")
    
    # Messages
    message_alert = models.BooleanField(default=True, help_text="Notify on new messages")
    
    # System
    backup_alert = models.BooleanField(default=True, help_text="Notify on backup operations")
    system_alert = models.BooleanField(default=False, help_text="System-level alerts")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Setting"
        verbose_name_plural = "Notification Settings"

    def __str__(self):
        return f"Notifications for {self.user.username}"


class UsedMaterial(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')]
    
    # Technician and Material References
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_materials')
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='used_instances')
    material_request = models.ForeignKey('MaterialRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_materials', help_text="Associated MaterialRequest from branch user")
    # Client Information
    client_name = models.CharField(max_length=200, blank=True, verbose_name='Client Name')
    client_address = models.TextField(blank=True, verbose_name='Client Address')
    client_phone = models.CharField(max_length=20, blank=True, verbose_name='Client Phone')
    # Material Usage Details
    mac_serial = models.ForeignKey('MacSerialNumber', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_records', help_text="Specific Mac/Serial number used")
    quantity = models.IntegerField(default=1)
    issue = models.TextField(blank=True, verbose_name='Technical Issue / Notes')
    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_note = models.TextField(blank=True, verbose_name='Admin Notes')
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Archive System Fields
    is_archived = models.BooleanField(default=False, help_text="Auto-archived for previous months")
    archived_at = models.DateTimeField(null=True, blank=True, help_text="When the used material was archived")
    
    class Meta:
        ordering = ['-added_at']
        verbose_name = 'Used Material'
        verbose_name_plural = 'Used Materials'
        indexes = [
            models.Index(fields=['technician', '-added_at']),
            models.Index(fields=['material', '-added_at']),
            models.Index(fields=['status']),
            models.Index(fields=['material_request', 'technician']),
        ]

    @property
    def category(self):
        """Return the category of the related material."""
        return self.material.category if self.material else ''
    
    @property
    def material_name(self):
        """Return the name of the related material from Material model."""
        return self.material.name if self.material else ''
    
    @property
    def technician_full_name(self):
        """Return the full name of the technician."""
        return self.technician.get_full_name() or self.technician.username
    
    def save(self, *args, **kwargs):
        # Default empty fields to 'N/A' as requested
        if not self.client_name:
            self.client_name = 'N/A'
        if not self.client_address:
            self.client_address = 'N/A'
        if not self.client_phone:
            self.client_phone = 'N/A'
        if not self.issue:
            self.issue = 'N/A'
        super().save(*args, **kwargs)

    def __str__(self):
        request_info = f" [Req#{self.material_request.id}]" if self.material_request else ""
        return f"{self.technician_full_name} - {self.material_name} ({self.quantity}x) - {self.added_at.strftime('%Y-%m-%d')}{request_info}"


class BackupRestore(models.Model):
    """Professional Backup & Restore model with role-based access and recovery"""
    BACKUP_TYPES = [
        ('full', 'Full Backup'),
        ('partial', 'Partial Backup'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deleted', 'Deleted (Recoverable)'),
        ('purged', 'Permanently Purged'),
    ]

    # Backup metadata
    backup_file = models.FileField(upload_to='backups/%Y/%m/%d/')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='backups_created')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Backup details
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES, default='full')
    backup_size = models.BigIntegerField(default=0, help_text="Size in bytes")
    description = models.TextField(blank=True, null=True, help_text="Optional backup description")
    
    # Recovery tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='backups_deleted')
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='backups_restored')
    
    # Audit fields
    data_records_count = models.IntegerField(default=0, help_text="Number of data records in backup")
    checksum = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 checksum for integrity verification")
    notes = models.TextField(blank=True, null=True, help_text="Admin notes about this backup")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Backup & Restore"
        verbose_name_plural = "Backups & Restores"

    def __str__(self):
        creator = self.created_by.username if self.created_by else "System"
        return f"{self.backup_type.capitalize()} Backup by {creator} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def is_recoverable(self):
        """Check if backup can be recovered"""
        return self.status in ['active', 'deleted']
    
    @property
    def is_recoverable_deleted(self):
        """Check if deleted backup can be recovered"""
        return self.status == 'deleted'
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.backup_size < 1024:
                return f"{self.backup_size:.2f} {unit}"
            self.backup_size /= 1024
        return f"{self.backup_size:.2f} TB"


class ActivityLog(models.Model):
    """Track user activities like login, logout, and actions"""
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('create', 'Create Action'),
        ('update', 'Update Action'),
        ('delete', 'Delete Action'),
        ('approve', 'Approval Action'),
        ('reject', 'Rejection Action'),
        ('download', 'Download Action'),
        ('restore', 'Restore Action'),
        ('other', 'Other Action'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, default='other')
    description = models.TextField(blank=True, help_text="Action description")
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="User's IP address")
    user_agent = models.TextField(blank=True, help_text="Browser/Device info")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class LogSettings(models.Model):
    """System-wide logging configuration"""
    LOG_LEVELS = [
        ('DEBUG', 'Debug - Detailed information'),
        ('INFO', 'Info - General information'),
        ('WARNING', 'Warning - Warning messages'),
        ('ERROR', 'Error - Error messages'),
        ('CRITICAL', 'Critical - Critical errors'),
    ]
    
    log_level = models.CharField(max_length=20, choices=LOG_LEVELS, default='INFO')
    enable_file_logging = models.BooleanField(default=True, help_text="Save logs to file")
    enable_database_logging = models.BooleanField(default=True, help_text="Save activity logs to database")
    log_user_activities = models.BooleanField(default=True, help_text="Track user login/logout")
    log_file_path = models.CharField(max_length=500, default='logs/app.log', help_text="Path where logs are saved")
    max_log_file_size = models.IntegerField(default=10485760, help_text="Max log file size in bytes (10MB default)")
    backup_count = models.IntegerField(default=5, help_text="Number of backup log files to keep")
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='log_settings_changes')
    
    class Meta:
        verbose_name = "Log Settings"
        verbose_name_plural = "Log Settings"
    
    def __str__(self):
        return f"Log Settings - Level: {self.log_level}"


class InternalMessage(models.Model):
    """Upcoming feature: Internal Communication / SMS"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(verbose_name="Message Content")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"


class MacSerialNumber(models.Model):
    """Store Mac/Serial numbers for materials assigned to branch users"""
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Used', 'Used'),
        ('Transferred', 'Transferred'),
        ('Retired', 'Retired'),
    ]

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='mac_serials')
    mac_serial = models.CharField(max_length=255, unique=True, help_text="Unique Mac/Serial number")
    quantity = models.IntegerField(default=1, help_text="Quantity for this mac/serial")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_mac_serials', help_text="Branch user this is assigned to")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active', help_text="Current status of this Mac/Serial entry")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_mac_serials', help_text="NOC user who added this")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mac/Serial Number'
        verbose_name_plural = 'Mac/Serial Numbers'
        indexes = [
            models.Index(fields=['material', '-created_at']),
            models.Index(fields=['assigned_to', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.material.name} - {self.mac_serial}"
    
    @property
    def material_name(self):
        """Return material name"""
        return self.material.name if self.material else 'N/A'
    
    @property
    def assigned_to_username(self):
        """Return assigned user's username"""
        return self.assigned_to.username if self.assigned_to else 'Unassigned'


class MaterialMacSerialImport(models.Model):
    """Track Mac/Serial import transactions from NOC to Branch users"""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='mac_serial_imports')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mac_serial_imports', help_text="Branch user receiving the materials")
    noc_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_mac_serial_imports', help_text="NOC user who created this import")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_quantity = models.IntegerField(default=1, help_text="Total quantity for this import")
    mac_serials_count = models.IntegerField(default=0, help_text="Number of mac/serial entries")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_mac_serial_imports', help_text="Who approved this import")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Material Mac/Serial Import'
        verbose_name_plural = 'Material Mac/Serial Imports'
        indexes = [
            models.Index(fields=['assigned_to', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.material.name} - {self.assigned_to.username} - {self.status}"
    
    @property
    def material_name(self):
        """Return material name"""
        return self.material.name if self.material else 'N/A'
    
    @property
    def branch_user_name(self):
        """Return branch user's full name"""
        if self.assigned_to:
            return self.assigned_to.get_full_name() or self.assigned_to.username
        return 'N/A'
    
    @property
    def noc_user_name(self):
        """Return NOC user's full name"""
        if self.noc_user:
            return self.noc_user.get_full_name() or self.noc_user.username
        return 'N/A'

# class returnMaterial(models.Model):
#     STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('Approved', 'Approved'),
#         ('Rejected', 'Rejected'),
#     ]
    
#     material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='material_returns')
#     assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='material_returns', help_text="Branch user returning the materials")
#     noc_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_material_returns', help_text="NOC user who created this return")
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
#     total_quantity = models.IntegerField(default=1, help_text="Total quantity for this return")
#     notes = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     approved_at = models.DateTimeField(null=True, blank=True)
#     approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_material_returns', help_text="Who approved this return")
    
#     class Meta:
#         ordering = ['created_at']
#         verbose_name = 'Material Return'
#         verbose_name_plural = 'Material Returns'
#         indexes = [
#             models.Index(fields=['assigned_to', 'created_at']),
#             models.Index(fields=['status', 'created_at']),
#         ]
    
#     def __str__(self):
#         return f"{self.material.name} - {self.assigned_to.username} - {self.status}"