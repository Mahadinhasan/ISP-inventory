# Branch Role Report Features - Implementation Complete

## Overview
Enhanced report functionality for **Branch role users** with auto-generated reports containing only relevant data (Material Requests and Used Materials).

## Features Implemented

### 1. **Auto-Generated Reports for Branch Users**
- Reports automatically filter data based on logged-in Branch user
- No need to select user manually
- Date range filtering available (preset: today, week, month, last30, last90 days)

### 2. **Excel Export (`/reports/export/excel/`)** 
When Branch user clicks export to Excel, the system generates a file with **6 separate sheets**:

#### Material Requests Sheets:
1. **Requests - Pending**: All pending requests for the user (Date, Material, Category, Qty, Type, Notes, Status)
2. **Requests - Approved**: All approved requests (Date, Material, Category, Qty, Type, Notes, Status)
3. **Requests - Rejected**: All rejected requests (Date, Material, Category, Qty, Type, Notes, Status)

#### Used Materials Sheets:
4. **Used Materials - Pending**: All pending used material records (Date, Material, Category, Qty Used, Issue)
5. **Used Materials - Accepted**: All accepted used material records (Date, Material, Category, Qty Used, Issue)
6. **Used Materials - Rejected**: All rejected used material records (Date, Material, Category, Qty Used, Issue)

#### Additional Sheet:
7. **Summary**: Overview statistics including:
   - Material Requests count (Pending, Approved, Rejected)
   - Used Materials count (Pending, Accepted, Rejected)
   - Total quantities for approved/accepted items

### 3. **PDF Export (`/reports/export/pdf/`)**
When Branch user clicks export to PDF, the system generates:

- **First Page**: Summary statistics with visual stat boxes
  - Total Requests & breakdown by status (with color coding)
  - Total Units Approved
  - Material Requests by status (Pending, Approved, Rejected)
  
- **Pending Requests Table**: Shows all pending requests
- **Approved Requests Table**: Shows all approved requests  
- **Rejected Requests Table**: Shows all rejected requests
- **Page Break**: Separates request and used materials sections
- **Used Materials Summary**: Statistics on used materials
- **Pending Used Materials Table**: Shows pending items
- **Accepted Used Materials Table**: Shows accepted items
- **Rejected Used Materials Table**: Shows rejected items

## Backend Files Modified

### 1. **views.py** - Added/Modified Functions:

#### New Helper Functions:
- `_generate_branch_excel_report()` - Generates Excel with 6+ sheets for Branch users
- `_generate_branch_pdf_report()` - Generates PDF report for Branch users

#### Modified Functions:
- `reports_export_excel()` - Now routes Branch users to specialized Excel generator
- `reports_export_pdf()` - Now routes Branch users to specialized PDF generator

### 2. **Templates** - Created:
- `branch_report_pdf.html` - Beautiful PDF template with all sections formatted for Branch reports

## Usage

### For Branch Users:

1. **Access Reports**: Navigate to Reports section from dashboard
2. **Select Date Range**: Use presets or custom dates
3. **Download Options**:
   - **Excel**: Click "Export to Excel" - Downloads `branch_report_YYYY-MM-DD_to_YYYY-MM-DD.xlsx`
   - **PDF**: Click "Export to PDF" - Downloads `branch_report_YYYY-MM-DD_to_YYYY-MM-DD.pdf`

### Data Included:

**Only shows data for the logged-in Branch user**:
- Their own Material Requests (all statuses)
- Their own Used Materials (all statuses)

**Does NOT include**:
- Other branches' data
- Material stock information
- User breakdowns
- System-wide statistics

## Styling & Formatting

### Excel Features:
- ✅ Separate sheets for each status
- ✅ Color-coded headers (blue background, white text)
- ✅ Alternating row colors for readability
- ✅ Frozen header rows
- ✅ Color-coded status cells (Green=Approved/Accepted, Yellow=Pending, Red=Rejected)
- ✅ Proper column widths
- ✅ Professional formatting

### PDF Features:
- ✅ Summary statistics with visual stat boxes
- ✅ Color-coded status badges
- ✅ Professional header section
- ✅ Multiple pages with page breaks
- ✅ Table formatting optimized for xhtml2pdf
- ✅ Footer with page numbers
- ✅ Print-friendly styling

## Database Queries Optimized

- Uses `.select_related()` for foreign key optimization
- Filters by date range and user
- Aggregates used `Sum()` for totals
- Groups by status for separate sheets

## URL Endpoints

These endpoints already exist and now have Branch-specific logic:

```
GET  /reports/                  # View main report page
GET  /reports/export/excel/     # Download Excel for Branch user
GET  /reports/export/pdf/       # Download PDF for Branch user
```

## Testing Checklist

- [ ] Login as Branch user
- [ ] Navigate to Reports section
- [ ] Select date range
- [ ] Click "Export to Excel" → Check all 6 sheets exist
- [ ] Click "Export to PDF" → Check PDF opens correctly
- [ ] Verify only current user's data is included
- [ ] Verify sheet names match (Pending, Approved, Rejected, etc.)
- [ ] Verify status counts are accurate
- [ ] Verify color coding is correct
- [ ] Verify no other branch data appears

## Notes

- Admin and Storekeeper roles continue to use the original comprehensive reporting system
- NoC role redirects to NoC dashboard (no report access)
- Only Branch role gets the specialized simplified report
- All timestamps are in local timezone
- Field mappings:
  - MaterialRequest.notes → Shows in requests
  - UsedMaterial.issue → Shows in used materials table (contains technical issue/notes)
  - UsedMaterial.admin_note → Available but not shown in reports

## Future Enhancements

Possible additions:
- Email report delivery
- Scheduled automated reports
- Custom email templates
- Report caching for faster downloads
- Filter by material type in reports
- Monthly comparison reports
