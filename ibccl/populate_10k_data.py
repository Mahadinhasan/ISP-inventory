import os
import sys
import django
import time
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest, UsedMaterial, UserProfile

def populate():
    print("=== Starting 10,000 (10K) Test Data Population ===")
    start_time = time.time()

    # Get reference users
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.first()

    try:
        store_user = User.objects.get(username='store')
    except User.DoesNotExist:
        store_user = admin_user

    try:
        noc_user = User.objects.get(username='noc')
    except User.DoesNotExist:
        noc_user = admin_user

    try:
        mirpur_user = User.objects.get(username='mirpur')
    except User.DoesNotExist:
        mirpur_user = admin_user

    categories = ['Internet', 'Dish', 'Fiber', 'Common item', 'Work shop']
    types = ['Piece', 'Meter']

    existing_count = Material.objects.count()
    print(f"Current Material Count in Database: {existing_count}")

    target_count = 10000
    needed_count = target_count - existing_count

    if needed_count > 0:
        print(f"Generating {needed_count} new materials...")

        material_prefix_names = [
            "Cat6 UTP Cable Roll", "Fiber Optical Patch Cord", "ONU Router Dual Band", 
            "MC Media Converter 20KM", "SFP Transceiver Module 10G", "Optical Fiber Closure 24 Core",
            "RJ45 Modular Connector Box", "Drop Cable 2 Core Flat", "Optical Power Meter Tester",
            "VFL Laser Pen Fault Finder", "Fusion Splicer Protection Sleeves", "Splitter 1:8 PLC Cassette",
            "Splitter 1:16 Steel Tube", "Patch Panel 24 Port Cat6", "Server Rack 9U Wall Mount",
            "UPS 1200VA Backup", "Core Router Switch Gigabit", "Distribution Box 16 Core",
            "Coaxial Cable RG6 300m", "DC Adapter 12V 2A", "BNC Connector Male",
            "Fiber Attenuator 5dB", "Krone Punch Down Tool", "Network Cable Tester Pro"
        ]

        batch_size = 2000
        total_batches = (needed_count + batch_size - 1) // batch_size
        total_inserted = 0

        created_counter = existing_count + 1
        for batch_idx in range(total_batches):
            batch_list = []
            current_batch_count = min(batch_size, needed_count - total_inserted)

            for i in range(current_batch_count):
                prefix = random.choice(material_prefix_names)
                name = f"{prefix} #{created_counter}"
                cat = random.choice(categories)
                typ = random.choice(types)
                qty = random.randint(5, 500)
                rate = random.randint(50, 4500)
                total = qty * rate
                rem = max(0, qty - random.randint(0, qty))
                min_lvl = random.randint(5, 30)

                status = 'Normal'
                if qty == 0:
                    status = 'Out of Stock'
                elif qty <= min_lvl:
                    status = 'Low Stock'

                creator = store_user if cat != 'Internet' else noc_user

                batch_list.append(Material(
                    name=name,
                    category=cat,
                    Type=typ,
                    quantity=qty,
                    rate=rate,
                    total_price=total,
                    Remaining_stock=rem,
                    min_stock_level=min_lvl,
                    notes=f"Auto-generated load test material item #{created_counter}",
                    status=status,
                    created_by=creator
                ))
                created_counter += 1

            Material.objects.bulk_create(batch_list, batch_size=batch_size, ignore_conflicts=True)
            total_inserted += len(batch_list)
            print(f"   Inserted Batch {batch_idx + 1}/{total_batches} ({total_inserted}/{needed_count})")

    final_material_count = Material.objects.count()
    print(f"Total Materials in Database Now: {final_material_count}")

    # Now create material requests for Mirpur Branch
    if MaterialRequest.objects.filter(requester=mirpur_user).count() < 500:
        print("\nGenerating 500 Material Requests for 'mirpur' Branch...")
        sample_materials = list(Material.objects.all()[:500])
        requests_to_create = []
        req_types = ['Regular', 'Emergency']
        req_statuses = ['Pending', 'Approved', 'Dispatched', 'Received', 'Rejected']

        for idx, mat in enumerate(sample_materials):
            requests_to_create.append(MaterialRequest(
                requester=mirpur_user,
                material=mat,
                quantity=random.randint(1, 20),
                request_type=random.choice(req_types),
                status=random.choice(req_statuses),
                admin_note=f"Load test request #{idx+1}"
            ))

        MaterialRequest.objects.bulk_create(requests_to_create, batch_size=500, ignore_conflicts=True)
        print(f"Created {len(requests_to_create)} Material Requests for 'mirpur' Branch.")

    elapsed = time.time() - start_time
    print(f"\nCompleted 10K Data Population in {elapsed:.2f} seconds!")

if __name__ == '__main__':
    populate()
