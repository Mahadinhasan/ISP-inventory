# Backend Notification Sending Guide

## Django Channels Implementation

### 1. Update Your Consumer (consumers.py)

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["user"].id
        self.user_group_name = f"notifications_user_{self.user_id}"

        # Add user to notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            # Handle incoming messages if needed
        except json.JSONDecodeError:
            pass

    # Handle notification messages
    async def notification(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'payload': event.get('payload', {})
        }))

    # Handle message notifications
    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event))
```

### 2. Update Your Routing (routing.py)

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
]
```

### 3. Create Notification Helper Functions

```python
# notifications.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

def send_notification(user_id, category, title, message, **kwargs):
    """
    Send a notification to a specific user.
    
    Args:
        user_id: Django user ID
        category: 'request', 'message', 'stock', or 'system'
        title: Notification title
        message: Notification message
        **kwargs: Additional fields like material, quantity, status
    """
    channel_layer = get_channel_layer()
    
    payload = {
        'id': f"notif_{user_id}_{int(time.time() * 1000)}",
        'category': category,
        'title': title,
        'message': message,
    }
    
    # Add optional fields
    if 'material' in kwargs:
        payload['material'] = kwargs['material']
    if 'quantity' in kwargs:
        payload['quantity'] = kwargs['quantity']
    if 'status' in kwargs:
        payload['status'] = kwargs['status']
    
    async_to_sync(channel_layer.group_send)(
        f"notifications_user_{user_id}",
        {
            "type": "send_notification",
            "payload": payload
        }
    )


def send_material_request_notification(user_id, material_name, quantity, status, request_id=None):
    """Send a material request notification."""
    message_map = {
        'Approved': f'Your request for {material_name} (Qty: {quantity}) has been Approved ✓',
        'Rejected': f'Your request for {material_name} (Qty: {quantity}) has been Rejected ✗',
        'Pending': f'Your request for {material_name} (Qty: {quantity}) is awaiting review',
    }
    
    message = message_map.get(status, 'Material request updated')
    
    send_notification(
        user_id,
        category='request',
        title='Material Request Update',
        message=message,
        material=material_name,
        quantity=quantity,
        status=status
    )


def send_message_notification(user_id, sender_name, preview_msg):
    """Send a new message notification."""
    send_notification(
        user_id,
        category='message',
        title=f'New message from {sender_name}',
        message=preview_msg
    )


def send_stock_alert_notification(user_id, material_name, current_qty, min_qty):
    """Send a stock alert notification."""
    send_notification(
        user_id,
        category='stock',
        title='Low Stock Alert',
        message=f'{material_name} stock is low ({current_qty} units, min: {min_qty})',
        material=material_name,
        quantity=current_qty
    )


def send_system_notification(user_id, title, message):
    """Send a system notification."""
    send_notification(
        user_id,
        category='system',
        title=title,
        message=message
    )


def broadcast_notification(category, title, message, **kwargs):
    """
    Send notification to all users in a group.
    
    Args:
        category: Notification category
        title: Notification title
        message: Notification message
        **kwargs: Additional fields
    """
    channel_layer = get_channel_layer()
    
    payload = {
        'category': category,
        'title': title,
        'message': message,
    }
    payload.update(kwargs)
    
    async_to_sync(channel_layer.group_send)(
        "notifications_broadcast",
        {
            "type": "send_notification",
            "payload": payload
        }
    )
```

---

## Integration Examples

### Example 1: Send Notification on Material Request Approval

```python
# views.py
from notifications import send_material_request_notification

def approve_material_request(request, request_id):
    material_request = MaterialRequest.objects.get(id=request_id)
    material_request.status = 'Approved'
    material_request.save()
    
    # Send notification to requester
    send_material_request_notification(
        user_id=material_request.requester.id,
        material_name=material_request.material.name,
        quantity=material_request.quantity,
        status='Approved'
    )
    
    return JsonResponse({'status': 'success'})
```

### Example 2: Send Notification on New Message

```python
# In your messaging app
from notifications import send_message_notification

def send_message(request, recipient_id):
    message_text = request.POST.get('message')
    
    # Save message
    message = Message.objects.create(
        sender=request.user,
        recipient_id=recipient_id,
        text=message_text
    )
    
    # Send notification
    send_message_notification(
        user_id=recipient_id,
        sender_name=request.user.username,
        preview_msg=message_text[:50] + ('...' if len(message_text) > 50 else '')
    )
    
    return JsonResponse({'status': 'success'})
```

### Example 3: Send Stock Alert Notification

```python
# In your signals or monitoring task
from notifications import send_stock_alert_notification

def check_low_stock():
    """Scheduled task to check and notify about low stock."""
    from django.core.management.base import BaseCommand
    
    low_stock_items = Material.objects.filter(
        quantity__lt=F('minimum_stock_level')
    )
    
    for material in low_stock_items:
        # Notify admin users
        admin_users = User.objects.filter(userprofile__role='Admin')
        for admin in admin_users:
            send_stock_alert_notification(
                user_id=admin.id,
                material_name=material.name,
                current_qty=material.quantity,
                min_qty=material.minimum_stock_level
            )
```

### Example 4: Send Notifications to Multiple Users

```python
# Send notification to all branch users
from django.contrib.auth.models import User

def notify_all_branches(title, message):
    from notifications import send_notification
    
    branch_users = User.objects.filter(userprofile__role='Branch')
    
    for user in branch_users:
        send_notification(
            user_id=user.id,
            category='system',
            title=title,
            message=message
        )
```

---

## Models Example

### Add to your models to track notification preferences (Optional)

```python
from django.db import models
from django.contrib.auth.models import User

class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preference')
    material_request_approved = models.BooleanField(default=True)
    material_request_rejected = models.BooleanField(default=True)
    new_message = models.BooleanField(default=True)
    stock_alert = models.BooleanField(default=True)
    system_notification = models.BooleanField(default=True)
    enable_sound = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Notification Preferences - {self.user.username}"
```

---

## Signals Example (Auto-Trigger Notifications)

```python
# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from isp_inventory.models import MaterialRequest
from notifications import send_material_request_notification

@receiver(post_save, sender=MaterialRequest)
def notify_on_request_status_change(sender, instance, created, update_fields, **kwargs):
    if not created and 'status' in update_fields:
        # Notify requester when status changes
        send_material_request_notification(
            user_id=instance.requester.id,
            material_name=instance.material.name,
            quantity=instance.quantity,
            status=instance.status
        )

# In apps.py
from django.apps import AppConfig

class IspInventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'isp_inventory'
    
    def ready(self):
        import isp_inventory.signals
```

---

## Testing Notifications

### Using Django Management Command

```python
# In management/commands/test_notification.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from notifications import send_material_request_notification

class Command(BaseCommand):
    help = 'Send test notifications'
    
    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int)
    
    def handle(self, *args, **options):
        user_id = options['user_id']
        
        send_material_request_notification(
            user_id=user_id,
            material_name='Test Fiber',
            quantity=100,
            status='Approved'
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Notification sent to user {user_id}'
            )
        )
```

Run with:
```bash
python manage.py test_notification 1
```

---

## Important Notes

1. **User Authorization**: Always verify user permissions before sending notifications
2. **Group Naming**: Follow the pattern `notifications_user_{user_id}`
3. **Error Handling**: Wrap notification sending in try-except blocks
4. **Async**: Use `async_to_sync()` for synchronous contexts
5. **Performance**: For bulk notifications, consider batching
6. **Testing**: Test with your Django Channels setup before production

---

## Common Issues & Fixes

### Issue: Notifications not appearing
**Solution**: 
1. Verify WebSocket is connected in browser console
2. Check that group name is correct
3. Ensure you're sending to authenticated users only

### Issue: Sound not playing
**Solution**:
1. Check browser autoplay settings
2. Ensure user has interacted with page before sound plays
3. Check Web Audio API console errors

### Issue: Notifications persisting after page refresh
**Solution**: This is expected. Use Django model to store notification history if needed.

### Issue: WebSocket closing frequently
**Solution**:
1. Increase the reconnection delay
2. Check server logs for issues
3. Ensure proper timeout settings in Django Channels

---

## Additional Resources

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
