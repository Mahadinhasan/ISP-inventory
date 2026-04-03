from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('materials/', views.materials_view, name='materials'),
    path('materials/<int:pk>/json/', views.material_json, name='material_json'),
    # path('tasks/', views.tasks_view, name='tasks'),
    path('requests/', views.requests_view, name='requests'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/excel/', views.reports_export_excel, name='reports_export_excel'),
    path('reports/export/pdf/', views.reports_export_pdf, name='reports_export_pdf'),
    path('used-materials/', views.used_materials_view, name='used_materials'),
    path('monitoring/', views.materials_monitoring_view, name='materials_monitoring'),
    path('api/used-materials/<int:pk>/', views.get_used_material_api, name='get_used_material_api'),
    path('api/used-materials/<int:pk>/manage/', views.manage_used_material_api, name='manage_used_material'),
    path('api/pending-requests/', views.pending_requests_api, name='pending_requests_api'),
    path('chat/', views.chat_view, name='chat'),
    path('api/chat/<int:user_id>/', views.chat_history_api, name='chat_history_api'),

    # Catch-all: show custom 404 for any unrecognised URL (works in DEBUG=True too)
    # re_path(r'^.*$', views.custom_404_view, name='custom_404'),
]