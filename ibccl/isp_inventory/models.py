from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime

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
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
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

    def __str__(self):
        stock_indicator = " (in stock)" if self.quantity > 0 else ""
        return f"{self.name}{stock_indicator}"

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
        now = timezone.datetime(2026, 3, 31)  # For testing, we can set this to a specific date. In production, use timezone.now()
        current_month = datetime(now.year, now.month, 1)
        
        monthly_count, created = MaterialMonthlyCount.objects.get_or_create(
            material=self,
            month=current_month,
            defaults={'count': 0}
        )
        
        # Reset count if it's a new month
        if created:
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

class Task(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Completed', 'Completed')]
    title = models.CharField(max_length=200)
    customer = models.CharField(max_length=100)
    address = models.TextField()
    Branch = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


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
    STATUS_CHOICES = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')]
    REQUEST_TYPE_CHOICES = [('Regular', 'Regular'), ('Advance', 'Advance')]
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='material_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='material_requests')
    quantity = models.IntegerField()
    notes = models.TextField(blank=True) # Deprecated logic potentially, but keeping for compatibility
    send_by = models.TextField(blank=True) # Explicit User Note
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='Regular')  # Regular or Advance
    admin_note = models.CharField(max_length=200, blank=True) #material quantity update note
    received_by = models.TextField(blank=True) # Who received the material (filled by branch user when approved)
    received_at = models.DateTimeField(null=True, blank=True) # When the received_by was last updated
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.requester} - {self.material.name}"
    
    @property
    def used_materials_count(self):
        """Return count of used materials linked to this request."""
        return self.used_materials.count()
    
    @property
    def used_materials_display(self):
        """Return comma-separated list of used material quantities."""
        items = self.used_materials.all()
        if not items:
            return '-'
        return ', '.join([f"{item.quantity}x {item.material.name}" for item in items])  

class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.key

class NotificationSetting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    low_stock_alert = models.BooleanField(default=True)
    new_request_alert = models.BooleanField(default=True)
    task_assignment_alert = models.BooleanField(default=True)

    def __str__(self):
        return f"Notifications for {self.user.username}"


class UsedMaterial(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')]
    
    # Technician and Material References
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_materials')
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='used_instances')
    # Client Information
    client_name = models.CharField(max_length=200, blank=True, verbose_name='Client Name')
    client_address = models.TextField(blank=True, verbose_name='Client Address')
    client_phone = models.CharField(max_length=20, blank=True, verbose_name='Client Phone')
    # Material Usage Details
    quantity = models.IntegerField(default=1)
    issue = models.TextField(blank=True, verbose_name='Technical Issue / Notes')
    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Accepted')
    admin_note = models.TextField(blank=True, verbose_name='Admin Notes')
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-added_at']
        verbose_name = 'Used Material'
        verbose_name_plural = 'Used Materials'
        indexes = [
            models.Index(fields=['technician', '-added_at']),
            models.Index(fields=['material', '-added_at']),
            models.Index(fields=['status']),
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
    
    def __str__(self):
        return f"{self.technician_full_name} - {self.material_name} ({self.quantity}x) - {self.added_at.strftime('%Y-%m-%d')}"
    
class backupandrestore(models.Model):
    backup_file = models.FileField(upload_to='backups/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Backup from {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


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