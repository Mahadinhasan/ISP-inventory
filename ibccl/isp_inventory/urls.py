from django.urls import path
from . import views

urlpatterns = [
    # ── Authentication & Core Views ──
    path('', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('backup-restore/', views.BackupRestoreView.as_view(), name='backup_restore'),
    path('logs/', views.LogsView.as_view(), name='logs'),
    path('trash/', views.TrashView.as_view(), name='trash'),
    path('chat/', views.ChatView.as_view(), name='chat'),

    # ── Materials & Inventory Management ──
    path('materials/', views.MaterialsView.as_view(), name='materials'),
    path('materials/<int:pk>/json/', views.MaterialJsonView.as_view(), name='material_json'),
    path('materials/export/excel/', views.MaterialsExportExcelView.as_view(), name='materials_export_excel'),
    path('requests/', views.RequestsView.as_view(), name='requests'),
    path('monitoring/', views.MaterialsMonitoringView.as_view(), name='materials_monitoring'),

    # ── Used, Refundable & Damaged Materials ──
    path('used-materials/', views.UsedMaterialsView.as_view(), name='used_materials'),
    path('refundable-materials/', views.RefundableMaterialsView.as_view(), name='refundable_materials'),
    path('damaged-materials/', views.DamagedMaterialsView.as_view(), name='damaged_materials'),
    path('damaged-materials/report-auto/', views.ReportDamageAutoView.as_view(), name='report_damage_auto'),

    # ── Reports & Exports ──
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('reports/export/excel/', views.ReportsExportExcelView.as_view(), name='reports_export_excel'),
    path('reports/export/pdf/', views.ReportsExportPdfView.as_view(), name='reports_export_pdf'),

    # ── JSON REST APIs ──
    path('api/used-materials/<int:pk>/', views.UsedMaterialApiView.as_view(), name='get_used_material_api'),
    path('api/used-materials/<int:pk>/manage/', views.ManageUsedMaterialApiView.as_view(), name='manage_used_material'),
    path('api/refundable-materials/<int:pk>/', views.RefundableMaterialApiView.as_view(), name='get_refundable_material_api'),
    path('api/refundable-materials-usage/<int:pk>/', views.RefundableMaterialUsageApiView.as_view(), name='get_refundable_material_usage_api'),
    path('api/damaged-materials/<int:pk>/', views.DamagedMaterialApiView.as_view(), name='get_damaged_material_api'),
    path('api/pending-requests/', views.PendingRequestsApiView.as_view(), name='pending_requests_api'),
    path('api/chat/<int:user_id>/', views.ChatHistoryApiView.as_view(), name='chat_history_api'),
    path('api/branch-stock/<int:user_id>/', views.BranchStockApiView.as_view(), name='get_branch_stock_api'),
    path('api/monitoring-users/', views.MonitoringUsersApiView.as_view(), name='get_monitoring_users_api'),
    path('api/recent-used-materials/', views.RecentUsedMaterialsApiView.as_view(), name='get_recent_used_materials_api'),
]