from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from isp_inventory.models import Material, MaterialMonthlyCount, SystemSetting


class Command(BaseCommand):
    help = 'Reset monthly quantities at month end, archive to monthly count, and accumulate remaining stock'

    def handle(self, *args, **options):
        now = timezone.now()
        current_month_start = datetime(now.year, now.month, 1)
        
        # Check if this month's reset has already been processed
        system_key = f"month_reset_{now.year}_{now.month}"
        try:
            setting = SystemSetting.objects.get(key=system_key)
            self.stdout.write(self.style.WARNING(f'Month-end reset already processed for {current_month_start.strftime("%B %Y")}'))
            return
        except SystemSetting.DoesNotExist:
            pass
        
        self.stdout.write(f"Processing month-end reset for {current_month_start.strftime('%B %Y')}...")
        
        materials_processed = 0
        
        for material in Material.objects.filter(quantity__gt=0):
            # Archive the current quantity to MaterialMonthlyCount
            monthly_count, created = MaterialMonthlyCount.objects.get_or_create(
                material=material,
                month=current_month_start,
                defaults={'count': material.quantity}
            )
            
            if not created:
                monthly_count.count = material.quantity
                monthly_count.save()
            
            # Accumulate leftover quantity into Remaining_stock
            material.Remaining_stock += material.quantity
            # Reset quantity (in stock) to 0 for the new month
            material.quantity = 0
            material.save()
            
            materials_processed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {material.name}: Archived {monthly_count.count} units, accumulated to Remaining_stock, quantity reset to 0"
                )
            )
        
        # Mark this month's reset as processed
        SystemSetting.objects.update_or_create(
            key=system_key,
            defaults={'value': str(now), 'description': f'Month-end reset processed for {current_month_start.strftime("%B %Y")}'}
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMonth-end reset complete! Processed {materials_processed} materials."
            )
        )
