from django.urls import path
from . import views

urlpatterns = [
    path('',views.noc_dashboard,name='noc_dashboard'),
]