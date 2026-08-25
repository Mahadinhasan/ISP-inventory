import os
import django
import random
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest, UsedMaterial

def populate_feni_used_materials():
    print("=== Step 1: Fetching User 'Feni' and Materials ===")
    try:
        feni_user = User.objects.get(username='Feni')
    except User.DoesNotExist:
        print("ERROR: User 'Feni' does not exist!")
        return

    # Fetch Feni's received requests & materials
    feni_requests = list(MaterialRequest.objects.filter(requester=feni_user, status='Received').select_related('material')[:10000])
    if not feni_requests:
        print("No received requests found for Feni. Fetching general materials...")
        all_materials = list(Material.objects.all()[:10000])
        feni_requests = [None] * len(all_materials)
    else:
        all_materials = [r.material for r in feni_requests]

    total_mats = len(all_materials)
    print(f"Materials available for Feni usage: {total_mats:,}")

    target_count = 30000
    print(f"\n=== Step 2: Generating {target_count:,} UsedMaterial Records for 'Feni' ===")
    
    quantities_pool = [10, 20, 30, 40, 50]
    issues = [
        "New broadband client installation",
        "Fiber line extension and splicing",
        "Corporate optical link setup",
        "POP server room maintenance",
        "Core distribution switch replacement",
        "Network outage emergency repair",
        "Home optical network ONU deployment",
        "Local branch infrastructure upgrade"
    ]
    
    zones = ["Feni Sadar", "Chhagalnaiya", "Daganbhuiyan", "Parshuram", "Fulgazi", "Sonagazi", "Trunk Road Hub", "Grand Trunk Zone"]
    
    used_records = []
    now = timezone.now()
    
    for i in range(1, target_count + 1):
        mat_idx = (i - 1) % total_mats
        mat = all_materials[mat_idx]
        req = feni_requests[mat_idx] if mat_idx < len(feni_requests) else None
        
        qty = random.choice(quantities_pool)
        issue = issues[i % len(issues)]
        zone = zones[i % len(zones)]
        client_num = (i % 5000) + 1
        
        # Stagger added_at across the past 30 days
        days_ago = random.randint(0, 25)
        added_time = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        used_entry = UsedMaterial(
            technician=feni_user,
            material=mat,
            material_request=req,
            client_name=f"Feni Client #{client_num:04d}",
            client_address=f"Holding #{client_num}, {zone}, Feni",
            client_phone=f"0181{random.randint(1000000, 9999999)}",
            dispatched_to=f"{zone} Network Sector",
            quantity=qty,
            issue=f"{issue} (Job #{i:05d})",
            status='Accepted',
            admin_note="Approved & verified by Store Admin",
            added_at=added_time,
            updated_at=added_time,
            is_archived=False,
            is_pop_entry=(i % 10 == 0)
        )
        used_records.append(used_entry)

    print(f"Bulk inserting {len(used_records):,} records into database...")
    created = UsedMaterial.objects.bulk_create(used_records, batch_size=2000)
    
    print(f"\n=== SUCCESS: {len(created):,} Used Materials Created for 'Feni' ===")
    
    # Summary
    from django.db.models import Sum, Count
    feni_usage = UsedMaterial.objects.filter(technician=feni_user).aggregate(
        total_qty=Sum('quantity'),
        total_entries=Count('id')
    )
    print(f"Feni Total Used Entries : {feni_usage['total_entries']:,}")
    print(f"Feni Total Units Used   : {feni_usage['total_qty']:,} units")
    print(f"Quantities breakdown   : 10, 20, 30, 40, 50 units randomly distributed")

if __name__ == '__main__':
    populate_feni_used_materials()
