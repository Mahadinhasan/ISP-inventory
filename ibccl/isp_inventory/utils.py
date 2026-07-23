from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import datetime
from .models import UserProfile, Material, MaterialMonthlyCount

ROLE_GROUPS = ['Admin', 'Storekeeper', 'Branch', 'NOC']


def ensure_userprofile(user):
    """Ensure a UserProfile exists for `user` and return it.

    This function is defensive: it handles the case where the reverse
    OneToOne accessor (`user.userprofile`) does not exist yet and will
    create a `UserProfile` using the first matching role-group or the
    default role `'Branch'`.
    """
    if user is None or user.pk is None:
        return None

    # Try to access the reverse relation safely
    try:
        profile = user.userprofile
        if profile:
            return profile
    except Exception:
        profile = None

    # Infer role from group membership if possible
    role_name = None
    try:
        grp = user.groups.filter(name__in=ROLE_GROUPS).first()
        if grp:
            role_name = grp.name
    except Exception:
        role_name = None

    if not role_name:
        role_name = 'Branch'

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role_name})
    return profile


def deduct_material_stock(material, qty):
    """Deduct approved quantity from material stock.

    The function deducts from `quantity` first and only uses
    `Remaining_stock` when necessary.
    """
    if qty <= material.quantity:
        material.quantity -= qty
    else:
        diff = qty - material.quantity
        material.quantity = 0
        material.Remaining_stock = max(material.Remaining_stock - diff, 0)
    material.save()


def restore_material_stock(material, qty):
    """Restore material stock when a request is rejected.

    This only returns the requested quantity to the in-stock amount.
    """
    material.quantity += qty
    material.save()


def sync_mac_serial_status(mac_serial):
    """
    Synchronizes the status of a MacSerialNumber based on all UsedMaterial and DamageMaterial records.

    Rules:
    1. If used in any Accepted UsedMaterial -> status = 'Used', is_ever_accepted = True
    2. Else if used in any Confirmed DamageMaterial -> status = 'Retired'
    3. Else -> status = 'Active'
    """
    if not mac_serial:
        return

    from .models import UsedMaterial, DamageMaterial

    # Check if attached to any Accepted UsedMaterial
    if UsedMaterial.objects.filter(mac_serial=mac_serial, status='Accepted', is_archived=False).exists():
        mac_serial.status = 'Used'
        mac_serial.is_ever_accepted = True
        mac_serial.save(update_fields=['status', 'is_ever_accepted'])
        return

    # Check if attached to any Confirmed DamageMaterial
    if DamageMaterial.objects.filter(mac_serial=mac_serial, status='Confirmed').exists():
        mac_serial.status = 'Retired'
        mac_serial.save(update_fields=['status'])
        return

    # Otherwise return to Active pool
    mac_serial.status = 'Active'
    mac_serial.save(update_fields=['status'])



# ==================== MONTHLY COUNT UTILITIES ====================

def get_current_month_date():
    """Get the first day of current month."""
    now = timezone.now()
    return datetime(now.year, now.month, 1)


def get_material_monthly_count(material, month_date=None):
    """
    Get or create monthly count for a material.
    
    Args:
        material: Material instance
        month_date: datetime object (defaults to current month)
    
    Returns:
        MaterialMonthlyCount instance with count value
    """
    if month_date is None:
        month_date = get_current_month_date()
    
    monthly_count, _ = MaterialMonthlyCount.objects.get_or_create(
        material=material,
        month=month_date.date(),
        defaults={'count': 0}
    )
    return monthly_count


def increment_material_count(material, quantity=1, month_date=None):
    """
    Increment monthly count for a material.
    
    Args:
        material: Material instance
        quantity: Amount to increment (default: 1)
        month_date: datetime object (defaults to current month)
    
    Returns:
        Updated MaterialMonthlyCount instance
    """
    if month_date is None:
        month_date = get_current_month_date()
    
    monthly_count = get_material_monthly_count(material, month_date)
    monthly_count.count += quantity
    monthly_count.save()
    return monthly_count


def reset_material_monthly_count(material, month_date=None):
    """
    Reset monthly count to 0 for end of month.
    
    Args:
        material: Material instance
        month_date: datetime object (defaults to current month)
    
    Returns:
        Reset MaterialMonthlyCount instance
    """
    if month_date is None:
        month_date = get_current_month_date()
    
    monthly_count = get_material_monthly_count(material, month_date)
    monthly_count.count = 0
    monthly_count.save()
    return monthly_count


def get_monthly_count_summary(month_date=None):
    """
    Get summary of all materials' monthly counts.
    
    Args:
        month_date: datetime object (defaults to current month)
    
    Returns:
        QuerySet of MaterialMonthlyCount with counts > 0
    """
    if month_date is None:
        month_date = get_current_month_date()
    
    return MaterialMonthlyCount.objects.filter(
        month=month_date.date()
    ).select_related('material').order_by('-count')


def reset_all_monthly_counts(month_date=None):
    """
    Reset all monthly counts at month end.
    
    Args:
        month_date: datetime object (defaults to current month)
    
    Returns:
        Count of materials reset
    """
    if month_date is None:
        month_date = get_current_month_date()
    
    reset_count = 0
    materials = Material.objects.all()
    
    for material in materials:
        reset_material_monthly_count(material, month_date)
        reset_count += 1
    
    return reset_count

