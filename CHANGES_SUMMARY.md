# Used Materials Column & Request Linking Implementation

## Summary
Added comprehensive support for linking Used Materials to Material Requests with role-based access control (Technician role only) and approval logic.

## Changes Made

### 1. **Models.py - Database Schema Updates**

#### MaterialRequest Model Changes:
- Added `related_name='material_requests'` to Material ForeignKey for better relationship management
- Added `related_name='material_requests'` to User (requester) ForeignKey
- Added `used_materials_count` property - returns count of used materials linked to the request
- Added `used_materials_display` property - returns formatted display of used materials (e.g., "2x Internet Cable, 1x Dish")

#### UsedMaterial Model Changes:
- Added `material_request` ForeignKey field (nullable, optional linking)
  - Links each used material to its parent material request
  - Allows tracking which materials were actually used for specific requests
  - Soft delete capability (SET_NULL when request is deleted)

### 2. **Migration**
- Created migration `0017_usedmaterial_material_request_and_more.py`
- Applied migration successfully to update database schema
- No data loss - all existing records preserved with NULL values for new field

### 3. **Forms.py - UsedMaterialForm Updates**

Enhanced form fields:
- Added `material_request` field to form Meta class
- Added corresponding widget configuration for `material_request` Select dropdown
- Updated form __init__ method to:
  - **For Technicians**: Filter material_request dropdown to show ONLY approved MaterialRequest objects for that technician
  - **For Admin/Storekeeper**: Show all approved MaterialRequest objects
  - Apply `select_related()` optimization for better query performance
  - Add helpful help text to fields

Filtering Logic:
```python
approved_requests = MaterialRequest.objects.filter(
    requester=user, 
    status='Approved'
)
# Only approved materials and requests shown to technicians
```

### 4. **Views.py - used_materials_view Updates**

Security enhancements:
- Added `select_related('material', 'material_request')` for optimized queries
- Updated CREATE action:
  - Validates material_request belongs to requesting technician
  - Only allows linking to approved requests the user owns
  - Sets material_request on save if provided
- Updated EDIT action:
  - Allows updating the material_request link
  - Clears link if invalid request is provided
  - Maintains same approval validation
- DELETE action: Works as before

### 5. **Admin.py - Admin Interface Customization**

#### MaterialRequestAdmin:
- Custom admin class for better MaterialRequest display
- List display columns:
  - `id`, `requester`, `material`, `quantity`, `status`
  - **`used_materials_count`** - Shows count of linked used materials
  - **`used_materials_display`** - Shows formatted list of used materials
  - `requested_at` - Request timestamp
- Advanced filtering by status, date, category
- Search by requester username, material name, notes
- Readonly fields for computed properties and timestamps
- Organized fieldsets for better admin UX

#### UsedMaterialAdmin:
- Custom admin class for UsedMaterial records
- List display with `material_request` column
- Filtering by status, date, category
- Search functionality
- Readonly timestamps
- Organized fieldsets by section

## Features Implemented

### ✅ Role-Based Access Control
- **Technician Only**: Can access and create used materials with only approved requests/materials
- **Admin/Storekeeper**: Restricted from using this feature (as per original design)
- Server-side validation on all create/edit operations

### ✅ Approval Logic
- Only materials from MaterialRequest objects with `status='Approved'` are available
- Technicians can only link requests they created and that are approved
- Prevents unauthorized material usage tracking

### ✅ Table Relationship
- `UsedMaterial.material_request` → `MaterialRequest` (many-to-one)
- `MaterialRequest.used_materials` → `UsedMaterial` (reverse relation)
- Optional linking (material can be used without linking to request)

### ✅ Admin Display
- Django admin shows used materials count for each request
- Displays detailed list of used materials under each request
- Easy navigation and filtering in admin interface

## Usage Examples

### For Technicians:
```
1. Create Material Request (status: Pending)
2. Wait for admin approval (status: Approved)
3. Create Used Material record
4. Select approved Material Request from dropdown
5. Record material usage with client info
```

### In Django Admin:
```
Materials Request list view:
- See "Used Materials Count" column
- See "Used Materials Display" column with items like "2x Internet Cable"
- Filter requests by approval status
- Click on request to see all linked used materials
```

## Database Schema
```
MaterialRequest
├── material_requests (reverse from Material)
├── material_requests (reverse from User)
└── used_materials (reverse from UsedMaterial) ← NEW

UsedMaterial
├── technician (User)
├── material (Material)
└── material_request (MaterialRequest) ← NEW
```

## Security Considerations
- ✅ Technicians can only use approved materials
- ✅ Technicians can only link their own approved requests
- ✅ Server-side validation on all operations
- ✅ No way to bypass approval workflow
- ✅ Admin can view all relationships for auditing

## Testing Checklist
- [ ] Verify migration applied successfully
- [ ] Test Technician can create used material with request link
- [ ] Test only approved requests appear in dropdown
- [ ] Test admin view shows used materials count
- [ ] Test admin view shows used materials display
- [ ] Verify used materials count updates when records added/deleted
- [ ] Test role-based access restrictions
- [ ] Verify no errors in Django system check

## Files Modified
1. `isp_inventory/models.py` - Added relationships and properties
2. `isp_inventory/forms.py` - Updated UsedMaterialForm with filtering
3. `isp_inventory/views.py` - Updated used_materials_view with linking logic
4. `isp_inventory/admin.py` - Added custom admin classes with display columns
5. `isp_inventory/migrations/0017_*.py` - Auto-generated migration

## Backward Compatibility
✅ All changes are backward compatible:
- New `material_request` field is nullable
- Existing used materials without request link continue to work
- All existing queries updated with optimization hints
- No breaking changes to APIs or views
