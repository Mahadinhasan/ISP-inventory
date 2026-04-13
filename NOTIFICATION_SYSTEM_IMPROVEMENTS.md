# Enhanced Notification System - Complete Documentation

## Overview
The notification system has been completely enhanced with advanced features including max 5 notifications display, real-time WebSocket support, notification sound, and notification type-specific handlers.

---

## Key Features Implemented

### 1. **Maximum 5 Notifications Display**
- The dropdown shows a maximum of 5 most recent notifications
- When more than 5 notifications arrive, the oldest ones are removed from view (but total count is tracked)
- A footer message displays: "Showing max 5 most recent notifications"

### 2. **Smart Badge Counter**
- **Badge Display**: Shows actual count when ≤ 5, displays "5+" when count exceeds 5
- **Total Count**: Shows actual total in header: `Notifications (X)`
- **Real-time Update**: Updates instantly when notifications arrive
- **Click to Clear**: Opening the dropdown marks badges as seen

### 3. **Notification Sound**
- **Web Audio API**: Uses modern Web Audio API for notification beep (800Hz → 600Hz frequency sweep)
- **Fallback**: Falls back to HTML5 audio element if Web Audio API unavailable
- **Universal**: Single sound plays for all notification types
- **Browser Safe**: Handles browser autoplay restrictions gracefully

### 4. **Notification Type Handlers**
Four main notification types with specific actions:

#### a. **Material Request** (`request`)
- Icon: `<i class="fas fa-clipboard-list text-blue-500"></i>`
- Click Action: Navigates to `/requests/`
- Status: Shows Approved/Rejected/Pending status with color coding
- Meta Data: Shows material name and quantity

#### b. **Message** (`message`)
- Icon: `<i class="fas fa-envelope text-green-500"></i>`
- Click Action: Navigates to `/chat/`
- Use Case: New messages from other users

#### c. **Stock Alert** (`stock`)
- Icon: `<i class="fas fa-exclamation-triangle text-red-500"></i>`
- Click Action: Navigates to `/materials/`
- Use Case: Low stock warnings, depletion alerts

#### d. **System** (`system`)
- Icon: `<i class="fas fa-info-circle text-purple-500"></i>`
- Click Action: Dismiss only
- Use Case: General system announcements

### 5. **Real-Time WebSocket Integration**
- **Connection URL**: `/ws/notifications/`
- **Auto-Reconnect**: Reconnects after 3 seconds if connection lost
- **Message Format**: Expects JSON with `type: 'notification'` and `payload` object
- **Console Logging**: Debug information for connection status

### 6. **Click-to-Action Functionality**
- Each notification is clickable
- Clicking executes the appropriate handler action
- Notification item is removed after clicking
- Counter updates automatically

---

## Notification Payload Structure

### Expected WebSocket Message Format
```json
{
  "type": "notification",
  "payload": {
    "id": "unique-notification-id",
    "category": "request",  // or "message", "stock", "system"
    "title": "Material Request Update",
    "message": "Your request was approved",
    "material": "Fiber",
    "quantity": 50,
    "status": "Approved"  // or "Rejected", "Pending"
  }
}
```

### Payload Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | String | No | Unique notification ID (auto-generated if missing) |
| `category` | String | Yes | One of: `request`, `message`, `stock`, `system` |
| `title` | String | No | Notification title (defaults based on category) |
| `message` | String | No | Notification message body |
| `material` | String | No | Material name (for request/stock) |
| `quantity` | Number | No | Quantity value (for request/stock) |
| `status` | String | No | Status for requests: `Approved`, `Rejected`, `Pending` |

---

## JavaScript Functions Reference

### Core Functions

#### `toggleNotificationMenu()`
Opens/closes the notification dropdown menu.
```javascript
toggleNotificationMenu()  // Toggles dropdown visibility
```

#### `clearNotifications()`
Clears all notifications and resets counters.
```javascript
clearNotifications()  // Removes all notifications
```

#### `updateNotificationCount()`
Updates badge and total count display.
```javascript
updateNotificationCount()  // Auto-called after changes
```

#### `handleNotificationClick(item, handler)`
Executes notification action and removes item.
```javascript
handleNotificationClick(item, handler)
```

#### `playNotificationSound()`
Plays notification sound using Web Audio API.
```javascript
playNotificationSound()  // Auto-called on new notification
```

### Global Variables

| Variable | Type | Description |
|----------|------|-------------|
| `window.unseenCount` | Number | Count of notifications not yet viewed |
| `window.totalNotifications` | Number | Total notifications received in session |
| `window.MAX_NOTIFICATIONS_DISPLAY` | Number | Set to 5 (maximum display count) |
| `window.notificationQueue` | Array | Queue of pending notifications |

---

## HTML Elements

### Key DOM Elements
| ID | Purpose |
|----|---------|
| `notification-bell` | Bell icon button |
| `notification-count` | Badge showing count |
| `notification-dropdown` | Main dropdown container |
| `notification-list` | Container for notification items |
| `notification-total-count` | Total count display |
| `notification-sound` | Audio element for sound |
| `empty-notifications` | Empty state display |

---

## Styling & Visual Behavior

### Notification Item Features
- **Hover Effect**: Background color changes, icon scales up slightly
- **Animation**: Fade-in animation on arrival
- **Status Colors**:
  - Approved: Green (`text-green-600`)
  - Rejected: Red (`text-red-500`)
  - Pending: Blue (`text-blue-500`)
- **Meta Indicators**: Small colored dot on the right side
- **Icon Background**: Takes on category colors with proper contrast

### Badge Behavior
- **Scale-in**: Appears with scale animation
- **Scale-out**: Disappears when menu opened
- **Color**: Always red (`bg-red-500`)
- **Content**: "5+" when count exceeds 5

---

## Testing & Examples

### Test Notification via Console
```javascript
// Send a test material request notification
const testData = {
  type: 'notification',
  payload: {
    category: 'request',
    title: 'Material Request Update',
    message: 'Your request for Fiber was approved',
    material: 'Fiber',
    quantity: 50,
    status: 'Approved'
  }
};

// Simulate WebSocket message
const event = new MessageEvent('message', {
  data: JSON.stringify(testData)
});
```

### Send Test Notifications from Backend (Django)
```python
# Using Django Channels
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

channel_layer = get_channel_layer()

# Send to user's notification group
async_to_sync(channel_layer.group_send)(
    f"notifications_user_{user_id}",
    {
        "type": "notification",
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

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Web Audio API | ✅ | ✅ | ✅ | ✅ |
| WebSocket | ✅ | ✅ | ✅ | ✅ |
| HTML5 Audio | ✅ | ✅ | ✅ | ✅ |
| CSS Animations | ✅ | ✅ | ✅ | ✅ |

---

## Backend Integration Points

### Expected WebSocket Consumer
Create/Update your consumers to send notifications in this format:

```python
# In your consumers.py
async def send_notification(self, event):
    await self.send(json.dumps(event))
```

### Notification Group Naming Convention
- User group: `notifications_user_{user_id}`
- Broadcast group: `notifications_broadcast`

---

## Performance Considerations

1. **Memory**: Max 5 items in DOM at any time
2. **Sound**: Lightweight Web Audio API (no file downloads)
3. **WebSocket**: Lightweight message format
4. **Auto-Cleanup**: Old notifications are removed when max reached
5. **Lazy Reconnection**: 3-second delay before reconnect attempt

---

## Future Enhancements

- [ ] Notification history/archive view
- [ ] Notification sorting options (by type, date)
- [ ] Notification dismissal delay animations
- [ ] Custom sound per notification type
- [ ] Desktop notifications API integration
- [ ] Notification preferences per type
- [ ] Export notification history

---

## Troubleshooting

### Notifications Not Appearing
1. Check WebSocket connection in browser console
2. Verify backend is sending to correct group
3. Check payload format matches expected structure

### Sound Not Playing
1. Check browser autoplay settings
2. Verify Web Audio API is not blocked
3. Try fallback HTML5 audio element
4. Check browser console for errors

### Badge Count Wrong
1. Clear browser cache
2. Open notification menu to reset count
3. Check `window.unseenCount` in console

### Dropdown Not Opening
1. Clear browser cache
2. Check for JavaScript errors in console
3. Verify `notification-bell` element exists

---

## Summary

The enhanced notification system provides:
✅ Real-time notifications via WebSocket
✅ Maximum 5 displayed with smart "5+" badge
✅ Four notification types with specific actions
✅ Single universal notification sound
✅ Click-to-action functionality
✅ Automatic counter management
✅ Dark mode support
✅ Responsive design
✅ Graceful fallbacks
✅ Auto-reconnection logic
