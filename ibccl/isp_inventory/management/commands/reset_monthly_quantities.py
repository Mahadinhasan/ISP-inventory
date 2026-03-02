from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from isp_inventory.models import Material, MaterialMonthlyCount


class Command(BaseCommand):
    help = 'Reset monthly quantities at month end and archive current month data'

    def handle(self, *args, **options):
        now = timezone.now()
        current_month_start = datetime(now.year, now.month, 1)
        
        self.stdout.write(f"Processing month-end reset for {current_month_start.strftime('%B %Y')}...")
        
        materials_processed = 0
        
        for material in Material.objects.all():
            # Only process if material has quantity > 0
            if material.quantity > 0:
                # Archive the current quantity to MaterialMonthlyCount
                monthly_count, created = MaterialMonthlyCount.objects.get_or_create(
                    material=material,
                    month=current_month_start,
                    defaults={'count': material.quantity}
                )
                
                if not created:
                    # If record already exists, update it
                    monthly_count.count = material.quantity
                    monthly_count.save()
                
                # Reset quantity to 0
                material.quantity = 0
                material.save()
                
                materials_processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {material.name}: Archived {monthly_count.count} units, quantity reset to 0"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMonth-end reset complete! Processed {materials_processed} materials."
            )
        )
