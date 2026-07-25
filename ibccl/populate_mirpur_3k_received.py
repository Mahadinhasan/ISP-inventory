import os
import sys
import django
import time
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest

def populate_mirpur_received():
    print("=== Starting 3,000 'Received' Materials Population for 'mirpur' Branch ===")
    start_time = time.time()

    try:
        mirpur_user = User.objects.get(username='mirpur')
    except User.DoesNotExist:
        print("ERROR: User 'mirpur' not found in database!")
        return

    all_materials = list(Material.objects.all())
    if not all_materials:
        print("ERROR: No materials found in database!")
        return

    target_count = 3000
    existing_received = MaterialRequest.objects.filter(requester=mirpur_user, status='Received').count()
    print(f"Current 'Received' Material Requests for 'mirpur': {existing_received}")

    needed_count = max(0, target_count - existing_received)
    if needed_count > 0:
        print(f"Generating {needed_count} new 'Received' Material Requests for 'mirpur'...")

        batch_size = 1000
        total_batches = (needed_count + batch_size - 1) // batch_size
        total_inserted = 0

        for b_idx in range(total_batches):
            batch_list = []
            curr_count = min(batch_size, needed_count - total_inserted)
            for i in range(curr_count):
                mat = random.choice(all_materials)
                qty = random.randint(5, 50)
                rate = mat.rate or random.randint(100, 2000)
                total = qty * rate

                batch_list.append(MaterialRequest(
                    requester=mirpur_user,
                    material=mat,
                    quantity=qty,
                    rate=rate,
                    total_price=total,
                    status='Received',
                    request_type='Regular',
                    pass_on='Storekeeper Main Store Dispatched',
                    pass_on_at=timezone.now(),
                    received_by='mirpur',
                    received_at=timezone.now(),
                    admin_note=f"3K Received stock batch item #{total_inserted + i + 1}"
                ))

            MaterialRequest.objects.bulk_create(batch_list, batch_size=batch_size, ignore_conflicts=True)
            total_inserted += len(batch_list)
            print(f"   Inserted Batch {b_idx + 1}/{total_batches} ({total_inserted}/{needed_count})")

    final_count = MaterialRequest.objects.filter(requester=mirpur_user, status='Received').count()
    print(f"\nTotal 'Received' Material Requests for 'mirpur' Now: {final_count}")

    elapsed = time.time() - start_time
    print(f"Completed 3K Received Materials Population in {elapsed:.2f} seconds!")

if __name__ == '__main__':
    populate_mirpur_received()
