from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', views.token_refresh_view, name='token_refresh'),  # JWT silent refresh
    path('dashboard/', views.dashboard, name='dashboard'),
    path('materials/', views.materials_view, name='materials'),
    path('materials/<int:pk>/json/', views.material_json, name='material_json'),
    path('materials/export/excel/', views.materials_export_excel, name='materials_export_excel'),
    # path('tasks/', views.tasks_view, name='tasks'),
    path('requests/', views.requests_view, name='requests'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('backup-restore/', views.backup_restore_view, name='backup_restore'),
    path('logs/', views.logs_view, name='logs'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/excel/', views.reports_export_excel, name='reports_export_excel'),
    path('reports/export/pdf/', views.reports_export_pdf, name='reports_export_pdf'),
    path('used-materials/', views.used_materials_view, name='used_materials'),
    path('refundable-materials/', views.refundable_materials_view, name='refundable_materials'),
    path('damaged-materials/', views.damaged_materials_view, name='damaged_materials'),
    path('damaged-materials/report-auto/', views.report_damage_auto, name='report_damage_auto'),
    path('monitoring/', views.materials_monitoring_view, name='materials_monitoring'),
    path('api/used-materials/<int:pk>/', views.get_used_material_api, name='get_used_material_api'),
    path('api/used-materials/<int:pk>/manage/', views.manage_used_material_api, name='manage_used_material'),
    path('api/refundable-materials/<int:pk>/', views.get_refundable_material_api, name='get_refundable_material_api'),
    path('api/refundable-materials-usage/<int:pk>/', views.get_refundable_material_usage_api, name='get_refundable_material_usage_api'),
    path('api/damaged-materials/<int:pk>/', views.get_damaged_material_api, name='get_damaged_material_api'),
    path('api/pending-requests/', views.pending_requests_api, name='pending_requests_api'),
    path('chat/', views.chat_view, name='chat'),
    path('api/chat/<int:user_id>/', views.chat_history_api, name='chat_history_api'),
    path('api/branch-stock/<int:user_id>/', views.get_branch_stock_api, name='get_branch_stock_api'),
    path('api/recent-used-materials/', views.get_recent_used_materials_api, name='get_recent_used_materials_api'),

    # Catch-all: show custom 404 for any unrecognised URL (works in DEBUG=True too)
    # re_path(r'^.*$', views.custom_404_view, name='custom_404'),
]