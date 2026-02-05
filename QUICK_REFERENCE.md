# Quick Reference: Used Materials Feature

## What Was Added?

### 1. **Model Relationship**
```
MaterialRequest 1 ──→ ∞ UsedMaterial
```
- Each UsedMaterial can now link to its parent MaterialRequest
- Optional linking (nullable field)
- Soft delete when request is deleted (SET_NULL)

### 2. **Form Enhancement**
- New dropdown field: "Material Request (Optional)"
- Only shows approved requests for Technicians
- All requests filtered for Admin/Storekeeper role

### 3. **Admin Display**
Two new columns visible in Django admin:
- **used_materials_count**: Shows number of linked used materials
- **used_materials_display**: Shows formatted list like "2x Cable, 1x Dish"

### 4. **Security**
- Technicians can ONLY use approved materials
- Technicians can ONLY link their OWN approved requests
- Server-side validation on all operations

## Files Changed

| File | Changes |
|------|---------|
| `models.py` | Added material_request FK to UsedMaterial + 2 properties to MaterialRequest |
| `forms.py` | Added material_request field with smart filtering for Technicians |
| `views.py` | Updated used_materials_view to handle request linking |
| `admin.py` | New MaterialRequestAdmin and UsedMaterialAdmin classes |
| `migrations/0017_*.py` | Database schema update (auto-generated) |

## How to Use

### As a Technician:
1. Request materials (status: Pending)
2. Wait for approval (status: Approved)
3. Create Used Material record:
   - Fill out form fields
   - Select from approved materials only
   - **Optionally** link to the approved request
   - Save

### As an Admin:
1. Go to Django admin: `/admin/isp_inventory/materialrequest/`
2. View Material Request list
3. See columns:
   - `used_materials_count` - How many materials used
   - `used_materials_display` - Which materials and quantities
4. Click on request to see full details with linked materials

## Key Properties

```python
# On MaterialRequest instances:
request.used_materials.all()          # QuerySet of linked UsedMaterial objects
request.used_materials_count          # Property: returns integer count
request.used_materials_display        # Property: returns formatted string

# On UsedMaterial instances:
used_material.material_request        # ForeignKey to MaterialRequest (nullable)
used_material.technician              # ForeignKey to User
used_material.material                # ForeignKey to Material
```

## Approval Workflow

```
┌─────────────┐
│  Request    │ Created by Technician
│  Pending    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Review by  │ Admin approves/rejects
│  Admin      │
└──────┬──────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
Approved  Rejected
   │
   ▼
┌─────────────────────────────┐
│ Create Used Material Record │
│ - Can select from approved  │
│   materials only            │
│ - Can link to request       │
│ - Record client info        │
│ - Record technical issue    │
└─────────────────────────────┘
   │
   ▼
┌─────────────────────────────┐
│ View in Admin Dashboard     │
│ - See count of items used   │
│ - See list of items         │
│ - Audit trail of usage      │
└─────────────────────────────┘
```

## API Examples

### Query: Get used materials for a request
```python
request = MaterialRequest.objects.get(id=1)
items = request.used_materials.all()
count = request.used_materials_count

for item in items:
    print(f"{item.quantity}x {item.material.name} used by {item.technician}")
```

### Query: Get all requests with usage
```python
requests = MaterialRequest.objects.filter(
    status='Approved'
).prefetch_related('used_materials')

for req in requests:
    print(f"{req.material.name}: {req.used_materials_count} items used")
```

### Create: Link used material to request
```python
UsedMaterial.objects.create(
    technician=user,
    material=material,
    material_request=request,  # NEW
    quantity=2,
    client_name='John',
    status='Accepted'
)
```

## Database Schema

### New Field
```sql
ALTER TABLE isp_inventory_usedmaterial 
ADD COLUMN material_request_id INTEGER REFERENCES isp_inventory_materialrequest(id);

CREATE INDEX idx_material_request 
ON isp_inventory_usedmaterial(material_request_id);
```

### Relations
```
MaterialRequest
├── material → Material
├── requester → User
└── used_materials (reverse relation)

UsedMaterial
├── technician → User
├── material → Material
└── material_request → MaterialRequest  (NEW)
```

## Role-Based Access

| Feature | Technician | Admin | Storekeeper |
|---------|-----------|-------|-------------|
| Create Used Material | ✓ (approved only) | ✗ | ✗ |
| Link to Request | ✓ (own requests) | ✓ (all) | ✗ |
| View Used Materials | ✓ (own) | ✓ (all) | ✗ |
| Edit Used Material | ✓ (own) | ✓ (all) | ✗ |
| See Request Count | N/A | ✓ (admin) | ✗ |
| See Request List | N/A | ✓ (admin) | ✗ |

## Testing Checklist

- [ ] Migration 0017 applied successfully
- [ ] No Django errors: `python manage.py check`
- [ ] Technician can create used material
- [ ] Form shows only approved requests
- [ ] Admin can see used_materials_count column
- [ ] Admin can see used_materials_display column
- [ ] Count updates when materials added/deleted
- [ ] Technician cannot link other users' requests
- [ ] Technician cannot use unapproved materials

## Troubleshooting

**Problem**: Material Request dropdown is empty
- **Solution**: Create a MaterialRequest with status='Approved' first

**Problem**: used_materials columns not showing in admin
- **Solution**: Run `python manage.py migrate`

**Problem**: Can't link material request
- **Solution**: Verify MaterialRequest belongs to current user and status is 'Approved'

## Performance Notes

- ✓ Optimized queries with `select_related` in views
- ✓ Database indexes automatically created on ForeignKey
- ✓ Admin uses readonly properties for display (no extra queries)
- ✓ Form filtering optimized with `distinct()` to avoid duplicates

## Backward Compatibility

✓ All changes are fully backward compatible:
- New field is nullable
- Existing records work unchanged
- Existing APIs continue to work
- No breaking changes to templates

## Next Steps

1. Test in development environment
2. Create any custom templates if needed
3. Update user documentation
4. Deploy to production with migration
5. Monitor for any issues in logs

## Support

For issues or questions:
1. Check IMPLEMENTATION_GUIDE.md for detailed info
2. Check CHANGES_SUMMARY.md for what was changed
3. Review Django logs for errors
4. Verify migration was applied: `python manage.py showmigrations`
