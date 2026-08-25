import re
import os

views_path = 'isp_inventory/views.py'
with open(views_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the mappings for each view function to its CBV class name and whether it requires LoginRequiredMixin
view_mappings = [
    ('login_view', 'LoginView', False, ['GET', 'POST']),
    ('logout_view', 'LogoutView', True, ['GET', 'POST']),
    ('token_refresh_view', 'TokenRefreshView', False, ['GET', 'POST']),
    ('dashboard', 'DashboardView', True, ['GET', 'POST']),
    ('materials_monitoring_view', 'MaterialsMonitoringView', True, ['GET']),
    ('get_branch_stock_api', 'BranchStockApiView', True, ['GET']),
    ('get_recent_used_materials_api', 'RecentUsedMaterialsApiView', True, ['GET']),
    ('get_monitoring_users_api', 'MonitoringUsersApiView', True, ['GET']),
    ('materials_view', 'MaterialsView', True, ['GET', 'POST']),
    ('materials_export_excel', 'MaterialsExportExcelView', True, ['GET']),
    ('material_json', 'MaterialJsonView', True, ['GET']),
    ('requests_view', 'RequestsView', True, ['GET', 'POST']),
    ('reports_view', 'ReportsView', True, ['GET']),
    ('reports_export_excel', 'ReportsExportExcelView', True, ['GET']),
    ('reports_export_pdf', 'ReportsExportPdfView', True, ['GET']),
    ('settings_view', 'SettingsView', True, ['GET', 'POST']),
    ('profile_view', 'ProfileView', True, ['GET', 'POST']),
    ('used_materials_view', 'UsedMaterialsView', True, ['GET', 'POST']),
    ('get_used_material_api', 'UsedMaterialApiView', True, ['GET']),
    ('manage_used_material_api', 'ManageUsedMaterialApiView', True, ['POST']),
    ('pending_requests_api', 'PendingRequestsApiView', True, ['GET']),
    ('chat_view', 'ChatView', True, ['GET']),
    ('chat_history_api', 'ChatHistoryApiView', True, ['GET']),
    ('refundable_materials_view', 'RefundableMaterialsView', True, ['GET', 'POST']),
    ('get_refundable_material_api', 'RefundableMaterialApiView', True, ['GET']),
    ('get_refundable_material_usage_api', 'RefundableMaterialUsageApiView', True, ['GET']),
    ('damaged_materials_view', 'DamagedMaterialsView', True, ['GET', 'POST']),
    ('report_damage_auto', 'ReportDamageAutoView', True, ['POST']),
    ('get_damaged_material_api', 'DamagedMaterialApiView', True, ['GET']),
    ('custom_404_view', 'Custom404View', False, ['GET']),
    ('backup_restore_view', 'BackupRestoreView', True, ['GET', 'POST']),
    ('logs_view', 'LogsView', True, ['GET']),
    ('trash_view', 'TrashView', True, ['GET', 'POST']),
]

# Let's create the CBVs at the end of views.py or wrapping each view cleanly
cbv_declarations = []
cbv_declarations.append("\n\n# ==========================================================================")
cbv_declarations.append("# CLASS-BASED VIEWS (CBVs) & ENDPOINTS")
cbv_declarations.append("# ==========================================================================\n")

for fn_name, cls_name, login_req, methods in view_mappings:
    base_class = "LoginRequiredMixin, View" if login_req else "View"
    cbv_declarations.append(f"""
class {cls_name}({base_class}):
    \"\"\"Class-based view for {fn_name}.\"\"\"
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return {fn_name}(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return {fn_name}(request, *args, **kwargs)
""")

# Append the CBV declarations to views.py
if "# CLASS-BASED VIEWS (CBVs) & ENDPOINTS" not in content:
    new_content = content + "\n".join(cbv_declarations)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully appended CBV classes to views.py")
else:
    print("CBVs already present in views.py")
