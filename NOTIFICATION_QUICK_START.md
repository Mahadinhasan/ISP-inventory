# Notification System - Quick Reference

## What Changed?

### 1. **Max 5 Notifications Badge**
- Shows count when ≤ 5
- Shows "5+" when count > 5
- Can only display 5 items max in dropdown
- Total count shown in header: `Notifications (X)`

### 2. **Notification Sound**
- **Sound Type**: Web Audio API (800Hz → 600Hz frequency sweep)
- **Duration**: 150ms beep
- **Fallback**: HTML5 audio if Web Audio fails
- **Trigger**: Plays automatically on new notification

### 3. **Click-to-Action System**
Every notification type has a specific action when clicked:

#### Material Request → `/requests/`
```
Icon: 📋 (Blue)
Status Colors: Approved (Green), Rejected (Red), Pending (Blue)
```

#### Message → `/chat/`
```
Icon: ✉️ (Green)
```

#### Stock Alert → `/materials/`
```
Icon: ⚠️ (Red)
```

#### System → Dismiss
```
Icon: ℹ️ (Purple)
```

### 4. **Real-Time Notifications**
- Uses WebSocket: `/ws/notifications/`
- Auto-reconnects every 3 seconds if disconnected
- Console logs for debugging

---

## Quick Test

### Test in Browser Console
```javascript
// Test notification UI
const testNotif = {
  id: 'test_1',
  category: 'request',
  title: 'Test Request',
  message: 'This is a test notification',
  material: 'Test Fiber',
  quantity: 50,
  status: 'Approved'
};

// Simulate by calling the function directly (for testing)
// This would normally come from WebSocket
```

### Check WebSocket Connection
```javascript
// In console
console.log('Unseen:', window.unseenCount)
console.log('Total:', window.totalNotifications)
console.log('Max Display:', window.MAX_NOTIFICATIONS_DISPLAY)
```

---

## Backend Implementation

### Send a Notification (Django)

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_notification(user_id):
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f"notifications_user_{user_id}",
        {
            "type": "send_notification",
            "payload": {
                "category": "request",
                "title": "Material Request Update",
                "message": "Your request was approved",
                "material": "Fiber",
                "quantity": 50,
                "status": "Approved"
            }
        }
    )
```

---

## Notification Payload Examples

### Material Request
```json
{
  "category": "request",
  "title": "Material Request Update",
  "message": "Your request for Fiber was approved",
  "material": "Fiber",
  "quantity": 50,
  "status": "Approved"
}
```

### New Message
```json
{
  "category": "message",
  "title": "New message from Admin",
  "message": "Hello, when can you send the materials?"
}
```

### Stock Alert
```json
{
  "category": "stock",
  "title": "Low Stock Alert",
  "message": "Fiber stock is below minimum",
  "material": "Fiber",
  "quantity": 5
}
```

### System
```json
{
  "category": "system",
  "title": "System Maintenance",
  "message": "System will be down for maintenance tomorrow"
}
```

---

## Key Files Modified

- **base.html**: Enhanced notification UI and scripts
- **NOTIFICATION_SYSTEM_IMPROVEMENTS.md**: Full documentation
- **BACKEND_NOTIFICATION_GUIDE.md**: Backend integration guide

---

## Global JavaScript Variables

| Variable | Type | Value |
|----------|------|-------|
| `window.unseenCount` | Number | Count of unseen notifications |
| `window.totalNotifications` | Number | Total notifications in session |
| `window.MAX_NOTIFICATIONS_DISPLAY` | Number | 5 (maximum) |
| `window.MAX_NOTIFICATIONS_DISPLAY` | Number | 5 (maximum) |

---

## Key CSS Classes

| Class | Purpose |
|-------|---------|
| `.notification-item` | Single notification container |
| `.fade-in` | Fade-in animation |
| `.dropdown-menu` | Dropdown animation |

---

## Important Features

✅ **Max 5 Display**: Oldest items removed when limit reached
✅ **Smart Badge**: Shows count ≤5, "5+" when >5
✅ **Real-time**: WebSocket connection with auto-reconnect
✅ **Sound**: Web Audio API with fallback
✅ **Type Handlers**: 4 notification types with specific actions
✅ **Dark Mode**: Full dark mode support
✅ **Responsive**: Works on mobile and desktop
✅ **Accessibility**: Proper icons and labels

---

## Troubleshooting

### No notifications showing?
- Check WebSocket connection: `window.notificationQueue`
- Verify backend sending to correct user group
- Look for errors in browser console

### Sound not playing?
- Check browser autoplay policy
- Verify Web Audio API isn't blocked
- Check console for audio errors

### Counter wrong?
- Clear notifications: Click "Mark all as read"
- Refresh page to reset state

---

## Next Steps

1. ✅ Update your Django consumers.py with NotificationConsumer
2. ✅ Create notifications.py with helper functions
3. ✅ Add signal handlers to auto-send notifications
4. ✅ Test with management command or console
5. ✅ Deploy and monitor WebSocket connections

---

For detailed information, see:
- [NOTIFICATION_SYSTEM_IMPROVEMENTS.md](NOTIFICATION_SYSTEM_IMPROVEMENTS.md)
- [BACKEND_NOTIFICATION_GUIDE.md](BACKEND_NOTIFICATION_GUIDE.md)
