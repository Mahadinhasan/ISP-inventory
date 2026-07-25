import os
import sys
import django
import time
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import (
    Material, MaterialRequest, UsedMaterial, DamageMaterial, 
    RefundableMaterial, RefundableMaterialUsage, MacSerialNumber, 
    ActivityLog, InternalMessage, UserProfile
)

def populate_highest_traffic():
    print("=== Starting HIGHEST TRAFFIC LOAD Population across ALL 21 Branch Users ===")
    start_time = time.time()

    # 1. Fetch reference users
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

    # Fetch all branch users
    branch_profiles = UserProfile.objects.filter(role='Branch').select_related('user')
    branch_users = [p.user for p in branch_profiles]
    if not branch_users:
        print("ERROR: No branch users found!")
        return

    print(f"Active Branch Users Found: {len(branch_users)}")

    all_materials = list(Material.objects.all())
    if not all_materials:
        print("ERROR: No materials found in database!")
        return

    print(f"Total Materials Available for Distribution: {len(all_materials)}")

    # 2. MaterialRequests: Distribute Received & Active Requests for ALL 21 Branches
    print("\n1/5. Distributing Received & Active Material Requests to ALL Branches...")
    req_batch = []
    statuses = ['Received', 'Approved', 'Dispatched', 'Pending']

    for b_user in branch_users:
        # Create 150 Received requests per branch
        for i in range(150):
            mat = random.choice(all_materials)
            qty = random.randint(10, 100)
            rate = mat.rate or random.randint(100, 3000)

            req_batch.append(MaterialRequest(
                requester=b_user,
                material=mat,
                quantity=qty,
                rate=rate,
                total_price=qty * rate,
                status='Received',
                request_type=random.choice(['Regular', 'Advance']),
                pass_on='Storekeeper Dispatched Main Warehouse',
                pass_on_at=timezone.now(),
                received_by=b_user.username,
                received_at=timezone.now(),
                admin_note=f"Full Distribution Batch #{i+1}"
            ))

    MaterialRequest.objects.bulk_create(req_batch, batch_size=2000, ignore_conflicts=True)
    print(f"   Created {len(req_batch)} Material Requests across all branches!")

    # 3. UsedMaterials: Populate Used Material Records (Accepted, Pending, Rejected)
    print("\n2/5. Populating Used Material Records for ALL Branches...")
    used_batch = []
    clients = [
        'Standard Chartered Bank', 'Labaid Hospital', 'Grameenphone POP', 'Robic Tower', 
        'Apex Footwear HQ', 'Square Pharmaceuticals', 'Dhaka Bank Branch', 'City Group Office',
        'Abul Khair Group', 'Hamdard Bangladesh', 'Rahimafrooz Center', 'BEXIMCO Complex'
    ]
    issues = [
        'New Line Installation', 'Fiber Cut Repair Work', 'ONU Upgrade to Dual Band', 
        'Media Converter Replacement', 'SFP Module Swap', 'Switch Replacement 24 Port',
        'Drop Wire Splice Work', 'Patch Cable Routing'
    ]
    used_statuses = ['Accepted', 'Pending', 'Rejected']

    for b_user in branch_users:
        for i in range(200):
            mat = random.choice(all_materials)
            qty = random.randint(1, 8)
            st = random.choice(used_statuses)

            used_batch.append(UsedMaterial(
                technician=b_user,
                material=mat,
                client_name=random.choice(clients),
                client_address=f"Plot #{random.randint(1,150)}, Road #{random.randint(1,30)}, Dhaka",
                client_phone=f"0171{random.randint(1000000, 9999999)}",
                quantity=qty,
                issue=random.choice(issues),
                status=st,
                admin_note="Traffic load test used material entry"
            ))

    UsedMaterial.objects.bulk_create(used_batch, batch_size=2000, ignore_conflicts=True)
    print(f"   Created {len(used_batch)} Used Material entries across all branches!")

    # 4. DamageMaterials: Populate Damage Material Records (Pending, Confirmed, Rejected)
    print("\n3/5. Populating Damaged Material Records for ALL Branches...")
    damage_batch = []
    damage_reasons = [
        'Thunderstorm High Voltage Lightning Spike', 'Overhead Cable Snapped by Truck',
        'Physical Water Submersion during Flood', 'ONU Adapter Burnout', 'Optical Receiver Fiber Core Cut'
    ]
    damage_statuses = ['Pending', 'Confirmed', 'Rejected']

    for b_user in branch_users:
        for i in range(40):
            mat = random.choice(all_materials)
            qty = random.randint(1, 5)
            st = random.choice(damage_statuses)

            damage_batch.append(DamageMaterial(
                branch_user=b_user,
                material=mat,
                quantity=qty,
                damage_reason=random.choice(damage_reasons),
                status=st,
                admin_note="Damage report load test entry"
            ))

    DamageMaterial.objects.bulk_create(damage_batch, batch_size=1000, ignore_conflicts=True)
    print(f"   Created {len(damage_batch)} Damaged Material entries across all branches!")

    # 5. RefundableMaterials & Usages: Returnable items for ALL Branches
    print("\n4/5. Populating Refundable & Returnable Materials for ALL Branches...")
    ref_batch = []
    returnable_names = [
        "ONU Router Dual Band Model-Z", "Optical Power Meter Pro", "Media Converter 20KM Gigabit",
        "Fiber Fusion Protection Box", "SFP Transceiver 10G Module", "VFL Red Laser Tester"
    ]

    for b_user in branch_users:
        for r_name in returnable_names:
            ref_batch.append(RefundableMaterial(
                branch_user=b_user,
                material_name=r_name,
                mac_serial=f"SN-REF-{b_user.username[:4].upper()}-{random.randint(10000,99999)}",
                quantity=random.randint(10, 50)
            ))

    RefundableMaterial.objects.bulk_create(ref_batch, batch_size=1000, ignore_conflicts=True)
    print(f"   Created {len(ref_batch)} Refundable Material entries across all branches!")

    # Populate Refundable Material Usages
    ref_items = list(RefundableMaterial.objects.all())
    usage_batch = []
    for r_item in ref_items[:800]:
        usage_batch.append(RefundableMaterialUsage(
            refundable_material=r_item,
            used_by=r_item.branch_user,
            materials_quantity=random.randint(1, 3),
            client_name="Commercial Office POP",
            client_address="Main Road Commercial Area",
            client_phone="01819000000",
            issue="Temporary Returnable Device Usage"
        ))

    RefundableMaterialUsage.objects.bulk_create(usage_batch, batch_size=1000, ignore_conflicts=True)
    print(f"   Created {len(usage_batch)} Refundable Material Usage entries!")

    # 6. Activity Logs & Messages: Populate Activity Logs
    print("\n5/5. Generating System Activity Logs & Internal Messages...")
    logs_batch = []
    msg_batch = []
    act_types = ['login', 'create', 'update', 'approve', 'other']

    for b_user in branch_users:
        for _ in range(15):
            logs_batch.append(ActivityLog(
                user=b_user,
                activity_type=random.choice(act_types),
                description=f"Branch user {b_user.username} performed system operation",
                ip_address=f"192.168.1.{random.randint(2, 254)}"
            ))
            msg_batch.append(InternalMessage(
                sender=b_user,
                receiver=store_user,
                content=f"Hello Storekeeper, branch {b_user.username} requires dispatch verification.",
                is_read=True
            ))

    ActivityLog.objects.bulk_create(logs_batch, batch_size=1000, ignore_conflicts=True)
    InternalMessage.objects.bulk_create(msg_batch, batch_size=1000, ignore_conflicts=True)
    print(f"   Created {len(logs_batch)} Activity Logs and {len(msg_batch)} Internal Messages!")

    elapsed = time.time() - start_time
    print(f"\nCOMPLETED HIGHEST TRAFFIC LOAD POPULATION in {elapsed:.2f} seconds!")

if __name__ == '__main__':
    populate_highest_traffic()
