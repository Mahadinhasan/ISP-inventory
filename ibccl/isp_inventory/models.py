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
    name = models.CharField(max_length=100)
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
    added_by = models.TextField(blank=True)
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
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    requester = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.requester} - {self.material.name}"
    
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
    technician = models.ForeignKey(User, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_note = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.technician.username} - {self.material.name}"