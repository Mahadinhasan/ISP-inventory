from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from isp_inventory.models import MaterialRequest, UsedMaterial, SystemSetting


class Command(BaseCommand):
    help = 'Auto-archive Material Requests and Used Materials from previous months (monthly auto-archive system)'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Get current month start
        current_month_start = datetime(now.year, now.month, 1)
        
        # Check if this month's archive has already been processed
        system_key = f"request_archive_{now.year}_{now.month}"
        try:
            setting = SystemSetting.objects.get(key=system_key)
            self.stdout.write(self.style.WARNING(
                f'Request archive already processed for {current_month_start.strftime("%B %Y")}'
            ))
            return
        except SystemSetting.DoesNotExist:
            pass
        
        self.stdout.write(self.style.SUCCESS(f"🔄 Starting auto-archive for {current_month_start.strftime('%B %Y')}..."))
        
        archived_count = 0
        
        # Archive all requests from previous years
        previous_year_requests = MaterialRequest.objects.filter(
            requested_at__year__lt=now.year,
            is_archived=False
        )
        prev_year_count = previous_year_requests.count()
        if prev_year_count > 0:
            previous_year_requests.update(
                is_archived=True,
                archived_at=now
            )
            archived_count += prev_year_count
            self.stdout.write(self.style.SUCCESS(f"✓ Archived {prev_year_count} requests from previous years"))
        
        # Archive all requests from previous months in current year
        previous_month_requests = MaterialRequest.objects.filter(
            requested_at__year=now.year,
            requested_at__month__lt=now.month,
            is_archived=False
        )
        prev_month_count = previous_month_requests.count()
        if prev_month_count > 0:
            previous_month_requests.update(
                is_archived=True,
                archived_at=now
            )
            archived_count += prev_month_count
            self.stdout.write(self.style.SUCCESS(f"✓ Archived {prev_month_count} requests from previous months"))
        
        # ── Archive Used Materials from previous years ──
        previous_year_used = UsedMaterial.objects.filter(
            added_at__year__lt=now.year,
            is_archived=False
        )
        prev_year_used_count = previous_year_used.count()
        if prev_year_used_count > 0:
            previous_year_used.update(
                is_archived=True,
                archived_at=now
            )
            archived_count += prev_year_used_count
            self.stdout.write(self.style.SUCCESS(f"✓ Archived {prev_year_used_count} used materials from previous years"))
        
        # ── Archive Used Materials from previous months in current year ──
        previous_month_used = UsedMaterial.objects.filter(
            added_at__year=now.year,
            added_at__month__lt=now.month,
            is_archived=False
        )
        prev_month_used_count = previous_month_used.count()
        if prev_month_used_count > 0:
            previous_month_used.update(
                is_archived=True,
                archived_at=now
            )
            archived_count += prev_month_used_count
            self.stdout.write(self.style.SUCCESS(f"✓ Archived {prev_month_used_count} used materials from previous months"))
        
        # Mark this month's archive as processed
        SystemSetting.objects.update_or_create(
            key=system_key,
            defaults={
                'value': str(now),
                'description': f'Request auto-archive processed for {current_month_start.strftime("%B %Y")} - {archived_count} total items archived'
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Archive complete! Total requests archived: {archived_count}'))
