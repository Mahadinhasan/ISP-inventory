from django.apps import AppConfig


class IspInventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'isp_inventory'
    def ready(self):
        # import signals so they are registered when the app is ready
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
