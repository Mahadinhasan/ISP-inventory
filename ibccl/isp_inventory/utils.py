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


# ── AUTO DATA BACKUP SYSTEM (Weekly at 2 AM -> Auto data_backup folder) ──────
import os
from django.conf import settings

AUTO_BACKUP_DIR = os.path.join(settings.BASE_DIR, 'Auto data_backup')

def get_auto_backup_config():
    """Retrieve auto backup settings from SystemSetting table."""
    from .models import SystemSetting
    enabled_obj = SystemSetting.objects.filter(key='auto_backup_enabled').first()
    day_obj = SystemSetting.objects.filter(key='auto_backup_day').first()
    time_obj = SystemSetting.objects.filter(key='auto_backup_time').first()
    last_run_obj = SystemSetting.objects.filter(key='auto_backup_last_run').first()

    return {
        'enabled': enabled_obj.value.lower() == 'true' if enabled_obj else True,
        'day': day_obj.value if day_obj else 'Sunday',
        'time': time_obj.value if time_obj else '02:00',
        'last_run': last_run_obj.value if last_run_obj else 'Never',
        'path': AUTO_BACKUP_DIR,
    }

def run_auto_backup(user=None, trigger_type='scheduled'):
    """
    Executes an automated or manual backup saved directly to 'Auto data_backup' folder.
    """
    import os
    import json
    import hashlib
    from io import StringIO
    from django.core.management import call_command
    from django.utils import timezone
    from .models import SystemSetting, ActivityLog

    os.makedirs(AUTO_BACKUP_DIR, exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"auto_backup_{timestamp}.json"
    file_path = os.path.join(AUTO_BACKUP_DIR, filename)

    exclude_models = ['auth.permission', 'contenttypes', 'admin.logentry', 'sessions.session']

    out = StringIO()
    call_command('dumpdata', exclude=exclude_models, stdout=out, indent=2)
    backup_data = out.getvalue()

    if not backup_data:
        raise ValueError("No data returned during dumpdata.")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(backup_data)

    records_count = 0
    try:
        data_list = json.loads(backup_data)
        records_count = len(data_list)
    except Exception:
        pass

    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    SystemSetting.objects.update_or_create(
        key='auto_backup_last_run',
        defaults={'value': now_str, 'description': 'Timestamp of last auto data backup execution'}
    )

    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        ActivityLog.objects.create(
            user=user,
            activity_type='create',
            description=f"Triggered Auto Data Backup saved to Auto data_backup/{filename} ({records_count} records)"
        )

    return {
        'filename': filename,
        'path': file_path,
        'records_count': records_count,
        'size': len(backup_data),
        'timestamp': now_str,
    }

def get_auto_backup_files_list():
    """Returns list of auto backup JSON files in Auto data_backup folder."""
    import os
    from datetime import datetime

    os.makedirs(AUTO_BACKUP_DIR, exist_ok=True)

    files_list = []
    try:
        for fname in os.listdir(AUTO_BACKUP_DIR):
            if fname.endswith('.json'):
                fpath = os.path.join(AUTO_BACKUP_DIR, fname)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    size_mb = stat.st_size / (1024 * 1024)
                    size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{stat.st_size / 1024:.1f} KB"
                    mtime_dt = datetime.fromtimestamp(stat.st_mtime)
                    files_list.append({
                        'name': fname,
                        'size': size_str,
                        'bytes': stat.st_size,
                        'mtime': mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        'path': fpath,
                    })
    except Exception:
        pass

    files_list.sort(key=lambda x: x['mtime'], reverse=True)
    return files_list

_auto_backup_scheduler_started = False

def start_auto_backup_scheduler():
    """Background scheduler thread that executes auto backup every week night at 2 AM."""
    global _auto_backup_scheduler_started
    if _auto_backup_scheduler_started:
        return
    _auto_backup_scheduler_started = True

    import time
    from datetime import datetime
    from django.utils import timezone

    while True:
        try:
            time.sleep(60)
            config = get_auto_backup_config()
            if not config['enabled']:
                continue

            now = timezone.now()
            day_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
            target_day_idx = day_map.get(config['day'], 6)
            target_hour = int(config['time'].split(':')[0]) if ':' in config['time'] else 2

            if now.weekday() == target_day_idx and now.hour == target_hour and now.minute < 3:
                last_run_str = config['last_run']
                if last_run_str != 'Never':
                    try:
                        last_run_dt = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M:%S")
                        if (now.replace(tzinfo=None) - last_run_dt).total_seconds() < 80000:
                            continue
                    except Exception:
                        pass
                run_auto_backup(trigger_type='scheduled')
        except Exception as e:
            print(f"[AutoBackupScheduler Exception]: {e}")



