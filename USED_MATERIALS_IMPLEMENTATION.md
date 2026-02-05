# Used Materials Approval System - Implementation Guide

## Overview
This document outlines the implementation of a used materials approval system with automatic material count deduction.

## System Architecture

### Key Features
1. **Technicians** can record used materials with detailed client information
2. **Admin/Storekeeper** can approve or reject used material records
3. **Automatic Deduction** - When approved, materials are automatically deducted from inventory (only Normal stock status)
4. **Material Category Display** - All used material records show the material category
5. **Comprehensive Tracking** - Full audit trail with timestamps and notes

## Components Implemented

### 1. Database Model (UsedMaterial)
Located in: `isp_inventory/models.py`

**Fields:**
- `technician` - ForeignKey to User (who used the material)
- `material` - ForeignKey to Material (which material was used)
- `material_request` - ForeignKey to MaterialRequest (optional link to request)
- `client_name` - CharField (who received the service)
- `client_address` - TextField (location)
- `client_phone` - CharField (contact)
- `quantity` - IntegerField (how much was used)
- `issue` - TextField (technical notes)
- `status` - CharField with choices: Pending, Accepted, Rejected
- `admin_note` - TextField (approver's notes)
- `added_at`, `updated_at` - Timestamps

**Properties:**
- `category` - Returns material category
- `material_name` - Returns material name
- `technician_full_name` - Returns technician's full name

### 2. Views (Business Logic)

#### A. `used_materials_view` (Technician Dashboard)
**URL:** `/used-materials/`
**Purpose:** Allows technicians to record material usage
**Actions:**
- Create new used material record
- Edit existing records (Pending status only)
- Delete records
- Link to material requests (optional)

**Validations:**
- Only approved materials can be used
- Only technicians can access this view
- Materials shown are filtered to approved requests

#### B. `approve_used_materials` (Admin Dashboard)
**URL:** `/used-materials/approve/`
**Purpose:** Central approval dashboard for admins/storekeepers
**Features:**
- View all used materials pending approval
- Filter by status (Pending, Accepted, Rejected)
- Search by material name, client name, technician
- Stats dashboard showing approval counts

**Access Control:**
- Admin and Storekeeper only

#### C. `manage_used_material` (Approval Detail Page)
**URL:** `/used-materials/<id>/manage/`
**Purpose:** Individual approval/rejection interface
**Actions:** 
- Approve (with automatic stock deduction for Normal materials)
- Reject (with optional admin notes)
- View approval history

**Key Logic:**
```python
if action == 'accept':
    if material.status == 'Normal':
        # Deduct from inventory
        material.quantity -= used_material.quantity
        material.save()  # Updates status automatically
        # Mark as accepted
        used_material.status = 'Accepted'
    else:
        # Accept but don't deduct (Low/Out of stock)
        used_material.status = 'Accepted'
        messages.warning("Material not deducted (Low/Out stock)")
```

### 3. Forms

#### `UsedMaterialForm` (Updated)
**Location:** `isp_inventory/forms.py`

**New Features:**
- **Category Field** - Read-only field that auto-populates from selected material
- **Material Filtering** - Technicians only see approved materials
- **Client Information** - Fields for client name, address, phone
- **Auto-validation** - Ensures technicians can only use approved materials

**Field Validation:**
- Technicians can only select from materials they've been approved to use
- Material selection triggers category auto-population
- Admin/Storekeeper can see all materials

### 4. Templates

#### A. `approve_used_materials.html`
**Location:** `templates/inventory/approve_used_materials.html`

**Features:**
- Summary stats panel (Pending, Accepted, Rejected, Total)
- Filterable table with all fields:
  - Technician name
  - Material name
  - Category (colored badge)
  - Client name, address, phone
  - Quantity used
  - Date/Time
  - Current status
  - Action button (Review/View)
- Search and filter functionality

#### B. `manage_used_material.html`
**Location:** `templates/inventory/manage_used_material.html`

**Sections:**
1. **Material Information**
   - Material name
   - Category (colored badge)
   - Material status (Normal/Low Stock/Out)
   - Available quantity
   - Quantity used

2. **Client Information**
   - Client name
   - Full address
   - Phone (clickable tel: link)
   - Date & time recorded

3. **Technical Notes**
   - Issue/notes in textarea

4. **Related Material Request** (if any)
   - Links to the original request
   - Shows approved quantity and status

5. **Approval Actions** (if Pending)
   - Admin notes textarea
   - Approve button (with conditional text based on material status)
   - Reject button
   - Warning if material not in Normal status

6. **Approval History** (if Already Approved/Rejected)
   - Shows final status
   - Admin notes
   - Last updated timestamp

### 5. URL Routes (Updated)
**Location:** `isp_inventory/urls.py`

New routes added:
```python
path('used-materials/approve/', views.approve_used_materials, name='approve_used_materials'),
# Used existing path for individual approval:
path('used-materials/<int:pk>/manage/', views.manage_used_material, name='manage_used_material'),
```

### 6. Navigation Updates
**Location:** `templates/inventory/base.html`

**Added Links:**
- **For Technicians:** "Record Materials" link to used_materials_view
- **For Admin/Storekeeper:** "Approve Materials" link to approve_used_materials

**Conditional Rendering:**
```django
{% if user.userprofile.role in 'Admin,Storekeeper' %}
    <!-- Show approval link -->
{% endif %}

{% if user.userprofile.role == 'Technician' %}
    <!-- Show record materials link -->
{% endif %}
```

## Workflow

### Technician Workflow
1. Navigate to "Record Materials" page
2. Click "Add Used Material"
3. Fill form:
   - Select material (auto-filtered to approved materials)
   - Material category auto-populates
   - Enter client information
   - Enter quantity used
   - Add technical notes
   - Optionally link to material request
4. Submit form
5. Record is created with Pending status
6. Admin must approve before count is deducted

### Admin/Storekeeper Workflow
1. Navigate to "Approve Materials" page
2. View all pending used materials in one table
3. Can filter by status or search
4. Click "Review" on pending items
5. On detail page:
   - Review all material and client information
   - Check material status (Normal/Low/Out)
   - Add admin notes if needed
   - Approve:
     - If Normal: Deducts inventory and marks as Accepted
     - If Low/Out: Accepts but doesn't deduct (with warning)
   - Or Reject with notes
6. Approval updates material count automatically (with transaction safety)

## Data Integrity & Safety

### Transaction Protection
- All approval operations use `transaction.atomic()` 
- Prevents race conditions when updating material stock
- Uses `select_for_update()` database lock

### Business Rules
- Only Normal status materials have stock deducted
- Low Stock and Out of Stock materials can be recorded but not deducted
- Material status automatically updates after deduction
- Once approved, records cannot be modified (can edit while Pending)

### Validation
- Sufficient stock check before deduction
- Technician can only use approved materials
- Admin-only access to approval functions
- Audit trail via admin_note and updated_at fields

## Key Statistics & Reports

### Dashboard Stats
- **Total Pending:** Count of Pending approvals
- **Total Accepted:** Count of approved materials
- **Total Rejected:** Count of rejected materials
- **Total:** Sum of all records

### Filtering
- By status (Pending, Accepted, Rejected)
- By search term (material name, client, technician)

## Error Handling

### User-Friendly Messages
- ✅ "Approval successful. X units deducted."
- ⚠️ "Material approved but NOT deducted (Low Stock)"
- ❌ "Insufficient stock available"
- ❌ "Permission denied. Admin/Storekeeper only"

### Edge Cases Handled
- Material status changes to Low Stock after deduction
- Multiple approvals of same material
- Trying to approve already-approved records
- Insufficient permissions checks

## Integration Points

### Material Request Tracking
- Used materials can be linked to original material requests
- Shows full request context during approval

### Material Quantity Updates
- Deduction directly updates Material.quantity
- Material.save() triggers automatic status refresh:
  - quantity ≤ 0 → Out of Stock
  - 0 < quantity < min_stock_level → Low Stock
  - quantity ≥ min_stock_level → Normal (unless Reserved/Deprecated)

## Testing Checklist

- [ ] Technician can record used material
- [ ] Material category displays correctly
- [ ] Only approved materials show in dropdown
- [ ] Admin can see all pending approvals
- [ ] Admin can filter by status
- [ ] Admin can search by material/client/technician
- [ ] Approval deducts Normal status materials
- [ ] Approval doesn't deduct Low/Out stock
- [ ] Material status updates after deduction
- [ ] Rejection doesn't deduct
- [ ] Cannot modify approved records
- [ ] Audit trail (admin_note, updated_at) saves correctly
- [ ] Navigation links show for correct roles
- [ ] Permission checks prevent unauthorized access

## Future Enhancements

1. **Bulk Approval:** Approve multiple records at once
2. **Email Notifications:** Notify technician when approved/rejected
3. **Approval Workflow:** Multiple-level approvals (Storekeeper → Admin)
4. **Reports:** Export approval history to PDF/CSV
5. **Auto-linking:** Auto-link used materials to related material requests
6. **Stock Reservations:** Hold material until approval
7. **Partial Approvals:** Approve different quantity than requested

## Support & Troubleshooting

### If Navigation Link Missing
- Check user's role (Admin/Storekeeper for approval, Technician for recording)
- Verify UserProfile exists for user
- Clear browser cache

### If Deduction Not Working
- Verify material status is "Normal"
- Check available quantity > requested quantity
- Review transaction logs for errors

### If Form Not Showing Category
- Ensure material is selected in dropdown
- Refresh page if category doesn't populate
- Check browser console for JavaScript errors

## Version History

- **v1.0** (Current) - Initial implementation with approval workflow
  - Used material recording
  - Admin approval system
  - Automatic stock deduction
  - Full audit trail
  - Role-based access control
