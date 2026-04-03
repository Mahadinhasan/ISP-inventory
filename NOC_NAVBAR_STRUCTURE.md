# NOC Role Navbar - Complete Structure

## ✅ Navbar Navigation Items

### **Desktop Navbar** (Fully Responsive Design)
```
ISP Inventory Logo  [Dashboard] [Materials] [Requests] [Reports] [Messages] [Notifications]  [Profile ▼]
```

### **Mobile Navbar** (Hamburger Menu)
```
ISP Inventory Logo  ☰
    ↓ Dropdown Menu:
    - Dashboard
    - Materials
    - Requests
    - Reports
    - Messages
    - Notifications
    - Profile
```

---

## 🔗 Menu Items & URL Mappings

### **1. Dashboard**
- **URL**: `/noc/dashboard/`
- **Template Reference**: `{% url 'noc:dashboard' %}`
- **Icon**: 📊 Tachometer
- **View**: `views.noc_dashboard`

### **2. Materials**
- **URL**: `/noc/materials/`
- **Template Reference**: `{% url 'noc:materials' %}`
- **Icon**: 📦 Boxes
- **View**: `views.noc_materials`
- **Actions**: Add, Edit, Delete materials

### **3. Requests**
- **URL**: `/noc/requests/`
- **Template Reference**: `{% url 'noc:requests' %}`
- **Icon**: ✈️ Paper Plane
- **View**: `views.noc_requests`
- **Actions**: Approve/Reject requests

### **4. Reports**
- **URL**: `/noc/reports/`
- **Template Reference**: `{% url 'noc:reports' %}`
- **Icon**: 📈 Chart Line
- **View**: `views.noc_reports`
- **Features**: Date filtering, Analytics, Export

### **5. Messages**
- **URL**: `/chat/`
- **Template Reference**: `{% url 'chat' %}`
- **Icon**: ✉️ Envelope
- **View**: `isp_inventory.views.chat_view`
- **Note**: Links to shared chat system

### **6. Notifications**
- **URL**: `/noc/notifications/`
- **Template Reference**: `{% url 'noc:notifications' %}`
- **Icon**: 🔔 Bell
- **View**: `views.noc_notifications`

### **7. Profile Dropdown** ▼
- **Icon**: 👤 User Avatar (with status indicator)
- **Sub-items**:
  - 👤 **My Profile** → `/noc/profile/`
  - 🎨 **Appearance** (Light/Dark/Auto mode)
  - 🟢 **Set Status** (Online/Offline)
  - 🚪 **Logout** → `/logout/`

---

## 📱 Responsive Design

### **Desktop (md breakpoint and above)**
- ✅ Full horizontal menu with icons
- ✅ Hover effects on menu items
- ✅ Active link highlighting (border-bottom)
- ✅ Profile dropdown on the right

### **Mobile (Below md breakpoint)**
- ✅ Hamburger menu button
- ✅ Full vertical menu list
- ✅ Touch-friendly spacing
- ✅ Icons with labels on each item

---

## 🎨 Styling Features

### **Desktop Menu Items**
```html
<a href="..." 
    class="nav-link border-transparent text-gray-500 
    hover:border-gray-300 hover:text-gray-700 
    inline-flex items-center px-3 py-2 border-b-2 
    text-sm font-medium transition">
    <i class="fas fa-[icon] mr-2"></i>Label
</a>
```

Features:
- Smooth transitions
- Hover border effect (bottom border appears)
- Icon + text on each item
- Consistent spacing

### **Mobile Menu Items**
```html
<a href="..." 
    class="block pl-3 pr-4 py-2 border-l-4 border-transparent 
    text-base font-medium text-gray-600 
    hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800 transition">
    <i class="fas fa-[icon] mr-2"></i>Label
</a>
```

Features:
- Left border highlight on hover
- Full width for mobile
- Larger text for accessibility
- Smooth background color transition

---

## 🔐 Security & Access Control

### **Decorator Protection**
```python
@login_required
@noc_role_required
def noc_dashboard(request):
    # Only NOC role users can access
```

### **Role Check**
All NOC routes are protected by:
1. `@login_required` - Must be logged in
2. `@noc_role_required` - Must have NOC role in UserProfile
3. Automatic redirect to dashboard if role check fails

---

## 📋 URL Configuration (urls.py)

```python
app_name = 'noc'

urlpatterns = [
    path('dashboard/', views.noc_dashboard, name='dashboard'),
    path('materials/', views.noc_materials, name='materials'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/edit/<int:pk>/', views.edit_material, name='edit_material'),
    path('materials/delete/<int:pk>/', views.delete_material, name='delete_material'),
    path('requests/', views.noc_requests, name='requests'),
    path('requests/approve/<int:pk>/', views.approve_request, name='approve_request'),
    path('requests/reject/<int:pk>/', views.reject_request, name='reject_request'),
    path('reports/', views.noc_reports, name='reports'),
    path('notifications/', views.noc_notifications, name='notifications'),
    path('profile/', views.noc_profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]
```

---

## ✨ Features

### **Active Navigation**
- Current page indicator (highlighted border)
- Smooth hover transitions
- Icon guidance for each section

### **User Information Display**
- Username in dropdown
- Email address
- Role badge (NOC)
- Online/Offline status indicator

### **Theme Support**
- Light mode
- Dark mode
- Auto mode (system preference)

### **Responsive Breakpoints**
- Mobile: < md (768px)
- Tablet/Desktop: ≥ md (768px)

---

## 🚀 Usage Example

### **Template Implementation**
```html
{% extends 'noc/base.html' %}

{% block content %}
    <!-- Content here uses the navbar automatically -->
{% endblock %}
```

### **Navigation in Links**
```html
<!-- Internal navigation -->
<a href="{% url 'noc:materials' %}">View Materials</a>

<!-- External app navigation -->
<a href="{% url 'chat' %}">Chat</a>

<!-- Logout -->
<a href="{% url 'noc:logout' %}">Logout</a>
```

---

## 🔍 Testing Checklist

- [ ] Desktop menu displays all 6 items
- [ ] Mobile menu shows hamburger button
- [ ] All links redirect to correct pages
- [ ] Active page shows border highlight
- [ ] Profile dropdown opens/closes correctly
- [ ] Dark mode toggle works
- [ ] Status indicator updates
- [ ] Messages link works
- [ ] Logout redirects to login page
- [ ] NOC pages are protected (non-NOC users can't access)

---

## 📞 Navigation Flow

```
User Logs In (NOC role)
    ↓
Redirects to /noc/dashboard/
    ↓
Navbar displayed with 6 main menu items:
    Dashboard    [← Currently viewing]
    Materials    [View/Manage]
    Requests     [Approve/Reject]
    Reports      [Analytics]
    Messages     [Chat]
    Notifications [Alerts]
    ↓
Profile Dropdown (top right)
    My Profile
    Appearance (Theme)
    Set Status
    Logout
```

---

## 📁 Files Modified

- ✅ `Noc/urls.py` - Fixed URL paths (removed duplicate /noc/)
- ✅ `templates/noc/base.html` - Enhanced navbar with all 6 menu items

---

**Status**: ✅ Complete & Ready for Testing  
**Last Updated**: April 2, 2026
