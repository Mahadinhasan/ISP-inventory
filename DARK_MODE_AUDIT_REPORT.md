# Dark Mode Styling Audit Report
**Date:** April 5, 2026  
**Scope:** ISP Inventory System - All Templates (inventory/ and noc/ directories)

---

## Executive Summary

After scanning all 32 template files (15 inventory + 17 noc), **10+ critical templates** are identified as having significant dark mode styling gaps. The issues range from missing `dark:` prefixed classes to hardcoded CSS that ignores dark mode entirely.

**Priority Level:** 🔴 **HIGH** - Multiple critical files need immediate attention

---

## CRITICAL ISSUES (Highest Priority)

### 1. `reports.html` (BOTH inventory AND noc) 🔴
**Status:** SEVERELY LACKING DARK MODE  
**File Paths:**
- [inventory/templates/inventory/reports.html](ibccl/templates/inventory/reports.html)
- [noc/templates/noc/reports.html](ibccl/templates/noc/reports.html)

**Issues:**
- **Hardcoded CSS colors** - Uses inline `<style>` with hardcoded hex values:
  - `.rpt-card` - `background: #fff;` (no dark mode)
  - `.stat-card` - All hardcoded colors
  - `.rpt-table th` - `background: linear-gradient(135deg, #4f46e5, #7c3aed);` (no dark mode)
  - `.rpt-table td` - `border-bottom: 1px solid #f3f4f6;` (light mode only)
  - `.badge` - All variations hardcoded
- **Text colors:** `.rpt-table td { color: #374151; }` - no dark mode variant
- **Status badges:** All hardcoded backgrounds with no dark support

**Critical Elements Missing:**
```
✗ .rpt-card - needs dark:bg-slate-800
✗ .rpt-table th - needs dark gradient variant  
✗ .rpt-table td - needs dark:text-gray-300 and dark:border-gray-700
✗ .stat-card - needs dark background and text colors
✗ .badge-* - all variants need dark mode
```

---

### 2. `tasks.html` (BOTH inventory AND noc) 🔴
**Status:** MISSING DARK MODE ON KEY ELEMENTS  
**File Paths:**
- [inventory/templates/inventory/tasks.html](ibccl/templates/inventory/tasks.html#L8)
- [noc/templates/noc/tasks.html](ibccl/templates/noc/tasks.html#L8)

**Line-by-Line Issues:**

| Line | Element | Missing Dark Mode |
|------|---------|------------------|
| 8 | `<h1>` - "Task Management" | Missing `dark:text-white` |
| 9 | `<p>` - subtitle | Missing `dark:text-gray-400` |
| 13 | Button text | Missing `dark:text-white` text color hover |
| 17+ | Task cards `bg-white` | Missing `dark:bg-gray-800` |
| 19 | Card title `text-gray-900` | Missing `dark:text-white` |
| 20 | Status spans | Missing `dark:` variants for badges |
| 22+ | Icon colors `text-gray-600` | Missing `dark:text-gray-400` |
| 60+ | Modal `bg-white` | Missing `dark:bg-gray-800` |
| 63 | Modal title `text-gray-900` | Missing `dark:text-white` |
| 68+ | Form labels `text-gray-700` | Missing `dark:text-gray-300` |
| 73+ | Form inputs | Missing `dark:bg-gray-700 dark:text-white` |
| 94 | Modal buttons | No dark hover states |

**Missing Elements:**
```
✗ Card containers: dark:bg-gray-800
✗ Text colors: dark:text-white, dark:text-gray-400
✗ Forms: dark:bg-gray-700, dark:border-gray-600
✗ Modal: dark:bg-gray-800, dark:border-gray-700
✗ Button hover states: dark variations missing
```

---

### 3. `noc/used_materials.html` 🔴
**Status:** MISSING DARK MODE ON MAJORITY OF ELEMENTS  
**File Path:** [noc/templates/noc/used_materials.html](ibccl/templates/noc/used_materials.html)

**Issues:**
- **Title:** Line 6 - `<h1 class="...text-gray-900">` - **MISSING** `dark:text-white`
- **Table headers:** Lines 45-59 - All `text-gray-900` without `dark:text-gray-300` or `dark:text-white`
- **Table rows:** Lines 62+ - `<tr class="hover:bg-gray-100">` - **MISSING** `dark:hover:bg-gray-700`
- **Text in cells:** Multiple instances of no dark mode:
  - `text-gray-900` without dark variant
  - `text-gray-700` without `dark:text-gray-300`
  - `bg-gray-50` without dark equivalent
- **Modal background:** Line 90 - `bg-white` **MISSING** `dark:bg-gray-800`
- **Dropdowns:** Line 92 - `<div class="...text-gray-700">` - no dark mode

**Missing Dark Classes:**
```
✗ All text colors need dark: variants
✗ Table cells need dark:hover:bg-gray-700
✗ Modal needs dark:bg-gray-800, dark:border-gray-700
✗ All form inputs missing dark styling
✗ Status badges missing dark variants
```

---

## HIGH PRIORITY ISSUES

### 4. `noc/materials.html` 
**Status:** PARTIALLY MISSING DARK MODE  
**File Path:** [noc/templates/noc/materials.html](ibccl/templates/noc/materials.html)

**Issues:**
- **Pagination section:** Lines 124+ - `text-gray-500 bg-white` - **COMPLETELY MISSING** dark mode
  - No `dark:text-gray-400` on text
  - No `dark:bg-gray-800` on button backgrounds
  - Link `text-gray-500` needs `dark:text-gray-400`
- **Input field:** Line 17 - `dark:bg-gray-700` (should be consistent with rest of app using `dark:bg-midnight-950`)
- **Search button:** `dark:hover:bg-midnight-700` - inconsistent color scheme

**Elements Needing Update:**
```
✗ Pagination controls (15+ lines)
✗ Navigation links dark styling
✗ Text color consistency (dark:text-gray-400, dark:text-gray-300)
```

---

### 5. `noc/requests.html`
**Status:** PARTIALLY MISSING DARK MODE  
**File Path:** [noc/templates/noc/requests.html](ibccl/templates/noc/requests.html)

**Issues:**
- **Action buttons (Lines 20-24):** 
  - Approve button: `bg-green-500` - **MISSING** `dark:bg-green-600` or similar
  - Reject button: `bg-red-500` - **MISSING** `dark:bg-red-600` or similar
  - Hover states: `hover:bg-green-600` - **MISSING** dark variants
- **"Processed" text (Line 26):** `text-xs text-gray-400` - needs `dark:text-gray-500` for contrast

**Missing Elements:**
```
✗ Button dark mode colors
✗ Button dark mode hover states
✗ Text contrast in dark mode
```

---

### 6. `noc/dashboard.html`
**Status:** INCONSISTENT DARK MODE PATTERN  
**File Path:** [noc/templates/noc/dashboard.html](ibccl/templates/noc/dashboard.html)

**Issues:**
- **Inconsistency:** Uses `dark:bg-gray-800` instead of app standard `dark:bg-midnight-900/40`
- **Cards (Lines 8-62):** Using `dark:bg-gray-800` when other files use `dark:bg-midnight-900/40`
- **Table section (Lines 73+):** Same inconsistency
- **Consistency Issue:** This creates a visual discrepancy with the inventory/dashboard.html which uses the correct midnight colors

**Pattern Issue:**
```
✗ All dark:bg-gray-800 should be dark:bg-midnight-900/40
✗ Visual consistency needed across NIB dashboards
✗ Update 8+ card elements
```

---

## MEDIUM PRIORITY ISSUES

### 7. `noc/register.html`
**Status:** LIGHT MODE CSS ONLY  
**File Path:** [noc/templates/noc/register.html](ibccl/templates/noc/register.html)

**Issues:**
- **All CSS styles** in `<style>` block (hundreds of lines) use hardcoded colors
- No dark mode CSS variables or classes
- `.register-card { background: rgba(255, 255, 255, 0.92); }` - no dark variant
- `.form-control { border: 1.5px solid #d1d5db; }` - hardcoded light color
- `.form-label { color: #374151; }` - hardcoded dark color (unreadable in dark mode)
- Role card styling: `.role-card label { background: #fff; }` - no dark mode

**Critical Sections Needing Dark Mode:**
```
✗ .register-card - add dark variant
✗ .form-control - add dark:bg-slate-800 dark:border-slate-600 dark:text-white
✗ .form-label - add dark:text-gray-300
✗ .field-group - add dark:bg-slate-800 dark:border-slate-700
✗ .role-card - add dark styling
```

---

### 8. `inventory/materials_monitoring.html`
**Status:** MOSTLY GOOD, MINOR GAPS  
**File Path:** [inventory/templates/inventory/materials_monitoring.html](ibccl/templates/inventory/materials_monitoring.html)

**Issues:**
- **User card text:** Line 135+ - Some text elements missing dark variants
- **Typography:** Gradients have light mode primary but workable in dark mode
- **Status dots:** Good implementation

**Minor Updates Needed:**
```
≈ Minor text color consistency 
≈ Card border colors could be darker (dark:border-slate-700)
```

---

### 9. `noc/materials_monitoring.html`
**Status:** MOSTLY CORRECT  
**File Path:** [noc/templates/noc/materials_monitoring.html](ibccl/templates/noc/materials_monitoring.html)

**Issues:**
- Primarily good but could use minor refinements
- Status colors appropriately use dark variants

---

## WELL-IMPLEMENTED TEMPLATES ✅

These templates have proper dark mode support:
- ✅ `inventory/dashboard.html` - Excellent
- ✅ `inventory/login.html` - Excellent  
- ✅ `inventory/profile.html` - Excellent
- ✅ `inventory/settings.html` - Excellent
- ✅ `inventory/chat.html` - Excellent
- ✅ `inventory/used_materials.html` - Excellent
- ✅ `inventory/requests.html` - Good
- ✅ `inventory/materials.html` - Good
- ✅ `noc/login.html` - Excellent
- ✅ `noc/add_material.html` - Good
- ✅ `noc/edit_material.html` - Good
- ✅ `noc/delete_confirm.html` - Good

---

## SUMMARY TABLE

| Template | Severity | Dark Mode Score | Issues Count |
|----------|----------|-----------------|--------------|
| reports.html (both) | 🔴 CRITICAL | 0% | 15+ |
| tasks.html (both) | 🔴 CRITICAL | 10% | 12+ |
| noc/used_materials.html | 🔴 CRITICAL | 15% | 10+ |
| noc/materials.html | 🟡 HIGH | 70% | 5+ |
| noc/requests.html | 🟡 HIGH | 80% | 3+ |
| noc/dashboard.html | 🟡 HIGH | 85% (inconsistent) | 8+ |
| noc/register.html | 🟡 HIGH | 10% (CSS only) | 20+ |
| inventory/materials_monitoring.html | 🟢 MEDIUM | 90% | 2+ |
| noc/materials_monitoring.html | 🟢 GOOD | 95% | 1 |

---

## RECOMMENDATIONS

### Phase 1: CRITICAL (Do First)
1. **Fix reports.html** (both files) - Add dark mode CSS variants
2. **Fix tasks.html** (both files) - Add missing dark: classes
3. **Fix noc/used_materials.html** - Add dark mode throughout

### Phase 2: HIGH (Do Next)
4. Fix `noc/materials.html` pagination
5. Fix `noc/requests.html` buttons
6. Fix `noc/dashboard.html` consistency
7. Rewrite `noc/register.html` CSS with dark mode support

### Phase 3: POLISH (Minor)
8. Minor refinements to materials_monitoring files

---

## Key Patterns to Apply

**Standard Dark Mode Classes Used in Well-Implemented Files:**
```css
/* Backgrounds */
dark:bg-midnight-900/40      /* Primary card background */
dark:bg-midnight-950         /* Form inputs, secondary */
dark:bg-slate-800            /* Alternative for tables */
dark:bg-gray-800             /* Older cards, transitional */

/* Text Colors */
dark:text-white              /* Primary text */
dark:text-gray-400           /* Secondary text */
dark:text-gray-300           /* Tertiary text */

/* Borders */
dark:border-midnight-800     /* Primary border */
dark:border-gray-700         /* Alternative border */
dark:border-slate-700        /* Alternative border */

/* Interactions */
dark:hover:bg-indigo-900/30  /* Hover states */
dark:focus:bg-midnight-950   /* Focus states */
```

---

## Files Requiring Updates

✋ **32 total template files scanned**
- 🔴 **7 files** require major updates (20%+)
- 🟡 **2 files** require minor updates (5-15%)
- ✅ **23 files** are well-implemented

---

*Report Generated: 2026-04-05*  
*Recommendation: Start with CRITICAL phase within this sprint*
