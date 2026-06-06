from django.contrib import admin
from django.urls import path, include,re_path
from isp_inventory.views import custom_404_view

# Custom error handlers
handler404 = custom_404_view

urlpatterns = [
    path('admin@/', admin.site.urls),
    path('', include('isp_inventory.urls')),
    path('noc/', include(('Noc.urls', 'noc'), namespace='noc')),
    re_path(r'^.*$', custom_404_view, name='custom_404'),
]