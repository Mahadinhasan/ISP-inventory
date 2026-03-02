from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from isp_inventory.models import MaterialMonthlyCount, Material


class Command(BaseCommand):
    help = 'Reset monthly counts at month end (creates new month record with count=0)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Specific month to reset (format: YYYY-MM, default: current month)',
            default=None,
        )

    def handle(self, *args, **options):
        now = timezone.now()
        
        if options['month']:
            try:
                month_date = datetime.strptime(options['month'], '%Y-%m')
                month_date = month_date.replace(day=1)
                self.stdout.write(f"Resetting counts for: {month_date.strftime('%B %Y')}")
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid month format. Use YYYY-MM'))
                return
        else:
            month_date = datetime(now.year, now.month, 1)
            self.stdout.write(f"Resetting counts for: {month_date.strftime('%B %Y')}")
        
        # Reset all materials for the specified month
        materials = Material.objects.all()
        reset_count = 0
        
        for material in materials:
            monthly_count, created = MaterialMonthlyCount.objects.get_or_create(
                material=material,
                month=month_date.date(),
                defaults={'count': 0}
            )
            
            if not created and monthly_count.count != 0:
                monthly_count.count = 0
                monthly_count.save()
                reset_count += 1
            elif created:
                reset_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Successfully reset {reset_count} material monthly counts'
            )
        )
