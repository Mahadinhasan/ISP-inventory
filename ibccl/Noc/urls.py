from django.urls import path
from . import views

app_name = 'noc'

urlpatterns = [
    # Authentication
    path('login/', views.noc_login_view, name='login'),
    path('logout/', views.noc_logout_view, name='logout'),
    # Main views
    path('dashboard/', views.noc_dashboard, name='dashboard'),
    path('materials/', views.noc_materials, name='materials'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/edit/<int:pk>/', views.edit_material, name='edit_material'),
    path('materials/delete/<int:pk>/', views.delete_material, name='delete_material'),
    path('materials/monitoring/', views.noc_materials_monitoring, name='materials_monitoring'),
    path('requests/', views.noc_requests, name='requests'),
    path('requests/approve/<int:pk>/', views.approve_request, name='approve_request'),
    path('requests/reject/<int:pk>/', views.reject_request, name='reject_request'),
    path('used-materials/', views.noc_used_materials, name='used_materials'),
    path('reports/', views.noc_reports, name='reports'),
    path('notifications/', views.noc_notifications, name='notifications'),
    path('profile/', views.noc_profile, name='profile'),
    path('logs/', views.noc_logs, name='logs'),
    path('trash/', views.trash_view, name='trash'),
    # Mac/Serial Numbers
    path('mac-serials/add/', views.add_mac_serials, name='add_mac_serials'),
    path('mac-serials/edit/<int:pk>/', views.edit_mac_serials, name='edit_mac_serials'),
    path('mac-serials/list/', views.list_mac_serials, name='list_mac_serials'),
    path('mac-serials/delete/<int:pk>/', views.delete_mac_serial, name='delete_mac_serial'),
    # API
    path('api/branch-materials/', views.get_branch_materials, name='get_branch_materials'),
    # Refundable Materials management
    path('refundable/log/', views.noc_log_refundable, name='log_refundable'),
    path('refundable/edit/<int:pk>/', views.noc_edit_refundable, name='edit_refundable'),
    path('refundable/delete/<int:pk>/', views.noc_delete_refundable, name='delete_refundable'),
    path('refundable/process/<int:pk>/', views.noc_process_refundable, name='process_refundable'),
    path('api/refundable/<int:pk>/', views.noc_get_refundable_api, name='get_refundable_api'),
    # Damaged Materials management
    path('damaged/log/', views.noc_log_damaged, name='log_damaged'),
    path('damaged/edit/<int:pk>/', views.noc_edit_damaged, name='edit_damaged'),
    path('damaged/delete/<int:pk>/', views.noc_delete_damaged, name='delete_damaged'),
    path('damaged/process/<int:pk>/', views.noc_process_damaged, name='process_damaged'),
    path('api/damaged/<int:pk>/', views.noc_get_damaged_api, name='get_damaged_api'),
    path('refundable-materials/', views.noc_refundable_materials_view, name='refundable_materials'),
    path('damaged-materials/', views.noc_damaged_materials_view, name='damaged_materials'),
]