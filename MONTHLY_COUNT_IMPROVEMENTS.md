# Material Models - Monthly Quantity Count Improvements

## Overview
Enhanced the material inventory models with monthly quantity tracking and automatic reset functionality. Materials now display "(in stock)" status when quantity > 0.

---

## Changes Made

### 1. **Updated Material Model** ([isp_inventory/models.py](isp_inventory/models.py))

#### Modified `__str__()` Method
```python
def __str__(self):
    """Display material name with stock status indicator."""
    stock_indicator = " (in stock)" if self.quantity > 0 else ""
    return f"{self.name}{stock_indicator}"
```
- Now displays "(in stock)" suffix when quantity > 0
- Example: "Copper Cable (in stock)" or "Fiber Pigtail" (if out)

#### New Properties
- `is_in_stock`: Boolean property to quickly check if quantity > 0

#### New Methods for Monthly Tracking
- `get_monthly_count()`: Get or create monthly count record for current month
- `increment_monthly_count(increment_by=1)`: Increase monthly count
- `reset_monthly_count()`: Reset monthly count to 0 at month end
- `get_previous_month_count()`: Retrieve last month's count for comparison

---

### 2. **New MaterialMonthlyCount Model**

A dedicated model to track monthly quantities with:
- **Unique Constraint**: One count per material per month
- **Auto-Reset**: Creates new month record with count=0 when a new month starts
- **Database Indexes**: For efficient queries on material and month
- **Methods**:
  - `reset()`: Reset count to 0
  - `month_display`: Formatted month string (e.g., "February 2026")
  - `is_current_month`: Check if record is for current month

**Schema**:
```
material (FK) → Material
month (Date) → First day of month
count (Int) → Monthly count (default: 0)
created_at (DateTime) → Auto-set
updated_at (DateTime) → Auto-updated
```

---

### 3. **New Management Command**

**File**: `isp_inventory/management/commands/reset_monthly_counts.py`

Handles automatic monthly resets:
```bash
# Reset current month
python manage.py reset_monthly_counts

# Reset specific month
python manage.py reset_monthly_counts --month 2026-02
```

Features:
- Processes all materials
- Creates new month records with count=0
- Resets existing counts if needed
- Colored output for success/error

---

### 4. **Enhanced Utility Functions**

**File**: `isp_inventory/utils.py`

New helper functions for easy access:

```python
# Get current month's first day
get_current_month_date()

# Get or create monthly count
get_material_monthly_count(material, month_date=None)

# Increment monthly count
increment_material_count(material, quantity=1, month_date=None)

# Reset monthly count at month end
reset_material_monthly_count(material, month_date=None)

# Get all counts for a month
get_monthly_count_summary(month_date=None)

# Reset all materials' counts
reset_all_monthly_counts(month_date=None)
```

---

## How to Use

### In Views/Forms
```python
from isp_inventory.utils import increment_material_count, get_monthly_count_summary

# When material is used
material = Material.objects.get(id=1)
increment_material_count(material, quantity=5)

# Get summary of current month
summary = get_monthly_count_summary()
for record in summary:
    print(f"{record.material.name}: {record.count}")
```

### In Admin Panel
```python
# Register and customize in admin.py
from django.contrib import admin
from isp_inventory.models import Material, MaterialMonthlyCount

@admin.register(MaterialMonthlyCount)
class MaterialMonthlyCountAdmin(admin.ModelAdmin):
    list_display = ['material', 'month_display', 'count', 'is_current_month']
    list_filter = ['month', 'material__category']
    search_fields = ['material__name']
    readonly_fields = ['created_at', 'updated_at']
```

### Scheduled Task (for automatic monthly reset)
Add to your `celery beat` schedule or use a cron job:
```bash
0 0 1 * * cd /path/to/project && python manage.py reset_monthly_counts
```

---

## Key Features

✅ **AutomaticMonth-End Reset**: Count becomes 0 when new month starts
✅ **In Stock Indicator**: "(in stock)" appears in string representation
✅ **Historical Tracking**: Previous month counts accessible
✅ **Efficient Queries**: Database indexes for fast lookups
✅ **Flexible Utility Functions**: Easy integration with existing code
✅ **Management Command**: Can be scheduled for automatic resets
✅ **Unique Constraint**: Prevents duplicate counts per material per month

---

## Database Migration

Migration file created: `0031_remove_material_created_by_role_materialmontlycount.py`

Changes:
- ✅ Removed `created_by_role` field from Material model
- ✅ Created new `MaterialMonthlyCount` table with foreign key to Material
- ✅ Added indexes for performance

**Apply migration**: 
```bash
python manage.py migrate isp_inventory
```

---

## Example: Workflow

```
January:
  - Item A: increment_monthly_count(material_a, 3) → count = 3
  - Item B: increment_monthly_count(material_b, 2) → count = 2

January 31 (Month End):
  - Run: reset_monthly_counts --month 2026-01
  - Item A: count = 0
  - Item B: count = 0

February 1 (New Month):
  - System auto-creates MaterialMonthlyCount for Feb
  - Item A: count = 0 (fresh start)
  - Item B: count = 0 (fresh start)
  - Can retrieve Jan counts via get_previous_month_count()
```

---

## Installation Notes

Required package installed:
- `python-dateutil` - For relativedelta calculations

**Already installed in project environment.**

---

## Next Steps (Optional Enhancements)

1. Add monthly analytics dashboard/views
2. Create reports for monthly consumption trends
3. Add alerts when threshold is reached in a month
4. Implement material allocation based on monthly history
5. Add export functionality for monthly counts
