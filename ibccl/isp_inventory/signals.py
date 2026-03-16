from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .utils import ensure_userprofile
from .models import UsedMaterial, Material, MaterialRequest, NotificationSetting, InternalMessage
from django.db.models import Sum
from .consumers import MATERIALS_MONITORING_GROUP, USER_NOTIFICATION_GROUP_PREFIX


def _broadcast_used_material(instance):
    """Notify admin & noc monitoring clients of used material create/update."""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        payload = {
            "id": instance.id,
            "technician_username": instance.technician.username if instance.technician else "",
            "technician_name": (instance.technician.get_full_name() or instance.technician.username)
            if instance.technician
            else "",
            "material_name": instance.material.name if instance.material else "",
            "quantity": instance.quantity,
            "status": instance.status,
            "added_at": instance.added_at.isoformat() if instance.added_at else None,
        }
        # Broadcast to admin group
        async_to_sync(channel_layer.group_send)(
            MATERIALS_MONITORING_GROUP,
            {"type": "used_material_update", "payload": payload},
        )
        
        # Broadcast to NOC group if material has a creator
        if instance.material and instance.material.created_by:
            noc_group = f"materials_monitoring_noc_{instance.material.created_by.id}"
            async_to_sync(channel_layer.group_send)(
                noc_group,
                {"type": "used_material_update", "payload": payload},
            )
    except Exception:
        pass


def _notify_user(user, payload):
    """Send a single notification event to one user's WebSocket group."""
    if not user or not user.id:
        return
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        group_name = f"{USER_NOTIFICATION_GROUP_PREFIX}{user.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "notification_event", "payload": payload},
        )
    except Exception:
        # Never break main flow due to notification issues
        pass


def _notify_users(users, payload):
    """Broadcast the same notification payload to multiple users."""
    for u in users:
        _notify_user(u, payload)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            ensure_userprofile(instance)
        except Exception:
            # Avoid raising during user creation if profile can't be created
            pass

@receiver(post_save, sender=Material)
def material_stock_notifications(sender, instance, **kwargs):
    """
    Notify Admin & Storekeeper when global material stock is low or out of stock.
    (Self notification for Admin/Store roles based on their responsibility)
    """
    if instance.status in ['Low Stock', 'Out of Stock']:
        from django.db.models import Q
        admin_store_users = User.objects.filter(
            userprofile__role__in=["Admin", "Storekeeper"]
        ).filter(
            Q(notificationsetting__isnull=True) | 
            Q(notificationsetting__low_stock_alert=True)
        ).distinct()

        if admin_store_users.exists():
            payload = {
                "category": "stock",
                "event": "low_stock",
                "title": "Stock Alert",
                "material": instance.name,
                "quantity": instance.quantity,
                "status": instance.status,
                "message": f"{instance.name} is currently {instance.status} (Qty: {instance.quantity}). Please restock.",
            }
            _notify_users(admin_store_users, payload)


@receiver(post_save, sender=UsedMaterial)
def subtract_used_material_from_inventory(sender, instance, created, **kwargs):
    """
    Automatically subtract used materials from the material's stock quantity.
    This is called when a UsedMaterial is created or updated.
    """
    # Real-time broadcast to admin materials monitoring (branch user usage)
    _broadcast_used_material(instance)
    if created:
        # When a new UsedMaterial is created, subtract its quantity from the material's stock
        material = instance.material
        if material:
            # Deduct the used quantity from available material stock
            material.quantity = max(0, material.quantity - instance.quantity)
            material.save(update_fields=['quantity'])
            
        # Self-notification for Branch users if their available personal stock is Low or Out of Stock
        total_in = MaterialRequest.objects.filter(requester=instance.technician, status='Approved').aggregate(s=Sum('quantity'))['s'] or 0
        total_out = UsedMaterial.objects.filter(technician=instance.technician).aggregate(s=Sum('quantity'))['s'] or 0
        branch_stock = total_in - total_out
        
        # Consider <= 2 as Low Stock for branch, and 0 as Out of Stock
        if branch_stock <= 2:
            status_text = "Out of Stock" if branch_stock <= 0 else "Low Stock"
            payload = {
                "category": "stock",
                "event": "branch_stock",
                "title": f"Self Stock Alert: {status_text}",
                "message": f"Your personal remaining stock is {status_text} (Remaining total: {branch_stock}). Please request more materials if needed.",
            }
            _notify_user(instance.technician, payload)


@receiver(post_delete, sender=UsedMaterial)
def restore_used_material_to_inventory(sender, instance, **kwargs):
    """
    Automatically restore used materials back to inventory when a UsedMaterial record is deleted.
    This ensures we don't lose track of material quantities if a record is removed.
    """
    material = instance.material
    if material:
        # Restore the deleted used material quantity back to inventory
        material.quantity += instance.quantity
        material.save(update_fields=['quantity'])


@receiver(post_save, sender=MaterialRequest)
def material_request_notifications(sender, instance, created, **kwargs):
    """
    Real-time notifications for MaterialRequest events:
    - When Branch sends a new request (Pending) -> notify Admin & Storekeeper users (if enabled).
    - When a request is Approved/Rejected -> notify the requester (if enabled).
    """
    try:
        # New request created (typically Pending) -> notify admin/storekeeper
        if created:
            # Only notify if material request alerts are enabled
            from django.db.models import Q
            admin_store_users = User.objects.filter(
                userprofile__role__in=["Admin", "Storekeeper"]
            ).filter(
                Q(notificationsetting__isnull=True) | 
                Q(notificationsetting__new_request_alert=True)
            ).distinct()

            if admin_store_users.exists():
                payload = {
                    "category": "request",
                    "event": "created",
                    "request_id": instance.id,
                    "material": instance.material.name if instance.material else "",
                    "quantity": instance.quantity,
                    "status": instance.status,
                    "request_type": instance.request_type,
                    "requester_username": instance.requester.username if instance.requester else "",
                    "message": f"New material request from {instance.requester.username if instance.requester else 'Unknown'}",
                }
                _notify_users(admin_store_users, payload)

        # Status-based notifications to requester
        if instance.status in ("Approved", "Rejected") and instance.requester:
            try:
                notif_setting = NotificationSetting.objects.get(user=instance.requester)
                if not notif_setting.new_request_alert:
                    return
            except NotificationSetting.DoesNotExist:
                # Default: if no explicit settings, treat as enabled
                pass

            payload = {
                "category": "request",
                "event": instance.status.lower(),
                "request_id": instance.id,
                "material": instance.material.name if instance.material else "",
                "quantity": instance.quantity,
                "status": instance.status,
                "request_type": instance.request_type,
                "message": f"Your material request for {instance.material.name if instance.material else 'material'} was {instance.status}.",
            }
            _notify_user(instance.requester, payload)
    except Exception:
        # Do not break save flow due to notification errors
        pass

@receiver(post_save, sender=InternalMessage)
def internal_message_notification(sender, instance, created, **kwargs):
    """
    Real-time notifications for the upcoming Internal Communication feature.
    When a message is sent, the receiver gets a live system notification.
    """
    if created and instance.receiver:
        payload = {
            "category": "message",
            "event": "new_message",
            "title": "New Internal Message",
            "sender": instance.sender.username,
            "message": f"Message from {instance.sender.username}: {instance.content[:60]}...",
        }
        _notify_user(instance.receiver, payload)
