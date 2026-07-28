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

        # Start background auto backup scheduler thread
        import os
        import threading
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            try:
                from .utils import start_auto_backup_scheduler
                t = threading.Thread(target=start_auto_backup_scheduler, daemon=True)
                t.start()
            except Exception:
                pass

