# Quick Implementation Guide - Material Request Type System

## 🎯 What Was Changed

### **1. Model Enhancement**
```python
# Added to MaterialRequest model
request_type = models.CharField(
    max_length=20, 
    choices=[('Regular', 'Regular'), ('Advance', 'Advance')],
    default='Regular'
)
```

### **2. Form Update**
```python
# RequestForm now includes
fields = ['material', 'quantity', 'request_type', 'user_note']
widgets = {
    'request_type': forms.RadioSelect(choices=[...])
}
```

### **3. View Logic**
- **Dashboard:** Now shows advance material data with request type filtering
- **Requests:** Separated into Regular and Advance sections automatically
- **User Filter:** Only shows Branch users in Admin/Storekeeper dropdown

### **4. UI Updates**
- **Type Column:** Added to both Regular and Advance request tables
- **Advance Modal:** New tab system for Storekeeper pending requests
- **Color Coding:** 
  - Regular = Blue
  - Advance = Indigo

---

## 📋 Branch User Workflow

### Creating a Request:
1. Click **"Request Material"** button
2. Select Material from dropdown
3. Enter Quantity
4. Choose Request Type:
   - **Regular** - Standard material request
   - **Advance** - Priority/advance booking
5. Add optional notes
6. Submit

### Viewing Advance Materials:
1. Dashboard → "Advance Materials" card
2. View your approved advance materials
3. See current stock count
4. Check request type in "Type" column

---

## 👨‍💼 Admin/Storekeeper Workflow

### Approving Requests:
1. Go to **"Material Requests"** page
2. View all requests separated by type
3. Filter by Branch user (dropdown)
4. For each request:
   - View Type (Regular/Advance)
   - Approve/Reject/Delete
   - Add admin note

### Storekeeper Special Access:
1. Dashboard → "Advanced Materials" card
2. Click to open modal
3. Switch to **"Pending Requests"** tab
4. See recent 10 pending requests
5. All pending requests (both Regular & Advance)

---

## 🗂️ Database Schema

### MaterialRequest Model
```
Field: request_type
Type: CharField(max_length=20)
Choices: 'Regular' | 'Advance'
Default: 'Regular'
Migration: 0025_materialrequest_request_type
```

### Color Scheme
| Type | Color | Theme |
|------|-------|-------|
| Regular | Blue | 🔵 Blue-100/800 |
| Advance | Indigo | 🔷 Indigo-100/800 |

---

## 🔍 Key Query Patterns

### Get Advance Materials for User:
```python
MaterialRequest.objects.filter(
    requester=user,
    request_type='Advance',
    status='Approved'
)
```

### Get Pending Requests:
```python
MaterialRequest.objects.filter(
    status='Pending'
).select_related('material', 'requester')
```

### Get All Regular Requests:
```python
MaterialRequest.objects.filter(
    request_type='Regular'
)
```

---

## 📱 Frontend Selectors

### Tab Switching:
```javascript
switchAdvanceTab('advanceTab')      // Show Advance Materials
switchAdvanceTab('pendingTab')      // Show Pending Requests
```

### Modal IDs:
- `#advanceMaterialsModal` - Main advance materials modal
- `#advanceTab` - Advance materials content
- `#pendingTab` - Pending requests content

---

## ✅ Deployment Checklist

- [x] Database migration created ✓
- [x] Database migration applied ✓
- [x] Model modified ✓
- [x] Form updated ✓
- [x] Views enhanced ✓
- [x] Dashboard template updated ✓
- [x] Requests template updated ✓
- [x] No breaking changes ✓
- [x] Backward compatible ✓
- [x] Static check passed ✓

---

## 🧪 Quick Testing Commands

### Check Project:
```bash
python ibccl/manage.py check
```

### Run Tests:
```bash
python ibccl/manage.py test isp_inventory
```

### Shell Test:
```python
python ibccl/manage.py shell

# In shell:
from isp_inventory.models import MaterialRequest
MaterialRequest.objects.filter(request_type='Advance').count()
```

---

## 📊 Key Statistics to Track

**After Implementation, Monitor:**
- Regular vs Advance request ratio
- Advance request approval rate
- Storekeeper pending request clearance time
- Type-specific approval timeline

---

## 🔗 Template Tags Used

```django
<!-- Type Display -->
{% if req.request_type == 'Advance' %}
    <span class="bg-indigo-100">Advance</span>
{% else %}
    <span class="bg-blue-100">Regular</span>
{% endif %}

<!-- Tab Control -->
{% if user.userprofile.role == 'Storekeeper' %}
    <!-- Show pending tab -->
{% endif %}
```

---

## 📞 Support Reference

### Role-Specific Features
| Role | Can Create | Can Approve | Views Pending | Filter Dropdown |
|------|-----------|-----------|---------------|-----------------|
| Branch | Yes | No | No | No |
| Admin | No | Yes | No | Yes (Branch) |
| Storekeeper | No | No | Yes | Yes (Branch) |

### Troubleshooting

**Issue:** Type column not showing
- **Solution:** Refresh browser cache, check migration applied

**Issue:** Pending tab not visible
- **Solution:** Verify user role is 'Storekeeper'

**Issue:** Old requests showing no type
- **Solution:** All default to 'Regular' - this is correct

---

## 📚 File Reference

| File | Changes | Lines |
|------|---------|-------|
| models.py | Added request_type field | ~145-146 |
| forms.py | Added request_type to form | ~61-68 |
| views.py | Dashboard & requests updates | Multiple |
| dashboard.html | Advance modal with tabs | ~431-516 |
| requests.html | Type column display | ~102-110 |

---

**Last Updated:** February 17, 2026  
**Status:** Production Ready ✓
