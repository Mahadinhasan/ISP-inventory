from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/inventory/materials-monitoring/$",
        consumers.MaterialsMonitoringConsumer.as_asgi(),
    ),
    re_path(
        r"ws/notifications/$",
        consumers.NotificationsConsumer.as_asgi(),
    ),
]
