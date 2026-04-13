# Dark Mode Styling - Quick Reference Summary

## 🔴 CRITICAL - 3 Files (Highest Priority)

### 1. Reports.html (inventory/ + noc/) - HARDCODED CSS
- **Problem:** All styles hardcoded in `<style>` block - doesn't recognize dark mode
- **Fix:** Convert to Tailwind dark: classes
- **Impact:** Completely unreadable in dark mode
- **Elements Affected:** Cards, tables, stat boxes, badges (15+ elements)

### 2. Tasks.html (inventory/ + noc/) - MISSING DARK CLASSES
- **Problem:** Headers, cards, modals have only light mode styling
- **Lines:** 8-9 (title/subtitle), 17+ (cards), 60+ (modal)
- **Fix:** Add `dark:` prefixes to all text/background classes
- **Impact:** Harsh/unreadable in dark mode
- **Elements:** 12+ missing dark variants

### 3. noc/used_materials.html - TEXT COLORS NOT DARK
- **Problem:** Light-only text colors throughout (text-gray-900, text-gray-700)
- **Lines:** 6 (title), 45-59 (table headers), multiple text elements
- **Fix:** Add dark:text-white, dark:text-gray-300 variants
- **Impact:** Hard to read text in dark mode
- **Elements:** 10+ text elements

---

## 🟡 HIGH - 4 Files (Should Fix Soon)

### 4. noc/materials.html - Pagination Not Styled
- **Problem:** Navigation buttons/links missing dark mode (lines 124+)
- **Quick Fix:** Add `dark:bg-gray-800 dark:text-gray-400` to pagination
- **Impact:** Navigation invisible in dark mode

### 5. noc/requests.html - Buttons Missing Dark States
- **Problem:** Approve/Reject buttons (lines 20-24) have no dark hover colors
- **Quick Fix:** Add `dark:bg-green-600`, `dark:bg-red-600` variants
- **Impact:** Buttons hard to see when hovering in dark mode

### 6. noc/dashboard.html - Color Scheme Inconsistency
- **Problem:** Uses `dark:bg-gray-800` instead of app standard `dark:bg-midnight-900/40`
- **Quick Fix:** Find/replace gray-800 → midnight-900/40 (8+ locations)
- **Impact:** Visual inconsistency with other dashboard pages

### 7. noc/register.html - Pure CSS (No Dark Mode)
- **Problem:** ALL styles hardcoded with light colors, 20+ CSS classes
- **Quick Fix:** Add dark mode CSS for major classes (.register-card, .form-control, .form-label, .role-card)
- **Impact:** Registration form unreadable in dark mode

---

## 📊 File Status Quick Check

```
✅ GOOD IMPLEMENTATION (23 files):
   inventory/dashboard.html
   inventory/login.html
   inventory/profile.html
   inventory/settings.html
   inventory/chat.html
   inventory/used_materials.html
   inventory/requests.html
   inventory/materials.html
   noc/login.html
   noc/add_material.html
   noc/edit_material.html
   noc/delete_confirm.html
   + others with >80% dark mode coverage

⚠️  NEEDS WORK (9 files):
   🔴 reports.html (inventory) - 0% dark mode
   🔴 reports.html (noc) - 0% dark mode
   🔴 tasks.html (inventory) - 10% dark mode
   🔴 tasks.html (noc) - 10% dark mode
   🔴 noc/used_materials.html - 15% dark mode
   🟡 noc/materials.html - 70% dark mode
   🟡 noc/requests.html - 80% dark mode
   🟡 noc/dashboard.html - 85% (but inconsistent)
   🟡 noc/register.html - 10% dark mode
```

---

## Dark Mode Pattern Reference

**Use These Classes**:
```
Backgrounds:
  dark:bg-midnight-900/40    (primary cards)
  dark:bg-midnight-950       (inputs, secondary)
  dark:bg-slate-800          (tables, optional)

Text:
  dark:text-white            (headings, primary)
  dark:text-gray-400         (secondary text)
  dark:text-gray-300         (tertiary text)

Borders:
  dark:border-midnight-800   (primary)
  dark:border-gray-700       (secondary)

Hover/Interactive:
  dark:hover:bg-indigo-900/30
  dark:focus:ring-indigo-500
```

---

## Action Plan by Priority

**Week 1 (MUST HAVE):**
- [ ] Fix reports.html (both files) - Convert hardcoded CSS to Tailwind
- [ ] Fix tasks.html (both files) - Add missing dark: classes
- [ ] Fix noc/used_materials.html - Add text color variants

**Week 2 (SHOULD HAVE):**
- [ ] Fix noc/materials.html pagination
- [ ] Fix noc/requests.html buttons
- [ ] Fix noc/dashboard.html consistency
- [ ] Fix noc/register.html CSS

**Quick Wins (15-30 min each):**
- Pagination styling on 1 file
- Button colors on 1 file
- Text color consistency on 2-3 files

---

## Files Ready for Review

See: **DARK_MODE_AUDIT_REPORT.md** for detailed breakdown with line numbers and specific issues.
