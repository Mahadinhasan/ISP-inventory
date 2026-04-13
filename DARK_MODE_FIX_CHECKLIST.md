# Dark Mode Styling - Detailed Fix Checklist

## 🔴 CRITICAL PRIORITY (Fix First)

### File 1: `inventory/reports.html` and `noc/reports.html`
**Severity:** 🔴 CRITICAL | **Dark Mode Score:** 0% | **Effort:** 2-3 hours

**Problem:** All styling uses HARDCODED CSS with no dark mode support

**Elements to Fix:**
```
Line Range  | Element            | Current               | Needs
----------|-------------------|----------------------|------------------
4-50      | .rpt-card         | background: #fff      | dark:bg-slate-800
8-14      | .stat-card        | hardcoded colors      | dark variants for all
15-25     | Table header      | bg: linear-gradient   | dark gradient
30-35     | Table rows        | border: #f3f4f6       | dark:border-gray-700
40-50     | Badges            | hardcoded bg/text     | dark:bg-slate-700
```

**CSS Fix Strategy:** Add media query block:
```css
@media (prefers-color-scheme: dark) {
  .rpt-card { background: rgb(30, 41, 59); color: white; }
  .rpt-table td { color: #d1d5db; border-color: #374151; }
  /* ... etc for all elements ... */
}
```

---

### File 2-3: `inventory/tasks.html` and `noc/tasks.html`
**Severity:** 🔴 CRITICAL | **Dark Mode Score:** 10% | **Effort:** 1.5 hours each

**Problem:** Missing dark: classes on every major element

**Quick Fix Checklist:**
```
Line  | Current Class                    | Add Dark Classes
------|----------------------------------|------------------------------------
8     | text-gray-900 (h1)              | dark:text-white
9     | text-gray-600 (subtitle)        | dark:text-gray-400
13    | Create button                   | dark:hover:bg-indigo-800
17    | bg-white (card)                 | dark:bg-gray-800 (or midnight-900/40)
19    | text-gray-900 (title)           | dark:text-white
22    | text-gray-600 (icons)           | dark:text-gray-400
60    | bg-white (modal)                | dark:bg-gray-800
63    | text-gray-900 (modal h3)        | dark:text-white
68    | text-sm font-medium text-gray   | dark:text-gray-300
70+   | Form inputs                     | dark:bg-gray-700 dark:text-white dark:border-gray-600
```

**Specific Changes:**
1. Line 8: Change `class="text-4xl font-bold text-gray-900"` to `class="text-4xl font-bold text-gray-900 dark:text-white"`
2. Line 60: Change `class="bg-white"` to `class="bg-white dark:bg-gray-800"`
3. All form inputs: Add `dark:bg-gray-700 dark:border-gray-600 dark:text-white`

---

### File 4: `noc/used_materials.html`
**Severity:** 🔴 CRITICAL | **Dark Mode Score:** 15% | **Effort:** 1.5 hours

**Problem:** Light-only text colors throughout file

**Critical Fixes:**
```
Line  | Element                | Current               | Change To
------|------------------------|----------------------|---------------------------
6     | Page title (h1)        | text-gray-900        | text-gray-900 dark:text-white
45-59 | Table headers          | text-gray-900        | text-gray-900 dark:text-gray-300
62    | Table row hover        | hover:bg-gray-100    | hover:bg-gray-100 dark:hover:bg-gray-700
64    | Cell text              | text-gray-900        | text-gray-900 dark:text-gray-300
90    | Modal background       | bg-white             | bg-white dark:bg-gray-800
92    | Dropdown display       | text-gray-700        | text-gray-700 dark:text-gray-300
```

**Search/Replace Patterns:**
- Replace: `text-gray-900"` → `text-gray-900 dark:text-white"` (for headings)
- Replace: `text-gray-700"` → `text-gray-700 dark:text-gray-300"` (for text)
- Replace: `bg-white"` → `bg-white dark:bg-gray-800"` (for containers)
- Add: `dark:hover:bg-gray-700` to all hover states on rows

---

## 🟡 HIGH PRIORITY (Fix Next)

### File 5: `noc/materials.html` - Pagination
**Severity:** 🟡 HIGH | **Dark Mode Score:** 70% | **Effort:** 30 minutes

**Problem:** Pagination navigation (lines 124+) has NO dark mode

**Specific Fixes:**
```
Line    | Element                    | Fix
--------|---------------------------|-----------------------------
134     | Pagination nav             | Add dark:bg-gray-800
137     | Previous button            | Add dark:bg-gray-700 dark:text-gray-300
140     | Page number                | Add dark:bg-gray-800 dark:text-gray-400
151     | Next button                | Add dark:bg-gray-700 dark:text-gray-300
```

**HTML Update:**
```html
<!-- Line 134-151: Replace -->
<nav class="inline-flex -space-x-px dark:bg-gray-800 p-2 rounded-lg">
  <!-- Update each button with dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600 -->
</nav>
```

---

### File 6: `noc/requests.html` - Button Colors
**Severity:** 🟡 HIGH | **Dark Mode Score:** 80% | **Effort:** 15 minutes

**Problem:** Action buttons (Approve/Reject) missing dark hover colors

**Specific Fixes:**
```
Line  | Button              | Current                  | Add Dark
------|---------------------|--------------------------|---------------------------
20    | Approve button      | bg-green-500 hover...    | dark:bg-green-600 dark:hover:bg-green-700
24    | Reject button       | bg-red-500 hover...      | dark:bg-red-600 dark:hover:bg-red-700
26    | "Processed" text    | text-xs text-gray-400    | dark:text-gray-500
```

**Quick Edit:**
```html
<!-- Line 20 -->
<button class="px-3 py-1 bg-green-500 text-white dark:bg-green-600 hover:bg-green-600 dark:hover:bg-green-700">

<!-- Line 24 -->
<button class="px-3 py-1 bg-red-500 text-white dark:bg-red-600 hover:bg-red-600 dark:hover:bg-red-700">
```

---

### File 7: `noc/dashboard.html` - Color Inconsistency
**Severity:** 🟡 HIGH | **Dark Mode Score:** 85% (inconsistent) | **Effort:** 20 minutes

**Problem:** Uses `dark:bg-gray-800` instead of app standard `dark:bg-midnight-900/40`

**What to Change:**
```
Current Pattern              | Change to
-----------------------------|-------------------------
dark:bg-gray-800            | dark:bg-midnight-900/40
dark:border-gray-700        | dark:border-midnight-800
```

**Files to Update:** All 8+ card elements in the dashboard

**Search/Replace:**
1. Find: `dark:bg-gray-800` → Replace: `dark:bg-midnight-900/40`
2. Find: `dark:border-gray-700` → Replace: `dark:border-midnight-800` (if inconsistent)

---

### File 8: `noc/register.html` - CSS-Only Styling
**Severity:** 🟡 HIGH | **Dark Mode Score:** 10% | **Effort:** 2-3 hours

**Problem:** 600+ lines of hardcoded CSS with NO dark mode support

**Major Elements to Add Dark Mode:**
```
CSS Class           | Current Color        | Add Dark Mode
-------------------|----------------------|----------------------------------
.register-card      | background: #fff     | dark: rgb(30, 41, 59)
.form-control       | border: #d1d5db      | dark: border #334155, bg #1e293b, text white
.form-label         | color: #374151       | dark: color #d1d5db
.field-group        | bg: #f8f7ff          | dark: bg #1e293b, border #334155
.role-card label    | background: #fff     | dark: background #1e293b, border #334155
.preset-btn         | bg: #f5f3ff          | dark: bg #312e81, color white
```

**Implementation Strategy:**
```css
/* Add at end of <style> block */
@media (prefers-color-scheme: dark) {
  .register-card { background: rgb(30, 41, 59); border-color: rgb(88, 102, 139); }
  .form-control { 
    background: rgb(30, 41, 59); 
    border-color: rgb(51, 65, 85);
    color: white;
  }
  /* ... continue for all elements ... */
}
```

---

## 📋 Implementation Checklist

### Critical Files (Deadline: This Week)
- [ ] `inventory/reports.html` - Convert CSS to dark mode support
- [ ] `noc/reports.html` - Convert CSS to dark mode support  
- [ ] `inventory/tasks.html` - Add dark: classes
- [ ] `noc/tasks.html` - Add dark: classes
- [ ] `noc/used_materials.html` - Add dark: text color variants

### High Priority (Deadline: Next Week)
- [ ] `noc/materials.html` - Fix pagination (30 min)
- [ ] `noc/requests.html` - Fix buttons (15 min)
- [ ] `noc/dashboard.html` - Fix inconsistency (20 min)
- [ ] `noc/register.html` - Add dark CSS (2-3 hours)

---

## Testing Checklist After Fixes

For each file, test:
- [ ] Toggle dark mode - all elements visible
- [ ] Text readable (sufficient contrast)
- [ ] Buttons/interactive elements clear
- [ ] Forms/inputs properly styled
- [ ] No hardcoded light colors showing through
- [ ] Modal/popup dark styling correct
- [ ] Table rows/headers properly styled
- [ ] Status badges distinguishable

---

## Related Files (Already Good)
✅ `noc/materials_monitoring.html` - Minor refinements only  
✅ `inventory/materials_monitoring.html` - Minor refinements only  
✅ All login/register/profile templates - Well implemented

---

**Total Estimated Effort:** 9-12 hours for ALL fixes
**Priority Distribution:** 
- Critical (5-6 hours)
- High (3-4 hours)  
- Polish (1-2 hours)
