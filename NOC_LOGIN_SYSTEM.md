# NOC Login System - Complete Setup

## ✅ Implementation Complete

The NOC role now has a completely separate and dedicated login system with its own views, URLs, and template.

---

## 🔐 Authentication Flow

### **Current Flow (After Implementation)**

#### **1. Main Login** (`/login/`)
Used by: Admin, Storekeeper, Branch roles
```
User visits /login/
    ↓
Enters credentials
    ↓
System authenticates user
    ↓
✅ Logs in → Redirects to /dashboard/
❌ Invalid → Shows error message
```

#### **2. NOC-Only Login** (`/noc/login/`)
Used by: NOC role ONLY
```
NOC User visits /noc/login/
    ↓
Enters NOC credentials
    ↓
System authenticates user
    ↓
Checks if user has role='NOC' in UserProfile
    ↓
✅ NOC user → Redirects to /noc/dashboard/
❌ Not NOC → Shows error "Access denied. This login page is for NOC role only."
❌ Invalid creds → Shows error "Invalid credentials"
❌ Inactive user → Shows error "Your account is inactive"
❌ No profile → Shows error "User profile not found"
```

---

## 📁 File Structure

### **Backend - Views**

**`Noc/views.py`**
```python
def noc_login_view(request):
    """
    NOC-only login page
    - Authenticates user
    - Checks if role is 'NOC'
    - Only redirects to /noc/dashboard/ if NOC
    - Shows appropriate error messages
    """

def noc_logout_view(request):
    """
    NOC logout
    - Logs out user
    - Redirects to /noc/login/
    """
```

### **URLs**

**`Noc/urls.py`**
```python
app_name = 'noc'

urlpatterns = [
    path('login/', views.noc_login_view, name='login'),          # /noc/login/
    path('logout/', views.noc_logout_view, name='logout'),       # /noc/logout/
    
    # Protected routes (require @login_required and @noc_role_required)
    path('dashboard/', views.noc_dashboard, name='dashboard'),
    path('materials/', views.noc_materials, name='materials'),
    # ... more routes
]
```

**`isp_inventory/urls.py`**
```python
urlpatterns = [
    path('', views.login_view, name='login'),                    # /login/
    # ... other routes
]
```

### **Templates**

**`templates/noc/login.html`**
- Custom NOC-branded login template
- Purple/Indigo gradient colors
- "NOC System" branding
- "Network Operations Center" subtitle
- Links back to main login for non-NOC users
- Role access restriction notice

**`templates/inventory/login.html`**
- Main login template for Admin/Branch/Storekeeper
- Updated with link to NOC login (`{% url 'noc:login' %}`)
- Says "NOC Team? Use NOC Login"

---

## 🔗 URL References

### **Template Usage**

| Purpose | Old URL | New URL |
|---------|---------|---------|
| NOC Login | N/A | `{% url 'noc:login' %}` → `/noc/login/` |
| NOC Logout | `{% url 'noc:logout' %}` | `{% url 'noc:logout' %}` → `/noc/logout/` |
| Main Login | `{% url 'login' %}` | `{% url 'login' %}` → `/login/` |
| Main Logout | `{% url 'logout' %}` | `{% url 'logout' %}` → `/logout/` |

### **Redirect Logic**

```
/noc/login/ (POST)
    ↓
noc_login_view() authenticates user
    ↓
Checks profile.role == 'NOC'
    ↓
✅ YES → login() → redirect('noc:dashboard') → /noc/dashboard/
❌ NO  → messages.error() → render('noc/login.html')

/login/ (POST)
    ↓
login_view() authenticates user
    ↓
login() → redirect('dashboard') → /dashboard/
```

---

## 🎨 Template Features

### **NOC Login (`/noc/login/`)**

**Visual Design:**
- Purple/Indigo gradient background
- Broadcast tower icon 🎙️
- "NOC System" title
- "Network Operations Center" subtitle
- Sign in call-to-action

**Functionality:**
- Username input field
- Password input field (with show/hide toggle)
- "Remember me" checkbox (1 hour session)
- Error message display
- Auto-hide messages after 5 seconds
- Responsive design (Mobile/Tablet/Desktop)
- Dark mode support

**Security:**
- CSRF token included
- Password field type (hidden by default)
- Role validation on backend
- Account active check
- User profile existence check

**User Links:**
- "Not NOC? Login as other role" → Links to `/login/`

### **Main Login (`/login/`)**

**Added Link:**
- "NOC Team? Use NOC Login" → Links to `/noc/login/`

---

## 🔒 Security Features

### **Access Control**

1. **NOC Login Page Protection:**
   - Anyone can view the page (not logged in check)
   - Only NOC role users can successfully log in
   - Prevents information leakage (doesn't say "user not found")

2. **Session Management:**
   - 2 options: Browser session (closes on exit) or 1-hour session
   - Set via `remember_me` checkbox
   - Configurable in code

3. **Account Status Checks:**
   - ✅ User exists
   - ✅ User is active
   - ✅ User profile exists
   - ✅ User has NOC role

4. **Error Messages:**
   - Role mismatch → "Access denied. This login page is for NOC role only."
   - Inactive account → "Your account is inactive. Please contact administrator."
   - Invalid credentials → "Invalid credentials. Please try again."
   - Missing profile → "User profile not found. Please contact administrator."

---

## 📊 User Journey

### **NOC User Login Journey**
```
1. User opens NOC login page: /noc/login/
   ↓
2. Enters username and password
   ↓
3. System verifies:
   - User exists? ✅
   - Password correct? ✅
   - Account active? ✅
   - User profile exists? ✅
   - Role is 'NOC'? ✅
   ↓
4. User logged in
   ↓
5. Redirected to /noc/dashboard/
   ↓
6. NOC Dashboard loaded with full navbar
```

### **Non-NOC User Tries NOC Login**
```
1. User opens NOC login page: /noc/login/
   ↓
2. Enters credentials (e.g., Admin user)
   ↓
3. System verifies:
   - User exists? ✅
   - Password correct? ✅
   - Account active? ✅
   - User profile exists? ✅
   - Role is 'NOC'? ❌
   ↓
4. Error: "Access denied. This login page is for NOC role only."
   ↓
5. User stays on /noc/login/ to retry or click link to main login
```

### **NOC User Logout Journey**
```
1. Click logout in NOC navbar
   ↓
2. POST to /noc/logout/
   ↓
3. noc_logout_view() executes
   ↓
4. Call logout(request) [clears session]
   ↓
5. Redirect to /noc/login/
   ↓
6. User sees NOC login page again
```

---

## ⚙️ Configuration

### **Django Settings (`ibccl/settings.py`)**

Current settings (unchanged):
```python
LOGIN_URL = 'login'                    # Default login URL for @login_required
LOGIN_REDIRECT_URL = 'dashboard'       # Default redirect after login
```

These settings apply to the main `isp_inventory.login_view`. The NOC login is completely separate and doesn't use these settings.

---

## 🔍 Testing Checklist

- [ ] Admin user can login via `/login/`
- [ ] Admin user redirected to `/dashboard/`
- [ ] Admin user cannot access `/noc/login/` with their account
- [ ] NOC user can login via `/noc/login/`
- [ ] NOC user redirected to `/noc/dashboard/`
- [ ] NOC user cannot login via main `/login/` (if logic checks role)
- [ ] Invalid credentials show error on both login pages
- [ ] "Remember me" checkbox works (1-hour session)
- [ ] Browser close logout works (session expires)
- [ ] Logout button redirects NOC users to `/noc/login/`
- [ ] "NOC Team? Use NOC Login" link works on main login
- [ ] "Login as other role" link works on NOC login
- [ ] NOC navigation navbar appears after NOC login
- [ ] Main dashboard navbar appears after main login
- [ ] Dark mode works on NOC login page
- [ ] Mobile responsive on NOC login page

---

## 🚀 Database Requirements

### **Required UserProfile Data**
For NOC login to work, each NOC user needs:
```python
UserProfile.objects.create(
    user=user_object,
    role='NOC',        # Must be exactly 'NOC'
    # ... other fields
)
```

### **User Account Requirements**
```python
User.objects.create_user(
    username='noc_user',
    email='noc@example.com',
    password='secure_password',
    is_active=True      # Must be True
)
```

---

## 📋 Related URLs

| URL | View | Purpose |
|-----|------|---------|
| `/` | Redirects | Home (currently redirects to login or dashboard) |
| `/login/` | `isp_inventory.login_view` | Main login (Admin/Branch/Storekeeper) |
| `/logout/` | `isp_inventory.logout_view` | Main logout |
| `/noc/login/` | `Noc.noc_login_view` | NOC login (NOC only) |
| `/noc/logout/` | `Noc.noc_logout_view` | NOC logout |
| `/dashboard/` | `isp_inventory.dashboard` | Main dashboard (Admin/Branch/Storekeeper) |
| `/noc/dashboard/` | `Noc.noc_dashboard` | NOC dashboard (NOC only) |

---

## 🔄 Migration Path (If Needed)

If you had NOC users logging in via main login before:
1. No migration needed - users still have valid sessions
2. On logout/next login, they'll use `/noc/login/` instead
3. All NOC data remains intact (uses same UserProfile)

---

## 📞 Troubleshooting

### **"Access denied. This login page is for NOC role only."**
- Check UserProfile.role = 'NOC' (case-sensitive)
- Verify user profile exists in database
- Check user is_active = True

### **"User profile not found"**
- Ensure UserProfile created for user
- Check OneToOne relationship is intact

### **"Your account is inactive"**
- Set User.is_active = True
- Contact administrator to activate account

### **User stuck on login page**
- Clear browser cookies/cache
- Check session settings in Django
- Verify CSRF token is included

---

## 📝 Files Modified

### **Backend**
- ✅ `Noc/views.py` - Added noc_login_view and noc_logout_view
- ✅ `Noc/urls.py` - Added login and logout URLs
- ✅ `isp_inventory/views.py` - Removed NOC redirect logic

### **Frontend**
- ✅ `templates/noc/login.html` - Created NOC login template
- ✅ `templates/inventory/login.html` - Added link to NOC login

---

## ✨ Key Features

- ✅ Separate NOC authentication system
- ✅ Role-based access control (only NOC role)
- ✅ Custom NOC branding and design
- ✅ Comprehensive error messages
- ✅ Session management options
- ✅ Remember me functionality
- ✅ Dark mode support
- ✅ Mobile responsive
- ✅ Password visibility toggle
- ✅ Cross-navigation between login pages
- ✅ Secure session handling
- ✅ Account status validation

---

**Status**: ✅ Complete & Ready for Testing  
**Last Updated**: April 2, 2026
