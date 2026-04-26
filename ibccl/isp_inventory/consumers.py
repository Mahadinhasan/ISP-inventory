import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.core.cache import cache

MATERIALS_MONITORING_GROUP = 'materials_monitoring'
USER_NOTIFICATION_GROUP_PREFIX = 'user_notifications_'

def _get_user_role(user):
    """Sync helper: get role from UserProfile or None."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.userprofile.role
    except Exception:
        return None


def _get_initial_monitoring_data(user=None):
    from django.db.models import Count, Sum, Q
    from .models import UserProfile, UsedMaterial

    branch_profiles = UserProfile.objects.filter(role='Branch').select_related('user')
    result = {
        'branch_users': [],
        'recent_used': [],
    }
    
    # Determine if we need to filter by NOC user
    is_noc = user and hasattr(user, 'userprofile') and user.userprofile.role == 'NOC'

    for profile in branch_profiles:
        u = profile.user
        used_filter = Q(technician=u)
        if is_noc:
            used_filter &= Q(material__created_by=user)
            
        used_count = UsedMaterial.objects.filter(used_filter).count()
        used_qty = UsedMaterial.objects.filter(used_filter).aggregate(s=Sum('quantity'))['s'] or 0
        
        # Only add to list if they have usage data for this NOC, or if user is Admin
        if not is_noc or used_count > 0:
            result['branch_users'].append({
                'id': u.id,
                'username': u.username,
                'full_name': u.get_full_name() or u.username,
                'is_online': profile.is_online,
                'used_materials_count': used_count,
                'used_quantity_total': used_qty,
            })
            
    # Recent used materials (last 20) for live feed
    recent = UsedMaterial.objects.select_related('technician', 'material')
    if is_noc:
        recent = recent.filter(material__created_by=user)
    
    recent = recent.order_by('-added_at')[:20]
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
def get_initial_data(user=None):
    return _get_initial_monitoring_data(user)


class MaterialsMonitoringConsumer(AsyncJsonWebsocketConsumer):
    """Real-time materials monitoring: Admin & NOC; shows branch users and used materials."""

    async def connect(self):
        self.user = self.scope.get('user')
        role = await get_user_role(self.user) if self.user else None
        if not self.user or not self.user.is_authenticated or role not in ['Admin', 'NOC']:
            await self.close(code=4403)
            return
            
        if role == 'Admin':
            self.monitoring_group = MATERIALS_MONITORING_GROUP
        else:
            self.monitoring_group = f"materials_monitoring_noc_{self.user.id}"
            
        await self.channel_layer.group_add(self.monitoring_group, self.channel_name)
        await self.accept()
        # Send initial snapshot
        data = await get_initial_data(self.user)
        await self.send_json({'type': 'initial', 'payload': data})

    async def disconnect(self, close_code):
        if hasattr(self, 'monitoring_group'):
            await self.channel_layer.group_discard(self.monitoring_group, self.channel_name)

    async def used_material_update(self, event):
        """Broadcast from channel layer: new or updated used material."""
        await self.send_json({
            'type': 'used_material_update',
            'payload': event.get('payload', {}),
        })

    async def user_status_change(self, event):
        """Broadcast from channel layer: user online/offline status change."""
        await self.send_json({
            'type': 'user_status_change',
            'payload': event.get('payload', {}),
        })

    async def receive_json(self, content):
        # Optional: handle ping/pong or refresh request
        if content.get('type') == 'refresh':
            data = await get_initial_data(self.user)
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


# Group name for all status updates
PRESENCE_GROUP = 'user_presence'
PRESENCE_CONNECTION_KEY_PREFIX = 'presence_connections_'


@database_sync_to_async
def set_user_online_status(user, is_online):
    """Sync helper to update user profile's online status."""
    if not user or not user.is_authenticated:
        return False
    try:
        from .models import UserProfile
        profile = UserProfile.objects.get(user=user)
        profile.is_online = is_online
        profile.save(update_fields=['is_online'])
        return True
    except Exception:
        return False


def _presence_connection_key(user_id):
    return f"{PRESENCE_CONNECTION_KEY_PREFIX}{user_id}"


@database_sync_to_async
def increment_presence_connections(user):
    """Track active websocket connections per user to avoid false offline state across tabs."""
    if not user or not user.is_authenticated:
        return 0

    key = _presence_connection_key(user.id)
    count = (cache.get(key) or 0) + 1
    cache.set(key, count, timeout=60 * 60 * 24)
    return count


@database_sync_to_async
def decrement_presence_connections(user):
    """Decrease active websocket connection count for the user."""
    if not user or not user.is_authenticated:
        return 0

    key = _presence_connection_key(user.id)
    current_count = cache.get(key) or 0
    next_count = max(current_count - 1, 0)

    if next_count == 0:
        cache.delete(key)
    else:
        cache.set(key, next_count, timeout=60 * 60 * 24)

    return next_count


@database_sync_to_async
def get_noc_user_ids():
    """Return all NOC user ids so their monitoring pages can receive live presence updates."""
    return list(
        User.objects.filter(userprofile__role='NOC').values_list('id', flat=True)
    )


class PresenceConsumer(AsyncJsonWebsocketConsumer):
    """Real-time presence: tracks online/offline status of users."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(PRESENCE_GROUP, self.channel_name)
        await self.accept()

        connection_count = await increment_presence_connections(self.user)
        if connection_count == 1:
            await set_user_online_status(self.user, True)
            await self.broadcast_presence_status('online')

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user.is_authenticated:
            remaining_connections = await decrement_presence_connections(self.user)
            if remaining_connections == 0:
                await set_user_online_status(self.user, False)
                await self.broadcast_presence_status('offline')
        
        if hasattr(self, 'channel_name'):
            await self.channel_layer.group_discard(PRESENCE_GROUP, self.channel_name)

    async def receive_json(self, content):
        """Handle manual status override from client."""
        msg_type = content.get('type')
        if msg_type == 'set_status':
            status = content.get('status')
            if status in ['online', 'offline']:
                is_online = (status == 'online')
                await set_user_online_status(self.user, is_online)
                await self.broadcast_presence_status(status)

    async def status_update(self, event):
        """Forward status updates from group to client."""
        await self.send_json(event)

    async def broadcast_presence_status(self, status):
        """Broadcast presence state to the shared presence group and monitoring dashboards."""
        presence_payload = {
            'user_id': self.user.id,
            'username': self.user.username,
            'status': status,
        }

        await self.channel_layer.group_send(
            PRESENCE_GROUP,
            {
                'type': 'status_update',
                'payload': presence_payload,
            }
        )

        monitoring_payload = {
            'user_id': self.user.id,
            'status': status,
        }

        await self.channel_layer.group_send(
            MATERIALS_MONITORING_GROUP,
            {
                'type': 'user_status_change',
                'payload': monitoring_payload,
            }
        )

        noc_user_ids = await get_noc_user_ids()
        for noc_user_id in noc_user_ids:
            await self.channel_layer.group_send(
                f"materials_monitoring_noc_{noc_user_id}",
                {
                    'type': 'user_status_change',
                    'payload': monitoring_payload,
                }
            )


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Real-time one-to-one chat."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        # Personal group for receiving messages
        self.user_group = f"user_chat_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive_json(self, content):
        """Handle incoming message from the user's browser."""
        msg_type = content.get('type')
        if msg_type == 'chat_message':
            receiver_id = content.get('receiver_id')
            message_text = content.get('message', '').strip()

            if not receiver_id or not message_text:
                return

            # Save to DB
            saved_msg = await self.save_message(receiver_id, message_text)
            if not saved_msg:
                return

            # Send to receiver's group
            receiver_group = f"user_chat_{receiver_id}"
            message_data = {
                'type': 'chat_message',
                'message': {
                    'id': saved_msg['id'],
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'content': message_text,
                    'created_at': saved_msg['created_at'],
                }
            }

            await self.channel_layer.group_send(receiver_group, message_data)
            
            # Send back to sender for confirmation/UI update
            await self.send_json(message_data)

    async def chat_message(self, event):
        """Receive message from group and send to WebSocket."""
        await self.send_json(event)

    @database_sync_to_async
    def save_message(self, receiver_id, content):
        from .models import InternalMessage
        try:
            receiver = User.objects.get(id=receiver_id)
            msg = InternalMessage.objects.create(
                sender=self.user,
                receiver=receiver,
                content=content
            )
            return {
                'id': msg.id,
                'created_at': msg.created_at.isoformat()
            }
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return None
