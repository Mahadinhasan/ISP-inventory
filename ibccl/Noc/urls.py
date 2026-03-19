from django.urls import path, re_path
from . import views

urlpatterns = [
    path('dashboard/', views.noc_dashboard, name='noc_dashboard'),
    path('materials/', views.noc_materials, name='noc_materials'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/edit/<int:pk>/', views.edit_material, name='edit_material'),
    path('materials/delete/<int:pk>/', views.delete_material, name='delete_material'),
    path('materials/monitoring/', views.noc_materials_monitoring, name='noc_materials_monitoring'),
    path('requests/', views.noc_requests, name='noc_requests'),
    path('requests/approve/<int:pk>/', views.approve_request, name='approve_request'),
    path('requests/reject/<int:pk>/', views.reject_request, name='reject_request'),
    path('reports/', views.noc_reports, name='noc_reports'),
    path('notifications/', views.noc_notifications, name='noc_notifications'),
    path('profile/', views.noc_profile, name='noc_profile'),
    re_path(r'^.*$', views.custom_404_view, name='custom_404'),
]