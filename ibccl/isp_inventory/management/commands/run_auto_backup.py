from django.core.management.base import BaseCommand
from isp_inventory.utils import run_auto_backup, get_auto_backup_config

class Command(BaseCommand):
    help = 'Executes an automated backup of the inventory database saved to Auto data_backup folder'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Auto Data Backup process..."))
        try:
            res = run_auto_backup(trigger_type='management_command')
            self.stdout.write(self.style.SUCCESS(
                f"Successfully created auto backup: {res['filename']} "
                f"({res['records_count']} records, size: {res['size']} bytes) at {res['timestamp']}"
            ))
            self.stdout.write(self.style.SUCCESS(f"Saved location: {res['path']}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Auto Backup Failed: {e}"))
