import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User


# Group name all admin monitoring clients join (import in signals for broadcast)
MATERIALS_MONITORING_GROUP = 'materials_monitoring'

# Prefix for per-user notification groups (import in signals for broadcast)
USER_NOTIFICATION_GROUP_PREFIX = 'user_notifications_'


def _get_user_role(user):
    """Sync helper: get role from UserProfile or None."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.userprofile.role
    except Exception:
        return None


def _get_initial_monitoring_data():
    from django.db.models import Count, Sum
    from .models import UserProfile, UsedMaterial

    branch_profiles = UserProfile.objects.filter(role='Branch').select_related('user')
    result = {
        'branch_users': [],
        'recent_used': [],
    }
    for profile in branch_profiles:
        u = profile.user
        used_count = UsedMaterial.objects.filter(technician=u).count()
        used_qty = UsedMaterial.objects.filter(technician=u).aggregate(s=Sum('quantity'))['s'] or 0
        result['branch_users'].append({
            'id': u.id,
            'username': u.username,
            'full_name': u.get_full_name() or u.username,
            'used_materials_count': used_count,
            'used_quantity_total': used_qty,
        })
    # Recent used materials (last 20) for live feed
    recent = UsedMaterial.objects.select_related('technician', 'material').order_by('-added_at')[:20]
    for um in recent:
        result['recent_used'].append({
            'id': um.id,
            'technician_username': um.technician.username,
            'technician_name': um.technician.get_full_name() or um.technician.username,
            'material_name': um.material.name if um.material else '',
            'quantity': um.quantity,
            'status': um.status,
            'added_at': um.added_at.isoformat() if um.added_at else None,
        })
    return result


@database_sync_to_async
def get_user_role(user):
    return _get_user_role(user)


@database_sync_to_async
def get_initial_data():
    return _get_initial_monitoring_data()


class MaterialsMonitoringConsumer(AsyncJsonWebsocketConsumer):
    """Real-time materials monitoring: Admin only; shows branch users and used materials."""

    async def connect(self):
        self.user = self.scope.get('user')
        role = await get_user_role(self.user) if self.user else None
        if not self.user or not self.user.is_authenticated or role != 'Admin':
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(MATERIALS_MONITORING_GROUP, self.channel_name)
        await self.accept()
        # Send initial snapshot
        data = await get_initial_data()
        await self.send_json({'type': 'initial', 'payload': data})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(MATERIALS_MONITORING_GROUP, self.channel_name)

    async def used_material_update(self, event):
        """Broadcast from channel layer: new or updated used material."""
        await self.send_json({
            'type': 'used_material_update',
            'payload': event.get('payload', {}),
        })

    async def receive_json(self, content):
        # Optional: handle ping/pong or refresh request
        if content.get('type') == 'refresh':
            data = await get_initial_data()
            await self.send_json({'type': 'initial', 'payload': data})


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    """Per-user real-time notifications (MaterialRequest events, etc.)."""

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.group_name = f"{USER_NOTIFICATION_GROUP_PREFIX}{user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notification_event(self, event):
        """Receive notification event from channel layer and forward to client."""
        await self.send_json(
            {
                "type": "notification",
                "payload": event.get("payload", {}),
            }
        )
