from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin_developer/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('', include('isp_inventory.urls')),
]
