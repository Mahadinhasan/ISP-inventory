from django.core.management.base import BaseCommand
from isp_inventory.models import Material


class Command(BaseCommand):
    help = 'Set Type for existing materials based on category (Fiber=Meter, others=Piece)'

    def handle(self, *args, **options):
        # Update materials with quantity > 0
        materials_updated = 0
        
        for material in Material.objects.filter(quantity__gt=0):
            if material.category == 'Fiber':
                material.Type = 'Meter'
            else:
                material.Type = 'Piece'
            material.save()
            materials_updated += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {material.name}: Set Type to {material.Type}"
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nType assignment complete! Updated {materials_updated} materials with quantity > 0."
            )
        )