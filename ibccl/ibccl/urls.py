from django.contrib import admin
from django.urls import path, include
from isp_inventory.views import custom_404_view

# Custom error handlers
handler404 = custom_404_view

urlpatterns = [
    path('admin_developer/', admin.site.urls),
    path('ibccl/', include('isp_inventory.urls')),
    path('noc/', include('Noc.urls')),
]