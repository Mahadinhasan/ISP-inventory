# Used Materials Approval System - Quick Start Guide

## What Was Implemented

A complete used materials tracking and approval system with these key features:

### 1. **Material Usage Recording** (For Technicians)
- Record when materials are used in the field
- Capture:
  - Material name and category (auto-populated)
  - Client name, address, and phone
  - Quantity used
  - Technical issue/notes
  - Link to original material request (optional)

### 2. **Admin Approval Dashboard** (For Admin/Storekeeper)
- Central location to review all used material records
- View pending, accepted, and rejected materials
- Filter by status or search by material/client/technician
- See all details in one comprehensive table

### 3. **Automatic Stock Deduction**
- When approved, materials are **automatically deducted** from inventory
- **Only Normal status materials** are deducted (not Low Stock or Out of Stock)
- Material status updates automatically (e.g., becomes Low Stock after deduction)
- Protected by database transactions to prevent errors

### 4. **Complete Audit Trail**
- Track who approved/rejected what
- Admin notes on each record
- Timestamps showing when actions were taken
- Access control ensures proper authorization

## How to Use

### For Technicians

**Step 1: Record Used Material**
1. Click "Record Materials" in navigation
2. Click "+ Add Used Material" button
3. Fill in the form:
   - **Material Name**: Select from approved materials (only those you've been approved for)
   - **Category**: Auto-fills from selected material
   - **Client Name**: Who received the service
   - **Client Address**: Where the work was done
   - **Phone**: Client contact number
   - **Quantity Used**: How many units
   - **Technical Issue/Notes**: What problem was fixed
   - **Material Request**: Link to original request (optional)
4. Submit
5. Your record will be marked as **Pending** until admin approves

### For Admin/Storekeeper

**Step 1: Review Pending Materials**
1. Click "Approve Materials" in navigation
2. You'll see a dashboard with:
   - Summary stats (Pending, Approved, Rejected counts)
   - Filter by status
   - Search by material name, client, or technician
3. Browse the comprehensive table showing:
   - Technician name
   - Material name & category
   - Client information (name, address, phone)
   - Quantity used
   - Date/time recorded
   - Current status

**Step 2: Approve or Reject Each Record**
1. Click "Review" button on a Pending record
2. You'll see a detailed page with all information:
   - Material status (Normal/Low Stock/Out of Stock)
   - Current available quantity
   - Full client details
   - Technical notes
3. Choose action:
   - **Approve & Deduct Stock**: 
     - If material is Normal: Deducts from inventory
     - If material is Low/Out: Shows warning but still approves (no deduction)
   - **Reject**: Denies the usage with optional notes
4. Add admin notes if needed (optional)
5. Click button to submit

**Step 3: View History**
- Approved/rejected records remain in the system with full audit trail
- You can still view them by filtering on "Approve Materials" page
- Click "View" to see details and approval notes

## Column Reference

When viewing used materials, these columns appear:

| Column | Description | Updated By |
|--------|-------------|-----------|
| **Material Name** | What was used | Technician |
| **Category** | Internet/Dish | Auto from Material |
| **Client Name** | Who received service | Technician |
| **Client Address** | Location of work | Technician |
| **Phone** | Client contact | Technician |
| **Quantity** | How much used | Technician |
| **Date/Time** | When recorded | System |
| **Status** | Pending/Accepted/Rejected | Admin (on approval) |
| **Action** | Review/Approve | Admin |

## Key Features Explained

### 1. Material Category
✅ **Automatic** - Populates whenever you select a material
- No manual entry needed
- Ensures consistency
- Shows as colored badge (Internet = Blue, Dish = Purple)

### 2. Stock Deduction Rules
✅ **Smart Deduction** - Only happens when:
- Status is "Approved"
- Material status is "Normal"
- Sufficient quantity available

⚠️ **No Deduction** - But still approved when:
- Material is "Low Stock"
- Material is "Out of Stock"
- Shows warning message to admin

### 3. Only Normal Materials Count
✅ As requested, the system:
- Only deducts from materials with "Normal" status
- Allows recording of Low Stock/Out of Stock materials
- But warns admin if attempting to approve them
- Never deducts from Low Stock or Out of Stock

### 4. Client Information Tracking
✅ Complete client data captured:
- Name, address, and phone number
- Used for service tracking and follow-up
- Searchable for finding records

## New Navigation Links

### For Technicians
**"Record Materials"** - Access used material recording form

### For Admin/Storekeeper  
**"Approve Materials"** - Access approval dashboard and review pending records

## Example Workflow

### Scenario: Technician deploys Internet materials to a client

1. **Technician's Action**:
   - Goes to "Record Materials"
   - Adds new record:
     - Material: "Cat5 Cable (approved)"
     - Quantity: 50 units
     - Client: "ABC Corp"
     - Address: "123 Business St"
     - Phone: "555-1234"
     - Issue: "Upgraded internet from 10Mbps to 100Mbps"

2. **Admin's Action**:
   - Sees pending record on "Approve Materials"
   - Clicks "Review"
   - Sees material has Normal status with 200 units available
   - Approves
   - System deducts 50 units → Material now has 150 units

3. **Result**:
   - Record marked as "Accepted"
   - Actual inventory reduced by 50
   - Full audit trail saved
   - Material status may auto-update if stock is now low

## What's New in This System

### Before Implementation
- No tracking of material usage
- Manual adjustment of counts
- No approval workflow
- No client information with material usage
- No material name/category display with usage

### After Implementation
✅ Track exact material usage with client details
✅ Automated approval workflow
✅ Automatic stock deduction when approved
✅ Only deduct from Normal status materials
✅ Full audit trail
✅ Material category always visible
✅ Smart status management

## Tips & Best Practices

1. **For Technicians**:
   - Always link to material request if available
   - Fill in all client information
   - Be specific in technical notes for audit purposes

2. **For Admin**:
   - Review pending materials regularly
   - Add notes for unusual approvals/rejections
   - Monitor materials with multiple usages for reordering needs
   - Use search/filter to find specific records quickly

3. **System-Wide**:
   - Regular approvals ensure accurate inventory
   - Low Stock status materials need attention
   - Use the approval dashboard to spot high-usage materials

## Troubleshooting

**Q: Why can't I see a material in the dropdown?**
A: You need it to be approved first. Ask admin to approve a material request for it.

**Q: Why didn't stock deduct when I approved?**
A: Likely the material status is Low Stock or Out of Stock. This is intentional - the system warns you.

**Q: Where do I find old records?**
A: Go to "Approve Materials" and filter by "Accepted" or "Rejected" status.

**Q: Can I change my mind after approving?**
A: The current system doesn't allow reversal. You could reject and re-request if needed.

**Q: Why is this material marked Low Stock?**
A: The quantity fell below the minimum stock level (usually 10) after an approval.

## Questions?

Refer to the detailed technical documentation in `USED_MATERIALS_IMPLEMENTATION.md` for in-depth system architecture and troubleshooting.
