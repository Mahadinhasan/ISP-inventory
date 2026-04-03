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
    path('reports/', views.noc_reports, name='reports'),
    path('notifications/', views.noc_notifications, name='notifications'),
    path('profile/', views.noc_profile, name='profile'),
]