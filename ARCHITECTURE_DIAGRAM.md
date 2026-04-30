# System Architecture Diagram

## Data Model Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER AUTHENTICATION                       │
│                                                                   │
│  ┌────────────┐      ┌──────────────┐      ┌──────────────┐     │
│  │   Django   │      │  UserProfile │      │   Groups     │     │
│  │    User    │◄────►│              │◄────►│              │     │
│  │            │      │role: Admin/  │      │Branch        │     │
│  └────────────┘      │Storekeeper/  │      │Storekeeper   │     │
│         ▲            │ Branch/NOC   │      │Admin         │     │
│         │            └──────────────┘      └──────────────┘     │
│         │                                                       │
└─────────┼──────────────────────────────────────────────────────┘
          │
          │
    ┌─────┴────────┬──────────────┬─────────────┐
    │              │              │             │
    ▼              ▼              ▼             ▼
┌────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐
│  Material  │ │ Task       │ │Vendor    │ │NotificationS│
│            │ │            │ │          │ │Setting      │
│ -name      │ │ -title     │ │ -name    │ │             │
│ -category  │ │ -customer  │ │ -contact │ │ -user       │
│ -quantity  │ │ -technician│ │ -phone   │ │ -preferences│
│ -status    │ │ -status    │ │ -address │ │             │
└────┬───────┘ └────────────┘ └──────────┘ └──────────────┘
     │
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│                    MATERIAL REQUEST WORKFLOW                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  MATERIALREQUEST                         │  │
│  │                                                          │  │
│  │  - material ──► Material  (FK)                          │  │
│  │  - requester ──► User (FK)                              │  │
│  │  - quantity: INTEGER                                    │  │
│  │  - status: Pending|Approved|Rejected                    │  │
│  │  - user_note: TEXT                                      │  │
│  │  - admin_note: TEXT                                     │  │
│  │  - requested_at: DATETIME                               │  │
│  │                                                          │  │
│  │  PROPERTIES (NEW):                                      │  │
│  │  ✓ used_materials_count  → Returns: INT                │  │
│  │  ✓ used_materials_display → Returns: STRING            │  │
│  │                                                          │  │
│  │  RELATIONS (NEW):                                       │  │
│  │  ◄─── used_materials (Reverse FK)                       │  │
│  │        └─ Links to all UsedMaterial(s) for this request │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ▲                                     │
│                            │                                     │
│                   Step 1: Create Request                         │
│                   Step 2: Approve/Reject                         │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   USEDMATERIAL (NEW)                     │  │
│  │                                                          │  │
│  │  FOREIGN KEYS:                                          │  │
│  │  - technician ──► User                                  │  │
│  │  - material ──► Material                                │  │
│  │  - material_request ──► MaterialRequest ◄─── NEW         │  │
│  │                                                          │  │
│  │  FIELDS:                                                │  │
│  │  - quantity: INTEGER                                    │  │
│  │  - client_name: VARCHAR                                 │  │
│  │  - client_address: TEXT                                 │  │
│  │  - client_phone: VARCHAR                                │  │
│  │  - issue: TEXT                                          │  │
│  │  - status: Pending|Accepted|Rejected                    │  │
│  │  - admin_note: TEXT                                     │  │
│  │  - added_at: DATETIME                                   │  │
│  │  - updated_at: DATETIME                                 │  │
│  │                                                          │  │
│  │  Step 3: Link Used Material to Request (Optional)       │  │
│  │  Step 4: Provide tracking & audit trail                 │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

## Request Workflow Diagram

```
                        ┌─────────────────┐
                        │  TECHNICIAN     │
                        │  Creates Request│
                        │  Status: Pending│
                        └────────┬────────┘
                                 │
                                 │ MaterialRequest(
                                 │   material=Cable,
                                 │   requester=John,
                                 │   quantity=5,
                                 │   status='Pending'
                                 │ )
                                 │
                                 ▼
                        ┌─────────────────┐
                        │     ADMIN       │
                        │   Reviews Req   │
                        │   status pending│
                        └─────┬───────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌─────────────┐     ┌──────────────┐
            │   APPROVE   │     │   REJECT     │
            │status=      │     │  status=     │
            │'Approved'   │     │  'Rejected'  │
            └──────┬──────┘     └──────────────┘
                   │
                   │ Now Technician can use
                   │ these materials
                   │
                   ▼
            ┌──────────────────────────────────┐
            │   TECHNICIAN                     │
            │   Creates UsedMaterial           │
            │                                  │
            │   Form shows:                    │
            │   - Material: Cable (approved)   │
            │   - Material Request: Select ▼   │
            │     (Dropdown with Request #1)   │
            │   - Client: John Doe             │
            │   - Address: 123 Main St         │
            │   - Quantity: 2                  │
            │   - Issue: Installation          │
            │                                  │
            │   Creates:                       │
            │   UsedMaterial(                  │
            │     technician=John,             │
            │     material=Cable,              │
            │     material_request=Req1,  ◄─── NEW LINK
            │     quantity=2,                  │
            │     status='Pending'             │
            │   )                              │
            └──────┬───────────────────────────┘
                   │
                   │
                   ▼
            ┌──────────────────────────────────┐
            │   ADMIN DASHBOARD                │
            │   (MaterialRequest List View)     │
            │                                  │
            │ ID│Req│Qty│Status│Count│Display  │
            │───┼───┼───┼──────┼─────┼────────│
            │ 1 │John│ 5 │Appr  │ 2   │2x Cable│
            │   │   │   │      │     │1x Kit  │
            │                                  │
            │ Can see:                         │
            │ ✓ used_materials_count: 2        │
            │ ✓ used_materials_display:        │
            │   "2x Cable, 1x Kit"        ◄─── NEW
            │                                  │
            └──────────────────────────────────┘
```

## Role-Based Access Control (RBAC)

```
┌─────────────────────────────────────────────────────────┐
│              ROLE-BASED FEATURE ACCESS                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  TECHNICIAN ROLE:                                       │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ✓ Create MaterialRequest                           │ │
│  │ ✓ Create UsedMaterial                              │ │
│  │ ✓ Link UsedMaterial to OWN approved request        │ │
│  │ ✓ View: OWN requests & used materials              │ │
│  │ ✗ Cannot view other technicians' records           │ │
│  │ ✗ Cannot approve/reject requests                   │ │
│  │ ✗ Cannot change request status                     │ │
│  │                                                     │ │
│  │ Material Dropdown Filter:                          │ │
│  │ ├─ Shows ONLY materials from OWN approved requests │ │
│  │ └─ Prevents using unapproved materials             │ │
│  │                                                     │ │
│  │ Request Dropdown Filter:                           │ │
│  │ ├─ Shows ONLY OWN approved MaterialRequests        │ │
│  │ └─ Prevents linking to other users' requests       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ADMIN ROLE:                                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ✓ View ALL MaterialRequests                         │ │
│  │ ✓ Approve/Reject requests                          │ │
│  │ ✓ View ALL UsedMaterial records                    │ │
│  │ ✓ See used_materials_count in list view            │ │
│  │ ✓ See used_materials_display in list view          │ │
│  │ ✓ Audit request → used material linking            │ │
│  │ ✗ Cannot create UsedMaterial records               │ │
│  │                                                     │ │
│  │ In Django Admin:                                   │ │
│  │ ├─ View: All requests with usage count             │ │
│  │ ├─ Filter: By status, date, category               │ │
│  │ ├─ Search: By requester, material name             │ │
│  │ └─ Readonly: Count and display properties          │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  STOREKEEPER ROLE:                                      │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ✗ Cannot create UsedMaterial                       │ │
│  │ ✗ Cannot link MaterialRequest                      │ │
│  │ ✗ Cannot view request linking information          │ │
│  │                                                     │ │
│  │ Can only:                                          │ │
│  │ ├─ Manage Material inventory                       │ │
│  │ └─ View material stock levels                      │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

```
┌──────────────────────────┐
│      auth_user           │
├──────────────────────────┤
│ id (PK)                  │
│ username                 │
│ password                 │
│ first_name               │
│ last_name                │
│ email                    │
└────────────┬─────────────┘
             │
    ┌────────┴────────┬──────────┬──────────┐
    │                 │          │          │
    ▼                 ▼          ▼          ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ UserProfile  │  │MaterialRequest│  │UsedMaterial  │  │  Material    │
├──────────────┤  ├──────────────────┤├──────────────┤  ├──────────────┤
│ id (PK)      │  │ id (PK)          ││ id (PK)      │  │ id (PK)      │
│ user_id (FK) ├─→│ requester_id(FK) ││ technician_id├─→│ name         │
│              │  │                  ││(FK)          │  │ category     │
│ role         │  │ material_id (FK)├─→ material_id │  │ quantity     │
│              │  │                  ││(FK)          │  │ status       │
└──────────────┘  │ quantity         ││              │  │              │
                  │ status           ││ material_request
                  │ requested_at     ││_id (FK, NULL) ◄─ NEW FIELD
                  │ user_note        ││              │  │
                  │ admin_note       ││ quantity     │  │
                  │                  ││ client_name  │  │
                  │ PROPERTIES (NEW):││ client_addr  │  │
                  │ - used_materials ││ client_phone │  │
                  │   _count         ││              │  │
                  │ - used_materials ││ issue        │  │
                  │   _display       ││ status       │  │
                  │                  ││ added_at     │  │
                  └──────────────────┘└──────────────┘  └──────────────┘
```

## Admin Interface Display

```
┌─────────────────────────────────────────────────────────────────────┐
│  Django Admin - Material Requests                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [All] [By Status ▼] [By Category ▼]  🔍 Search: __________         │
│                                                                      │
│  ┌────┬──────────┬─────────────┬─────┬──────────┬────────┬─────────┤
│  │ ID │ Requester│ Material    │ Qty │ Status   │ Used ▼ │ Display │
│  │    │          │             │     │          │ Count  │         │
│  ├────┼──────────┼─────────────┼─────┼──────────┼────────┼─────────┤
│  │ 1  │ John     │ Internet ... │ 5   │ Approved │ 2 ◄─── │ 2x Cable│
│  │    │          │             │     │          │ NEW    │ 1x Kit  │
│  │    │          │             │     │          │        │ ◄ NEW   │
│  ├────┼──────────┼─────────────┼─────┼──────────┼────────┼─────────┤
│  │ 2  │ Jane     │ Dish        │ 3   │ Pending  │ 0      │ -       │
│  ├────┼──────────┼─────────────┼─────┼──────────┼────────┼─────────┤
│  │ 3  │ Bob      │ Cable       │ 10  │ Approved │ 5      │ 3x Cable│
│  │    │          │             │     │          │        │ 2x Kit  │
│  └────┴──────────┴─────────────┴─────┴──────────┴────────┴─────────┘
│                                                                      │
│  Click on request #1 to view detail with all linked UsedMaterials  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Material Request: Cable (ID: 1)                            │  │
│  │                                                              │  │
│  │  Request Info                                               │  │
│  │  ├─ Requester: John                                         │  │
│  │  ├─ Material: Internet Cable                                │  │
│  │  ├─ Quantity: 5                                             │  │
│  │  ├─ Status: Approved                                        │  │
│  │  └─ Requested: 2024-01-15                                   │  │
│  │                                                              │  │
│  │  Used Materials (NEW SECTION)                               │  │
│  │  ├─ Count: 2                      ◄─ used_materials_count  │  │
│  │  └─ Display: "2x Cable, 1x Kit"   ◄─ used_materials_display
│  │                                                              │  │
│  │  All Linked UsedMaterial Records:                           │  │
│  │  ├─ [1] 2x Cable - John - 2024-01-16 - Installation        │  │
│  │  └─ [2] 1x Kit - John - 2024-01-17 - Replacement           │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Code Flow Diagram

```
USER INTERACTION:
┌──────────────────────────────────────────────────────────────────┐
│ Technician fills UsedMaterialForm                                │
│                                                                  │
│ Form Fields:                                                    │
│ ├─ Material: [Select ▼] ◄─ Filtered by UsedMaterialForm       │
│ ├─ Material Request: [Select ▼] ◄─ NEW - Also filtered        │
│ ├─ Client Name: [___________]                                  │
│ ├─ Client Address: [___________]                               │
│ ├─ Phone: [___________]                                        │
│ ├─ Quantity: [_____]                                           │
│ ├─ Issue: [___________]                                        │
│ └─ Status: [Select ▼]                                          │
│                                                                  │
│ Submit                                                          │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
         [FORM PROCESSING]
         
         Form.__init__(user=technician)
         │
         ├─ For Technician:
         │  ├─ Filter material to approved materials only
         │  │  └─ approved_material_ids = MaterialRequest.objects.filter(
         │  │      requester=technician,
         │  │      status='Approved'
         │  │    ).values_list('material', flat=True)
         │  │
         │  └─ Filter material_request to approved requests only
         │     └─ approved_requests = MaterialRequest.objects.filter(
         │        requester=technician,
         │        status='Approved'
         │      )
         │
         └─ For Others:
            └─ Show all approved materials and requests
         
                 │
                 ▼
         [VIEW PROCESSING]
         
         used_materials_view(request)
         │
         ├─ Check role: Must be Technician ✓
         │
         ├─ Validate material in approved list ✓
         │
         ├─ Validate material_request:
         │  └─ Check ownership: request.requester == current_user ✓
         │
         ├─ Create UsedMaterial:
         │  └─ UsedMaterial.objects.create(
         │       technician=user,
         │       material=material,
         │       material_request=request,  ◄─ SET LINK
         │       quantity=qty,
         │       ...
         │     )
         │
         └─ Success: Redirect to used_materials
         
                 │
                 ▼
         [DATABASE STORAGE]
         
         INSERT INTO isp_inventory_usedmaterial
         (technician_id, material_id, material_request_id, ...)
         VALUES (123, 45, 67, ...)
         
                 │
                 ▼
         [ADMIN VIEW]
         
         Admin views MaterialRequest list
         │
         ├─ Column: used_materials_count
         │  └─ Calls: request.used_materials.count()
         │     Result: 2
         │
         └─ Column: used_materials_display
            └─ Calls: request.used_materials.all()
               Result: "2x Cable, 1x Kit"
```

## File Modification Summary

```
BEFORE                          AFTER
─────────────────────────────────────────────────────────
models.py                       models.py
├─ Material                     ├─ Material
├─ MaterialRequest              ├─ MaterialRequest ◄─ ENHANCED
│  ├─ material (FK)             │  ├─ material (FK, related_name)
│  ├─ requester (FK)            │  ├─ requester (FK, related_name)
│  └─ status                    │  ├─ status
│                               │  ├─ + used_materials_count property
│                               │  └─ + used_materials_display property
│                               │
├─ UsedMaterial                 ├─ UsedMaterial ◄─ ENHANCED
│  ├─ technician (FK)           │  ├─ technician (FK)
│  ├─ material (FK)             │  ├─ material (FK)
│  └─ status                    │  ├─ + material_request (FK) ◄─ NEW
│                               │  └─ status
                                
forms.py                        forms.py
├─ UsedMaterialForm             ├─ UsedMaterialForm ◄─ ENHANCED
│  ├─ fields = [...]            │  ├─ fields = [..., + material_request]
│  ├─ Material dropdown          │  ├─ Material dropdown (filtered)
│  └─ __init__ filtering         │  ├─ Material Request dropdown ◄─ NEW (filtered)
                                │  └─ __init__ enhanced filtering
                                
admin.py                        admin.py
├─ admin.site.register(...)     ├─ MaterialRequestAdmin ◄─ NEW CLASS
│                               │  ├─ list_display = [... + used_materials_count, used_materials_display]
                                │  ├─ list_filter
                                │  ├─ search_fields
                                │  └─ fieldsets
                                │
                                ├─ UsedMaterialAdmin ◄─ NEW CLASS
                                │  ├─ list_display = [... + material_request]
                                │  ├─ list_filter
                                │  ├─ search_fields
                                │  └─ fieldsets
                                │
                                └─ admin.site.register(..., CustomAdmin)
                                
views.py                        views.py
├─ used_materials_view()        ├─ used_materials_view() ◄─ ENHANCED
│  └─ select_related('material')│  ├─ select_related('material', 'material_request')
                                │  ├─ Form handling for material_request ✓
                                │  ├─ Validation for material_request ownership ✓
                                │  └─ Setting material_request on save ✓
                                
migrations/                     migrations/
└─ (none)                       └─ 0017_usedmaterial_material_request_and_more.py ◄─ NEW
```

---

This implementation provides a complete, secure, and auditable material usage tracking system with proper role-based access control and approval workflows.
