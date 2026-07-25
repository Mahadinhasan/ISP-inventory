import os
import sys
import django
import time
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MacSerialNumber, MaterialMacSerialImport, MaterialRequest

def populate_noc_mac_serials():
    print("=== Starting 2,000 (2K) NOC MAC/Serial Materials Population for 'mirpur' Branch ===")
    start_time = time.time()

    # Reference Users
    try:
        noc_user = User.objects.get(username='noc')
    except User.DoesNotExist:
        print("ERROR: User 'noc' not found!")
        return

    try:
        mirpur_user = User.objects.get(username='mirpur')
    except User.DoesNotExist:
        print("ERROR: User 'mirpur' not found!")
        return

    # Fetch/Ensure NOC / Internet Materials
    noc_materials = list(Material.objects.filter(category='Internet'))
    if not noc_materials:
        print("No 'Internet' category materials found. Creating NOC materials...")
        noc_materials = [
            Material.objects.create(name="ZTE Dual Band ONU Router", category="Internet", Type="Piece", quantity=5000, rate=2500, total_price=12500000, created_by=noc_user),
            Material.objects.create(name="Huawei OptiXstar ONU", category="Internet", Type="Piece", quantity=5000, rate=2800, total_price=14000000, created_by=noc_user),
            Material.objects.create(name="Tenda Fiber ONU Box", category="Internet", Type="Piece", quantity=5000, rate=1800, total_price=9000000, created_by=noc_user),
            Material.objects.create(name="FiberHome Gigabit SFP Module", category="Internet", Type="Piece", quantity=5000, rate=1200, total_price=6000000, created_by=noc_user)
        ]

    target_count = 2000
    existing_count = MacSerialNumber.objects.filter(added_by=noc_user, assigned_to=mirpur_user).count()
    print(f"Current MAC/Serial count for 'mirpur' added by NOC: {existing_count}")

    needed_count = max(0, target_count - existing_count)

    if needed_count > 0:
        print(f"Generating {needed_count} new MAC/Serial numbers...")

        mac_list = []
        batch_size = 1000
        start_counter = existing_count + 1

        mac_prefixes = ["C4:AD:34", "BC:A5:11", "00:1E:67", "D8:07:B6", "F4:8E:38"]

        for i in range(needed_count):
            counter_val = start_counter + i
            mat = random.choice(noc_materials)
            prefix = random.choice(mac_prefixes)
            mac_str = f"{prefix}:{random.randint(10,99):02X}:{random.randint(10,99):02X}:{counter_val:04X}"
            
            # Ensure unique mac_serial name
            mac_serial_code = f"MAC-NOC-{counter_val:05d}-{mac_str}"

            mac_list.append(MacSerialNumber(
                material=mat,
                mac_serial=mac_serial_code,
                quantity=1,
                assigned_to=mirpur_user,
                status='Active',
                is_ever_accepted=True,
                added_by=noc_user
            ))

        MacSerialNumber.objects.bulk_create(mac_list, batch_size=batch_size, ignore_conflicts=True)
        print(f"   Inserted {len(mac_list)} MAC/Serial entries for 'mirpur'!")

    final_mac_count = MacSerialNumber.objects.filter(added_by=noc_user, assigned_to=mirpur_user).count()
    print(f"\nTotal MAC/Serial Numbers for 'mirpur' Added by NOC: {final_mac_count}")

    # Also create NOC MaterialRequests with Received status
    print("\nCreating NOC Material Requests with 'Received' status for 'mirpur'...")
    noc_reqs = []
    for idx, mat in enumerate(noc_materials):
        noc_reqs.append(MaterialRequest(
            requester=mirpur_user,
            material=mat,
            quantity=500,
            rate=mat.rate,
            total_price=500 * mat.rate,
            status='Received',
            request_type='Regular',
            pass_on='NOC Team Dispatched',
            pass_on_at=timezone.now(),
            received_by='mirpur',
            received_at=timezone.now(),
            admin_note=f"2K MAC/Serial Material Allocation #{idx+1}"
        ))
    MaterialRequest.objects.bulk_create(noc_reqs, ignore_conflicts=True)
    print(f"Created NOC Material Requests with status 'Received'.")

    elapsed = time.time() - start_time
    print(f"\nCompleted 2K NOC MAC/Serial Materials Population in {elapsed:.2f} seconds!")

if __name__ == '__main__':
    populate_noc_mac_serials()
