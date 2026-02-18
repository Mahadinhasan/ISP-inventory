# ⚡ Quick Start Guide - Request Materials Flow

## For Branch Users

### Create a Regular Request
```
1. Go to Requests page
2. Click [Request Material] (Blue Button)
3. Modal shows: "Regular Request"
4. Select Material
5. Enter Quantity
6. Add Notes (optional)
7. Click Submit
✓ Request created with Type="Regular"
```

### Create an Advance Request
```
1. Go to Requests page
2. Click [Advance Materials] (Indigo Button)
3. Modal shows: "Advance Request"
4. Select Material
5. Enter Quantity
6. Add Notes (optional)
7. Click Submit
✓ Request created with Type="Advance"
```

### View Your Requests
```
- Go to Requests page
- See all your requests
- Type column shows:
  🔵 Regular (Blue)
  🔷 Advance (Indigo)
- Status shows: Pending/Approved/Rejected
```

---

## For Admin Users

### View All Requests
```
1. Go to Requests page
2. See all requests from all branch users
3. Tables are organized:
   - Regular Requests section
   - Advance Requests section
4. Filter by user (dropdown)
5. Type column clearly shows type
```

### Quick Identification
```
Blue Badge 🔵 = Regular Request
Indigo Badge 🔷 = Advance Request

Visual scanning is instant!
```

### Manage Requests
```
1. Click [Manage] on any request
2. Modal opens for Admin actions
3. Approve/Reject/Save Note
4. Type is preserved through workflow
```

---

## Buttons & Colors

### Request Page Buttons
```
┌─────────────────────────────┐
│ Requests                    │
├─────────────────────────────┤
│ [Request Material] ← Blue      │ 
│ [Advance Materials] ← Indigo   │
└─────────────────────────────┘
```

### Type Badges in Table
```
┌──────────┬─────┬──────────────────┐
│ Material │ Qty │ Type             │
├──────────┼─────┼──────────────────┤
│ Cable    │ 10  │ Regular 🔵       │
│ Router   │ 2   │ Advance 🔷       │
│ Switch   │ 5   │ Regular 🔵       │
└──────────┴─────┴──────────────────┘
```

---

## Form Fields

When creating a request, you provide:

```
✓ Material - Choose from dropdown
✓ Quantity - Enter number
✓ Type - Auto-set by button (Regular or Advance)
✓ User Note - Optional text
```

---

## Status Values

After submission:
- **Pending** - Waiting for admin approval
- **Approved** - Admin approved the request
- **Rejected** - Admin rejected the request

---

## Key Differences

### Regular Request
- Standard material request
- Normal processing
- Blue indicator
- `request_type = "Regular"`

### Advance Request
- Priority/advance booking
- Special handling
- Indigo indicator
- `request_type = "Advance"`

---

## FAQs

**Q: How do I know if a request is Regular or Advance?**  
A: Check the Type column - Blue = Regular, Indigo = Advance

**Q: Can I change the type after creating?**  
A: No, type is set when you create the request

**Q: Where do I click to create a request?**  
A: Requests page, click [Request Material] or [Advance Materials]

**Q: What fields are required?**  
A: Material and Quantity are required, User Note is optional

**Q: What happens after I submit?**  
A: Request shows in Requests page with Type=Pending status

---

## Common Tasks

### Create Regular Request
```
Requests → [Request Material] → Fill Form → Submit
```

### Create Advance Request
```
Requests → [Advance Materials] → Fill Form → Submit
```

### Check Request Status
```
Requests → View Table → See Type & Status
```

### Filter by User
```
Requests → Select User (Dropdown) → See their requests
```

### Approve Request (Admin)
```
Requests → [Manage] → [Approve] → Save
```

### Reject Request (Admin)
```
Requests → [Manage] → [Reject] → Save
```

---

## Visual Quick Reference

### Page Layout
```
┌────────────────────────────────────┐
│ Material Requests                  │
├────────────────────────────────────┤
│ [Search] [Regular] [Advance]       │ ← Buttons
│          [Filter by User ▼]        │ ← Dropdown
├────────────────────────────────────┤
│ Pending: 5  Approved: 12  Rej: 2   │ ← Stats
├────────────────────────────────────┤
│ ID │ Material │ Qty │ Type │ ...   │ ← Table
│    │          │     │ 🔵🔷 │       │
└────────────────────────────────────┘
```

### Modal Layout
```
┌──────────────────────────────────┐
│ Request Material                 │
│ (with type indicator)            │
├──────────────────────────────────┤
│ ℹ️ Regular Request               │
│                                  │
│ Material: [Dropdown]             │
│ Quantity: [Number]               │
│ User Notes: [Text Area]          │
│                                  │
│     [Cancel]  [Submit]           │
└──────────────────────────────────┘
```

---

## Tips & Tricks

1. **Quick Scanning:** Use the Type column color badges for quick identification
2. **Filtering:** Use the user dropdown to filter by specific branch user
3. **Searching:** Use the search box to find specific materials
4. **Bulk Operations:** Filter first, then manage multiple requests

---

## Important Notes

- ✓ Type is set at creation time based on button clicked
- ✓ Type cannot be changed after submission
- ✓ Type persists through approval workflow
- ✓ Admin can see all user and type combinations
- ✓ Type column always visible for quick reference

---

## Support Reference

| Issue | Solution |
|-------|----------|
| Can't see buttons? | Make sure you're logged in as Branch user |
| Type not showing? | Refresh page (Ctrl+F5) |
| Can't select Advance? | Check if Request Modal opened correctly |
| Type showing wrong? | Verify you clicked correct button |

---

**Last Updated:** February 17, 2026  
**Status:** ✅ ACTIVE  

Questions? Check the documentation files or contact support.
