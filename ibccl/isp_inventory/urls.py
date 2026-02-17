from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('materials/', views.materials_view, name='materials'),
    path('materials/<int:pk>/json/', views.material_json, name='material_json'),
    path('tasks/', views.tasks_view, name='tasks'),
    path('requests/', views.requests_view, name='requests'),
    path('settings/', views.settings_view, name='settings'),
    path('reports/', views.reports_view, name='reports'),
    path('used-materials/', views.used_materials_view, name='used_materials'),
    path('api/used-materials/<int:pk>/', views.get_used_material_api, name='get_used_material_api'),
    path('used-materials/<int:pk>/manage/', views.manage_used_material, name='manage_used_material'),
    path('api/pending-requests/', views.pending_requests_api, name='pending_requests_api'),

]