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


# ── TRASH & RECOVERY UTILITIES ───────────────────────────────────────────
import json
from django.core.serializers.json import DjangoJSONEncoder


def move_to_trash(user, item_type, item_name, instance=None, extra_data=None):
    """
    Serializes a model instance and records a TrashItem entry.
    Items remain in Trash for 30 days before auto permanent delete.
    """
    from .models import TrashItem, models
    data = {}
    model_name = ''
    obj_id = None
    if instance:
        model_name = instance.__class__.__name__
        obj_id = getattr(instance, 'pk', None)
        for field in instance._meta.fields:
            val = getattr(instance, field.name)
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                val = val.pk if val else None
            elif isinstance(val, (datetime, timezone.datetime)):
                val = val.isoformat()
            data[field.name] = val
    
    if extra_data:
        data['_extra'] = extra_data

    role = 'Branch'
    if user and hasattr(user, 'userprofile'):
        role = user.userprofile.role
    elif user and user.is_superuser:
        role = 'Admin'

    now = timezone.now()
    expires_at = now + timezone.timedelta(days=30)

    trash_item = TrashItem.objects.create(
        user=user,
        user_role=role,
        item_type=item_type,
        item_name=item_name,
        model_name=model_name,
        object_id=obj_id,
        serialized_data=json.dumps(data, cls=DjangoJSONEncoder),
        deleted_at=now,
        expires_at=expires_at
    )
    return trash_item


def create_or_restore_instance(ModelClass, object_id, data, default_overrides=None):
    """
    Safely recreates or restores a model instance using serialized fields,
    filtering out any invalid/non-existent model field names to prevent TypeErrors,
    and mapping foreign keys to field.attname (e.g. technician_id instead of technician)
    so integer IDs are assigned properly without raising Django assignment errors.
    """
    from django.db import models

    valid_fields = set()
    fk_field_map = {}
    for field in ModelClass._meta.fields:
        valid_fields.add(field.name)
        if hasattr(field, 'attname'):
            valid_fields.add(field.attname)
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            fk_field_map[field.name] = field.attname

    filtered_defaults = {}
    if data:
        for k, v in data.items():
            if k.startswith('_'):
                continue
            target_key = fk_field_map.get(k, k)
            if target_key in valid_fields:
                filtered_defaults[target_key] = v

    if default_overrides:
        for k, v in default_overrides.items():
            target_key = fk_field_map.get(k, k)
            if target_key in valid_fields:
                filtered_defaults[target_key] = v

    pk_name = ModelClass._meta.pk.name
    filtered_defaults.pop(pk_name, None)
    filtered_defaults.pop(ModelClass._meta.pk.attname, None)

    inst = None
    created = False
    if object_id:
        try:
            inst = ModelClass.objects.get(pk=object_id)
            for k, v in filtered_defaults.items():
                setattr(inst, k, v)
            inst.save()
        except ModelClass.DoesNotExist:
            inst = ModelClass.objects.create(id=object_id, **filtered_defaults)
            created = True
    else:
        inst = ModelClass.objects.create(**filtered_defaults)
        created = True

    return inst, created


def restore_trash_item(trash_item, user=None):
    """
    Restores an item from Trash back to its original model table.
    """
    if trash_item.is_restored or trash_item.is_permanently_deleted:
        return False, "Item is already restored or permanently deleted."

    if not trash_item.serialized_data:
        trash_item.is_restored = True
        trash_item.save()
        return True, "Item marked as restored."

    try:
        data = json.loads(trash_item.serialized_data)
    except Exception:
        data = {}

    extra = data.get('_extra', {})
    model_name = trash_item.model_name

    from .models import (
        Material, MaterialRequest, UsedMaterial, RefundableMaterial,
        RefundableMaterialUsage, DamageMaterial, MacSerialNumber
    )
    from django.contrib.auth.models import User

    try:
        if model_name == 'Material':
            mat, created = create_or_restore_instance(Material, trash_item.object_id, data, {'is_deleted': False})

        elif model_name == 'MaterialRequest':
            req, created = create_or_restore_instance(MaterialRequest, trash_item.object_id, data, {'is_hidden_by_admin': False, 'is_hidden_by_noc': False})

        elif model_name == 'UsedMaterial':
            um, created = create_or_restore_instance(UsedMaterial, trash_item.object_id, data)
            if um.mac_serial:
                sync_mac_serial_status(um.mac_serial)

        elif model_name == 'RefundableMaterial':
            rf, created = create_or_restore_instance(RefundableMaterial, trash_item.object_id, data)

        elif model_name == 'RefundableMaterialUsage':
            rfu, created = create_or_restore_instance(RefundableMaterialUsage, trash_item.object_id, data)

        elif model_name == 'DamageMaterial':
            dm, created = create_or_restore_instance(DamageMaterial, trash_item.object_id, data)

        elif model_name == 'MacSerialNumber':
            mac, created = create_or_restore_instance(MacSerialNumber, trash_item.object_id, data)

        elif model_name == 'User':
            try:
                u = User.objects.get(id=trash_item.object_id)
                u.is_active = True
                u.save()
            except User.DoesNotExist:
                u = User.objects.create(
                    id=trash_item.object_id,
                    username=data.get('username', trash_item.item_name),
                    email=data.get('email', ''),
                    first_name=data.get('first_name', ''),
                    last_name=data.get('last_name', ''),
                    is_active=True
                )
                ensure_userprofile(u)
                if extra.get('profile_role'):
                    u.userprofile.role = extra.get('profile_role')
                    u.userprofile.save()

        trash_item.is_restored = True
        trash_item.save()
        return True, f"Successfully restored '{trash_item.item_name}'."
    except Exception as e:
        return False, f"Restore failed: {str(e)}"


def cleanup_expired_trash():
    """
    Automatically marks items expired (>30 days) as permanently deleted.
    """
    from .models import TrashItem
    now = timezone.now()
    TrashItem.objects.filter(
        expires_at__lte=now,
        is_restored=False,
        is_permanently_deleted=False
    ).update(is_permanently_deleted=True)


