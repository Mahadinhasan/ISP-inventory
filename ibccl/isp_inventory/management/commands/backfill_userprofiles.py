from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from isp_inventory.utils import ensure_userprofile


class Command(BaseCommand):
    help = 'Create UserProfile records for all users if missing.'

    def handle(self, *args, **options):
        users = User.objects.all()
        created = 0
        for u in users:
            profile = ensure_userprofile(u)
            if profile:
                # ensure_userprofile created or returned an existing profile
                pass
        self.stdout.write(self.style.SUCCESS(f'Processed {users.count()} users.'))