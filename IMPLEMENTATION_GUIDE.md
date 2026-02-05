# Implementation Guide: Used Materials Column with Request Linking

## Overview
This implementation adds a "Used Materials" relationship tracking system that links used material entries to their parent material requests, with strict role-based access control for Technicians only.

## Architecture

### Database Relationships
```
Material Request (Approved)
    ↓
Technician can create Used Material entries
    ↓
Each Used Material can be linked to the parent Material Request
    ↓
Admin can see: Count & List of used materials for each request
```

### Flow Diagram
```
1. Technician submits MaterialRequest
   ↓
2. Admin approves MaterialRequest
   ↓
3. Technician creates UsedMaterial record
   ├─ Selects from APPROVED materials only
   ├─ Optionally links to approved MaterialRequest
   └─ Records client info & technical details
   ↓
4. Admin views MaterialRequest with:
   ├─ used_materials_count property
   └─ used_materials_display property
```

## Model Structure

### MaterialRequest Model
```python
class MaterialRequest(models.Model):
    material = ForeignKey(Material, related_name='material_requests')
    requester = ForeignKey(User, related_name='material_requests')
    quantity = IntegerField
    status = CharField('Pending'|'Approved'|'Rejected')
    
    # NEW PROPERTIES
    @property
    def used_materials_count(self):
        # Returns: Integer count of linked UsedMaterial objects
        
    @property
    def used_materials_display(self):
        # Returns: String like "2x Cable, 1x Dish"
```

### UsedMaterial Model
```python
class UsedMaterial(models.Model):
    technician = ForeignKey(User)
    material = ForeignKey(Material)
    material_request = ForeignKey(MaterialRequest, null=True, blank=True)  # NEW
    quantity = IntegerField
    status = CharField('Pending'|'Accepted'|'Rejected')
    client_name = CharField
    issue = TextField
```

## Technician Workflow

### Step 1: Request Material (Create MaterialRequest)
```python
# Technician creates request
request = MaterialRequest.objects.create(
    material=Material.objects.get(name='Internet Cable'),
    requester=technician_user,
    quantity=5,
    user_note='Needed for installation',
    status='Pending'  # Waiting for approval
)
```

### Step 2: Wait for Approval
- Admin reviews pending requests
- Admin sets status to 'Approved' or 'Rejected'

### Step 3: Create Used Material with Request Link
```python
# Form filtering in UsedMaterialForm.__init__:
# Only shows approved requests for this technician
approved_requests = MaterialRequest.objects.filter(
    requester=technician_user,
    status='Approved'
)

# Technician creates used material entry
used_material = UsedMaterial.objects.create(
    technician=technician_user,
    material=material,  # From approved request
    material_request=approved_request,  # LINK TO REQUEST (Optional)
    quantity=2,
    client_name='John Doe',
    client_address='123 Main St',
    issue='Installation of internet',
    status='Pending'
)
```

## Admin View Benefits

### MaterialRequest List View
```
ID | Requester | Material | Qty | Status | Used Count | Used Materials | Date
---|-----------|----------|-----|--------|------------|-----------------|------
1  | John      | Cable    | 5   | Appr   | 2          | 2x Cable, 1x... | 2024-01-15
2  | Jane      | Dish     | 3   | Pend   | 0          | -               | 2024-01-14
```

### MaterialRequest Detail View
```
Request Info
├─ Requester: John
├─ Material: Internet Cable
├─ Quantity: 5
├─ Status: Approved
├─ Requested: 2024-01-15

Used Materials (Count: 2)
├─ 2x Cable (Tech: John, Date: 2024-01-16)
└─ 1x Cable (Tech: John, Date: 2024-01-17)
```

## Form Filtering Logic

### For Technicians
```python
# Filter 1: Material dropdown
approved_material_ids = MaterialRequest.objects.filter(
    requester=user,
    status='Approved'
).values_list('material_id', flat=True).distinct()

material_queryset = Material.objects.filter(id__in=approved_material_ids)
# Result: Only materials from user's approved requests

# Filter 2: Material Request dropdown  
material_request_queryset = MaterialRequest.objects.filter(
    requester=user,
    status='Approved'
)
# Result: Only approved requests for this user
```

### For Admin/Storekeeper
```python
# Show all approved materials
material_queryset = Material.objects.all()

# Show all approved requests
material_request_queryset = MaterialRequest.objects.filter(status='Approved')
```

## Security Features

### Server-Side Validation
```python
# In used_materials_view:
material_request = form.cleaned_data.get('material_request')

# Verify request belongs to technician
if material_request and material_request.requester == request.user:
    um.material_request = material_request
else:
    messages.error("You can only link your own approved requests")
```

### Role-Based Access
```python
# Only Technicians can access
if role != 'Technician':
    messages.error("Access restricted to Technicians only.")
    return redirect('dashboard')
```

### Approval Workflow
```python
# Can only use approved materials
if material.id in approved_material_ids:
    # Process
else:
    messages.error("You can only record usage for approved materials.")
```

## API Examples

### Query Requests with Used Materials
```python
# Get request with all linked used materials
request = MaterialRequest.objects.get(id=1)

# Count linked used materials
count = request.used_materials_count  # Property returns 2
display = request.used_materials_display  # "2x Cable, 1x Dish"

# Get all used materials for a request
used_items = request.used_materials.all()
# QuerySet of UsedMaterial objects
```

### Reverse Queries
```python
# Get all material requests for a material
material = Material.objects.get(name='Cable')
requests = material.material_requests.all()
# QuerySet of MaterialRequest objects

# Get used materials for a technician
used = UsedMaterial.objects.filter(technician=user)
# Includes material_request foreign key
```

## Admin Customization

### MaterialRequestAdmin Features
```python
# Display columns
list_display = [
    'id',
    'requester',
    'material',
    'quantity',
    'status',
    'used_materials_count',    # Property-based display
    'used_materials_display',  # Formatted list
    'requested_at'
]

# Quick filters
list_filter = ['status', 'requested_at', 'material__category']

# Search
search_fields = ['requester__username', 'material__name', 'user_note']

# Custom fieldsets
fieldsets = (
    ('Request Info', {'fields': (...)}),
    ('Notes', {'fields': (...)}),
    ('Used Materials', {'fields': ('used_materials_count', 'used_materials_display')})
)
```

## Migration Details

### Migration File: 0017_usedmaterial_material_request_and_more.py
```python
# Changes applied:
# 1. Add material_request ForeignKey to UsedMaterial
# 2. Add related_name to Material ForeignKey in MaterialRequest
# 3. Add related_name to User ForeignKey in MaterialRequest

# Data impact:
# - No data loss (nullable field)
# - Existing records get NULL value for material_request
# - All existing queries continue to work
```

## Testing Scenarios

### Scenario 1: Technician Uses Approved Material
```
1. Technician A creates MaterialRequest for 5 cables (Pending)
2. Admin approves request (Status: Approved)
3. Technician A creates UsedMaterial:
   - Material: Cable (from approved request)
   - Material Request: Select approved request
   - Quantity: 2
   - Result: Successfully linked ✓
```

### Scenario 2: Technician Cannot Use Unapproved
```
1. Technician B creates MaterialRequest for dishes (Pending)
2. Admin rejects request (Status: Rejected)
3. Technician B tries to create UsedMaterial:
   - Material: Dish (not in approved list)
   - Result: Dropdown shows no options, error message ✗
```

### Scenario 3: View Used Materials Count
```
1. Admin views MaterialRequest list
2. Sees column: "Used Materials Count"
3. Sees count: "2" for approved requests
4. Sees display: "2x Cable, 1x Installation Kit"
5. Clicks request to see detail view with all linked used materials
```

## Performance Considerations

### Optimizations Applied
```python
# In views:
used_materials = UsedMaterial.objects.filter(
    technician=request.user
).select_related('material', 'material_request')  # Joins to avoid N+1

# In forms:
approved_requests.select_related('material')  # Optimize dropdown
```

### Database Indexes
```python
# Already exist on UsedMaterial:
- technician + added_at
- material + added_at
- status

# Implicitly created on new ForeignKey:
- material_request (database creates automatically)
```

## Troubleshooting

### Issue: Technician sees no materials in dropdown
- Check: User has approved MaterialRequest objects
- Check: MaterialRequest.status = 'Approved'
- Check: User's role is 'Technician'

### Issue: material_request field not appearing
- Run: `python manage.py migrate`
- Check: Newest migration applied

### Issue: Used materials count showing wrong number
- Check: UsedMaterial.material_request is set correctly
- Check: Database migration applied
- Restart: Django development server

## Future Enhancements

1. Add ability to view used materials by request in frontend template
2. Add reporting: "% of requested materials actually used"
3. Add bulk approve functionality
4. Add notifications when used materials exceed request quantity
5. Add historical tracking of usage patterns
