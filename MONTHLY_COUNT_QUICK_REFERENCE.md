# Monthly Count Implementation - Quick Reference

## ✨ Key Features

### 1. In Stock Indicator
Materials now show "(in stock)" when quantity > 0:
```
Copper Cable (in stock)
Fiber Pigtail
```

### 2. Monthly Tracking
Each material has a monthly count that automatically resets at month end.

### 3. Easy API

```python
from isp_inventory.models import Material
from isp_inventory.utils import increment_material_count, reset_material_monthly_count

# Get a material
material = Material.objects.get(name="Copper Cable")

# Increment monthly count
material.increment_monthly_count(5)

# Or use utility function
increment_material_count(material, quantity=3)

# Get monthly count
count_record = material.get_monthly_count()
print(count_record.count)  # Current month count

# Reset at month end
material.reset_monthly_count()

# Or use utility
reset_material_monthly_count(material)

# Get previous month's count
prev_count = material.get_previous_month_count()
```

---

## 🗄️ Database Model

### MaterialMonthlyCount
- `material` → ForeignKey to Material
- `month` → First day of month (DateField)
- `count` → Monthly count (default: 0)
- `created_at` → Auto timestamp
- `updated_at` → Auto update timestamp

**Unique Constraint**: material + month (one per month)

---

## 🛠️ Management Commands

### Reset Current Month
```bash
python manage.py reset_monthly_counts
```

### Reset Specific Month
```bash
python manage.py reset_monthly_counts --month 2026-02
```

---

## 📊 Utility Functions

| Function | Purpose |
|----------|---------|
| `get_current_month_date()` | Get first day of current month |
| `get_material_monthly_count(material)` | Get/create monthly record |
| `increment_material_count(material, qty)` | Add to monthly count |
| `reset_material_monthly_count(material)` | Reset to 0 |
| `get_monthly_count_summary()` | Get all counts (current month) |
| `reset_all_monthly_counts()` | Reset all materials |

---

## 💡 Use Cases

### Case 1: Track Material Usage Per Month
```python
# When technician uses material
technician = User.objects.get(username='john')
material = Material.objects.get(name="Fiber Cable")

# Increment what was used
material.increment_monthly_count(2)
```

### Case 2: Generate Monthly Report
```python
from isp_inventory.utils import get_monthly_count_summary

report = get_monthly_count_summary()
for record in report:
    print(f"{record.material.name}: {record.count} units")
```

### Case 3: Monitor Previous Month Performance
```python
material = Material.objects.get(name="Copper Cable")

current = material.get_monthly_count().count
previous = material.get_previous_month_count()

print(f"Current month: {current}, Previous: {previous}")
```

### Case 4: Automated Month-End Reset
Schedule in crontab:
```bash
# Reset at 12:01 AM on 1st of every month
1 0 1 * * cd /project && python manage.py reset_monthly_counts
```

---

## 🔧 Admin Integration

Add to `admin.py`:
```python
from django.contrib import admin
from isp_inventory.models import MaterialMonthlyCount

@admin.register(MaterialMonthlyCount)
class MaterialMonthlyCountAdmin(admin.ModelAdmin):
    list_display = ['material', 'month_display', 'count']
    list_filter = ['month', 'material__category']
    search_fields = ['material__name']
    readonly_fields = ['created_at', 'updated_at']
```

---

## 📈 Properties & Methods

### Material Model Additions

**Properties**:
- `is_in_stock` → Boolean, True if quantity > 0

**Methods**:
- `get_monthly_count()` → Returns MaterialMonthlyCount instance
- `increment_monthly_count(by=1)` → Adds to count
- `reset_monthly_count()` → Sets count to 0
- `get_previous_month_count()` → Gets last month's count

### MaterialMonthlyCount Model

**Properties**:
- `month_display` → Formatted string (e.g., "February 2026")
- `is_current_month` → Boolean

**Methods**:
- `reset()` → Resets count to 0

---

## ✅ What's Included

✓ New MaterialMonthlyCount model with database migration
✓ Updated Material model with monthly methods
✓ Management command for resets
✓ Utility functions module
✓ "(in stock)" indicator in Material display
✓ Database indexes for performance
✓ Unique constraints preventing duplicates

---

## 📋 Common Tasks

**Initialize current month for all materials**:
```python
from isp_inventory.models import Material, MaterialMonthlyCount
from datetime import datetime

for material in Material.objects.all():
    MaterialMonthlyCount.objects.get_or_create(
        material=material,
        month=datetime.now().replace(day=1),
        defaults={'count': 0}
    )
```

**Get stats for a material**:
```python
material = Material.objects.get(name="Item")
print(f"This month: {material.get_monthly_count().count}")
print(f"Last month: {material.get_previous_month_count()}")
print(f"In stock: {material.is_in_stock}")
print(f"Display: {material}")  # With (in stock) indicator
```

**Bulk reset for month**:
```python
from isp_inventory.utils import reset_all_monthly_counts
reset_all_monthly_counts()
```

---

## 🚀 Migration Applied

- Migration: `0031_remove_material_created_by_role_materialmonthlycount.py`
- Status: ✅ Applied successfully
- Changes:
  - New MaterialMonthlyCount table created
  - Material model updated with methods
  - Database indexes added

---

## 📞 Support Functions

All available via:
```python
from isp_inventory.utils import *
```

No additional dependencies beyond existing project requirements.
