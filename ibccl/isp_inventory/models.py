from django.contrib.auth.models import User
from django.db import models

# Extend User with Role
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Storekeeper', 'Storekeeper'),
        ('Technician', 'Technician'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Technician')

    def __str__(self):
        return f"{self.user.username} - {self.role}"    

class Material(models.Model):
    CATEGORY_CHOICES = [
        ('Internet', 'Internet'),
        ('Dish', 'Dish'),
    ]
    name = models.CharField(max_length=100, unique=True)#can't allow duplicate name 
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    quantity = models.IntegerField(default=0)
    min_stock_level = models.IntegerField(default=10)
    notes = models.TextField(blank=True)
    STATUS_CHOICES = [
        ('Normal', 'Normal'),
        ('Low Stock', 'Low Stock'),
        ('Out of Stock', 'Out of Stock'),
        ('Reserved', 'Reserved'),
        ('Deprecated', 'Deprecated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Normal')
    added_by = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    @property
    def added_by_display(self):
        """Return a friendly display for `added_by`.

        `added_by` stores a username string. Prefer the User's full name
        when available, otherwise fall back to username or the raw value.
        """
        if not self.added_by:
            return ''
        try:
            user = User.objects.filter(username=self.added_by).first()
            if user:
                full = (user.first_name or '') + (' ' + user.last_name if user.last_name else '')
                full = full.strip()
                return full or user.username
        except Exception:
            pass
        return self.added_by

    @property
    def stock_status(self):
        """Map the display status to a code used for filtering/styling."""
        if self.status == 'Low Stock': return 'low'
        if self.status == 'Normal': return 'normal'
        if self.status == 'Out of Stock': return 'out_of_stock'
        return 'normal'

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
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class MaterialRequest(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')]
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='material_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='material_requests')
    quantity = models.IntegerField()
    notes = models.TextField(blank=True) # Deprecated logic potentially, but keeping for compatibility
    user_note = models.TextField(blank=True) # Explicit User Note
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_note = models.CharField(max_length=200, blank=True) #material quantity update note
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
    
class Vendor(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

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
    material_request = models.ForeignKey(MaterialRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_materials')
    
    # Material Details (auto-populated from Material model)
    # category is accessed via material.category property
    
    # Client Information
    client_name = models.CharField(max_length=200, blank=True, verbose_name='Client Name')
    client_address = models.TextField(blank=True, verbose_name='Client Address')
    client_phone = models.CharField(max_length=20, blank=True, verbose_name='Client Phone')
    
    # Material Usage Details
    quantity = models.IntegerField(default=1)
    issue = models.TextField(blank=True, verbose_name='Technical Issue / Notes')
    
    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
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
        """Return the name of the related material."""
        return self.material.name if self.material else ''
    
    @property
    def technician_full_name(self):
        """Return the full name of the technician."""
        return self.technician.get_full_name() or self.technician.username
    
    def __str__(self):
        return f"{self.technician_full_name} - {self.material_name} ({self.quantity}x) - {self.added_at.strftime('%Y-%m-%d')}"