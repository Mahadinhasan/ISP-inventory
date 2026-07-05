from django.contrib import admin
from django.urls import path, include, re_path
from isp_inventory.views import custom_404_view
from django.conf import settings
from django.conf.urls.static import static

# Custom error handlers
handler404 = custom_404_view

urlpatterns = [
    path('admin@/', admin.site.urls),
    path('', include('isp_inventory.urls')),
    path('noc/', include(('Noc.urls', 'noc'), namespace='noc')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Also add standard static files fallback
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns.append(re_path(r'^.*$', custom_404_view, name='custom_404'))