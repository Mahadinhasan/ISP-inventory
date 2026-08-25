from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .utils import ensure_userprofile
from .models import UsedMaterial, Material, MaterialRequest, NotificationSetting, InternalMessage, ActivityLog, LogSettings
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
            "technician_id": instance.technician.id if instance.technician else None,
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
            Q(notification_setting__isnull=True) | 
            Q(notification_setting__low_stock_alert=True)
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
        # Instead of generic subtraction here, we handle it explicitly in views.py based on Accepted/Rejected status.
        # This prevents double deduction and honors the Remaining_stock logic.

        # Self-notification for Branch users if their available personal stock is Low or Out of Stock.
        # Fix: Only count 'Received' MaterialRequests and 'Accepted' UsedMaterials to correctly reflect stock.
        total_in = MaterialRequest.objects.filter(
            requester=instance.technician,
            status='Received'
        ).aggregate(s=Sum('quantity'))['s'] or 0
        total_out = UsedMaterial.objects.filter(
            technician=instance.technician,
            status='Accepted'
        ).aggregate(s=Sum('quantity'))['s'] or 0
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

        # Notify the NOC user who created the material when a branch user reports using it.
        # Check NotificationSetting before sending so NOC can opt-out if desired.
        if instance.material and instance.material.created_by:
            noc_user = instance.material.created_by
            try:
                if hasattr(noc_user, 'userprofile') and noc_user.userprofile.role == 'NOC':
                    # Check NOC notification preference (new_request_alert covers used-material alerts)
                    should_notify = True
                    try:
                        from isp_inventory.models import NotificationSetting
                        noc_setting = NotificationSetting.objects.get(user=noc_user)
                        should_notify = noc_setting.new_request_alert
                    except NotificationSetting.DoesNotExist:
                        pass  # Default: enabled

                    if should_notify:
                        technician_name = (instance.technician.get_full_name() or instance.technician.username) if instance.technician else 'Unknown'
                        material_name = instance.material.name if instance.material else 'Unknown'
                        noc_payload = {
                            "category": "request",
                            "event": "used_material",
                            "title": "New Used Material Report",
                            "message": f"{technician_name} reported using {instance.quantity}x {material_name}.",
                        }
                        _notify_user(noc_user, noc_payload)
            except Exception:
                pass

    # On status change (Accepted/Rejected):
    # - Notify the branch user (technician) of the NOC decision
    # - Also notify the NOC user themselves as a confirmation of their action
    if not created and instance.status in ('Accepted', 'Rejected') and instance.material and instance.material.created_by:
        try:
            noc_user = instance.material.created_by
            if hasattr(noc_user, 'userprofile') and noc_user.userprofile.role == 'NOC':
                technician_name = (instance.technician.get_full_name() or instance.technician.username) if instance.technician else 'Unknown'
                material_name = instance.material.name if instance.material else 'Unknown'

                # 1. Notify the branch user (technician) of the decision
                if instance.technician:
                    branch_payload = {
                        "category": "request",
                        "event": instance.status.lower(),
                        "title": f"Material Report {instance.status}",
                        "message": f"Your used material report for {material_name} was {instance.status} by NOC.",
                    }
                    _notify_user(instance.technician, branch_payload)

                # 2. Confirm to NOC user that their action was saved
                # (This ensures NOC receives their own WebSocket notification for real-time UI feedback)
                noc_confirm_payload = {
                    "category": "stock",
                    "event": f"used_material_{instance.status.lower()}",
                    "title": f"Usage {instance.status}",
                    "message": f"You {instance.status.lower()} {technician_name}'s usage of {instance.quantity}x {material_name}.",
                }
                _notify_user(noc_user, noc_confirm_payload)
        except Exception:
            pass




@receiver(post_delete, sender=UsedMaterial)
def restore_used_material_to_inventory(sender, instance, **kwargs):
    """
    NOTE: No stock restoration is needed here.

    Branch stock is NOT stored as a field in the database.
    It is calculated dynamically every time as:
        available = MaterialRequest(Received).quantity
                  - UsedMaterial(Accepted).quantity
                  - DamageMaterial(Pending/Confirmed).quantity
                  - RefundableMaterial.quantity

    When a UsedMaterial record is deleted, it simply disappears from the
    UsedMaterial table, and the next dynamic calculation will automatically
    reflect the correct (higher) available stock — no manual restoration needed.

    If stock was NOT returning correctly after delete, the root cause was Bug #1:
    `my_stock_count` was counting Pending/Rejected UsedMaterial records in `total_out`
    (missing status='Accepted' filter). That bug has been fixed in views.py.
    """
    pass  # Dynamic calculation handles this automatically.



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
                Q(notification_setting__isnull=True) | 
                Q(notification_setting__new_request_alert=True)
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

            # If this material was created by a NOC user, notify them too
            if instance.material and instance.material.created_by:
                noc_user = instance.material.created_by
                try:
                    if hasattr(noc_user, 'userprofile') and noc_user.userprofile.role == 'NOC':
                        should_notify = True
                        try:
                            from isp_inventory.models import NotificationSetting
                            noc_setting = NotificationSetting.objects.get(user=noc_user)
                            should_notify = noc_setting.new_request_alert
                        except NotificationSetting.DoesNotExist:
                            pass
                        if should_notify:
                            requester_name = instance.requester.get_full_name() or instance.requester.username if instance.requester else 'Unknown'
                            noc_req_payload = {
                                "category": "request",
                                "event": "created",
                                "request_id": instance.id,
                                "material": instance.material.name if instance.material else "",
                                "quantity": instance.quantity,
                                "status": instance.status,
                                "request_type": instance.request_type,
                                "message": f"New request for {instance.material.name} from {requester_name}.",
                            }
                            _notify_user(noc_user, noc_req_payload)
                except Exception:
                    pass

        # Status-based notifications to requester
        if instance.status in ("Approved", "Rejected") and instance.requester:
            try:
                from isp_inventory.models import NotificationSetting
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


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Track user login activity"""
    try:
        log_settings = LogSettings.objects.first()
        if log_settings and log_settings.log_user_activities and log_settings.enable_database_logging:
            ip_address = get_client_ip(request) if request else None
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            # Update user profile last_active
            profile = ensure_userprofile(user)
            from django.utils import timezone
            profile.last_active = timezone.now()
            profile.last_login = timezone.now()
            profile.is_online = True
            profile.save(update_fields=['last_active', 'last_login', 'is_online'])
            
            # Create activity log
            ActivityLog.objects.create(
                user=user,
                activity_type='login',
                description=f'User {user.username} logged in',
                ip_address=ip_address,
                user_agent=user_agent[:500],
            )
    except Exception:
        pass


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Track user logout activity"""
    try:
        log_settings = LogSettings.objects.first()
        if log_settings and log_settings.log_user_activities and log_settings.enable_database_logging:
            ip_address = get_client_ip(request) if request else None
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            # Update user profile
            if user:
                profile = ensure_userprofile(user)
                from django.utils import timezone
                profile.is_online = False
                profile.save(update_fields=['is_online'])
            
            # Create activity log
            if user:
                ActivityLog.objects.create(
                    user=user,
                    activity_type='logout',
                    description=f'User {user.username} logged out',
                    ip_address=ip_address,
                    user_agent=user_agent[:500],
                )
    except Exception:
        pass


def get_client_ip(request):
    """Get client IP address from request"""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(post_save, sender=User)
def create_notification_setting(sender, instance, created, **kwargs):
    """Create NotificationSetting for new users"""
    if created:
        NotificationSetting.objects.get_or_create(user=instance)


# ── Automatically Log User Create, Edit & Delete Actions ──────────────────────
from .middleware import get_current_user, get_current_request
from .models import DamageMaterial, RefundableMaterial, MacSerialNumber

LOGGED_MODELS = [Material, MaterialRequest, UsedMaterial, RefundableMaterial, DamageMaterial, MacSerialNumber]

def log_db_action(instance, sender, action_type, description):
    try:
        user = get_current_user()
        if not user or not user.is_authenticated:
            # Fallback checks to find an associated user
            if hasattr(instance, 'created_by') and instance.created_by:
                user = instance.created_by
            elif hasattr(instance, 'requester') and instance.requester:
                user = instance.requester
            elif hasattr(instance, 'technician') and instance.technician:
                user = instance.technician
            elif hasattr(instance, 'user') and instance.user:
                user = instance.user
            else:
                return

        request = get_current_request()
        ip_address = get_client_ip(request) if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        # Check database logging settings
        log_settings = LogSettings.objects.first()
        if log_settings and log_settings.log_user_activities and log_settings.enable_database_logging:
            ActivityLog.objects.create(
                user=user,
                activity_type=action_type,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent[:500]
            )
    except Exception:
        pass

@receiver(post_save, sender=Material)
@receiver(post_save, sender=MaterialRequest)
@receiver(post_save, sender=UsedMaterial)
@receiver(post_save, sender=RefundableMaterial)
@receiver(post_save, sender=DamageMaterial)
@receiver(post_save, sender=MacSerialNumber)
def log_create_or_update(sender, instance, created, **kwargs):
    model_name = sender.__name__
    action = 'create' if created else 'edit'
    desc = f"{model_name} '{instance}' was {'created' if created else 'updated'}"
    log_db_action(instance, sender, action, desc)

@receiver(post_delete, sender=Material)
@receiver(post_delete, sender=MaterialRequest)
@receiver(post_delete, sender=UsedMaterial)
@receiver(post_delete, sender=RefundableMaterial)
@receiver(post_delete, sender=DamageMaterial)
@receiver(post_delete, sender=MacSerialNumber)
def log_delete(sender, instance, **kwargs):
    model_name = sender.__name__
    desc = f"{model_name} '{instance}' was deleted"
    log_db_action(instance, sender, 'delete', desc)

