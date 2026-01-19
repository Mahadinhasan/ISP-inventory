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
    path('request/approve/<int:pk>/', views.approve_request, name='approve_request'),
    path('settings/', views.settings_view, name='settings'),
    path('reports/', views.reports_view, name='reports'),
    path('used-materials/', views.used_materials_view, name='used_materials'),
    path('used-materials/<int:pk>/manage/', views.manage_used_material, name='manage_used_material'),

]