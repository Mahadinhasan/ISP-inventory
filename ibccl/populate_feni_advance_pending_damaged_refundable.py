import os
import sys
import django
import random
from django.utils import timezone
from datetime import timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import (
    Material, MaterialRequest, DamageMaterial,
    RefundableMaterial, RefundableMaterialUsage
)

def populate_feni_extra_data():
    print("=== Fetching User 'Feni' and Materials ===")
    try:
        feni_user = User.objects.get(username='Feni')
    except User.DoesNotExist:
        print("ERROR: User 'Feni' does not exist!")
        return

    all_materials = list(Material.objects.all()[:10000])
    if not all_materials:
        print("ERROR: No materials found in database!")
        return

    now = timezone.now()
    total_mats = len(all_materials)

    # -------------------------------------------------------------
    # 1. ADVANCE REQUESTS (5,000)
    # -------------------------------------------------------------
    print("\n1/5. Generating 5,000 Advance Material Requests for 'Feni'...")
    advance_requests = []
    for i in range(1, 5001):
        mat = all_materials[(i - 1) % total_mats]
        qty = random.randint(100, 500)
        rate = mat.rate or 120.0
        req_time = now - timedelta(days=random.randint(0, 20))
        
        req = MaterialRequest(
            material=mat,
            requester=feni_user,
            quantity=qty,
            rate=rate,
            total_price=round(qty * rate, 2),
            status='Approved',
            request_type='Advance',
            notes=f"Advance network emergency reserve request #{i:04d}",
            send_by='Feni Branch Team Lead',
            admin_note='Authorized by Admin for Advance Buffer',
            requested_at=req_time,
            is_archived=False,
            is_hidden_by_admin=False,
            is_hidden_by_noc=False
        )
        advance_requests.append(req)

    created_advance = MaterialRequest.objects.bulk_create(advance_requests, batch_size=1000)
    print(f"   ✓ Created {len(created_advance):,} Advance Requests!")

    # -------------------------------------------------------------
    # 2. PENDING REQUESTS (5,000)
    # -------------------------------------------------------------
    print("\n2/5. Generating 5,000 Pending Material Requests for 'Feni'...")
    pending_requests = []
    for i in range(1, 5001):
        mat = all_materials[(i + 2500) % total_mats]
        qty = random.randint(50, 300)
        rate = mat.rate or 120.0
        req_time = now - timedelta(hours=random.randint(1, 72))
        
        req = MaterialRequest(
            material=mat,
            requester=feni_user,
            quantity=qty,
            rate=rate,
            total_price=round(qty * rate, 2),
            status='Pending',
            request_type='Regular',
            notes=f"Routine expansion stock requisition #{i:04d}",
            send_by='Feni Field Engineer',
            requested_at=req_time,
            is_archived=False,
            is_hidden_by_admin=False,
            is_hidden_by_noc=False
        )
        pending_requests.append(req)

    created_pending = MaterialRequest.objects.bulk_create(pending_requests, batch_size=1000)
    print(f"   ✓ Created {len(created_pending):,} Pending Requests!")

    # -------------------------------------------------------------
    # 3. LOW STOCK MATERIALS (1,000)
    # -------------------------------------------------------------
    print("\n3/5. Setting 1,000 Materials to 'Low Stock'...")
    low_stock_ids = [m.id for m in all_materials[:1000]]
    updated_low = Material.objects.filter(id__in=low_stock_ids).update(
        quantity=15,
        Remaining_stock=15,
        min_stock_level=100,
        status='Low Stock'
    )
    print(f"   ✓ Updated {updated_low:,} Materials to 'Low Stock' (Qty: 15, Min: 100)!")

    # -------------------------------------------------------------
    # 4. REFUNDABLE MATERIALS (1,000) & USAGES (5,000)
    # -------------------------------------------------------------
    print("\n4/5. Generating 1,000 Refundable Materials & 5,000 Usages for 'Feni'...")
    refundable_items = []
    for i in range(1, 1001):
        mat = all_materials[i % total_mats]
        ref = RefundableMaterial(
            branch_user=feni_user,
            material_name=f"Refundable {mat.name[:80]} #{i:04d}",
            mac_serial=f"FENI-REF-{i:06d}",
            quantity=100,
            added_at=now - timedelta(days=random.randint(1, 30))
        )
        refundable_items.append(ref)

    created_refs = RefundableMaterial.objects.bulk_create(refundable_items, batch_size=500)
    print(f"   ✓ Created {len(created_refs):,} Refundable Material headers!")

    # Generate 5,000 Usages across the created refundable materials
    ref_list = list(RefundableMaterial.objects.filter(branch_user=feni_user)[:1000])
    usages = []
    zones = ["Feni Sadar", "Chhagalnaiya", "Daganbhuiyan", "Parshuram", "Fulgazi", "Sonagazi"]
    
    for i in range(1, 5001):
        ref_parent = ref_list[(i - 1) % len(ref_list)]
        usage_time = now - timedelta(days=random.randint(0, 20), hours=random.randint(0, 23))
        zone = zones[i % len(zones)]
        
        u = RefundableMaterialUsage(
            refundable_material=ref_parent,
            used_by=feni_user,
            materials_quantity=random.choice([1, 2, 5, 10]),
            client_name=f"Refundable Client #{i:04d}",
            client_address=f"Holding #{i % 300}, {zone}, Feni",
            client_phone=f"0182{random.randint(1000000, 9999999)}",
            dispatched_to=f"{zone} Network POP",
            issue=f"Temporary replacement deployment during line repair #{i:05d}",
            used_at=usage_time
        )
        usages.append(u)

    created_usages = RefundableMaterialUsage.objects.bulk_create(usages, batch_size=1000)
    print(f"   ✓ Created {len(created_usages):,} Refundable Material Usages!")

    # -------------------------------------------------------------
    # 5. DAMAGE MATERIALS (500)
    # -------------------------------------------------------------
    print("\n5/5. Generating 500 Damaged Materials for 'Feni'...")
    damage_reasons = [
        "Thunderbolt / Power surge burnt optical module",
        "Physical core rupture due to external road construction",
        "Water ingress inside joint enclosure during flood",
        "Overheating and hardware optical chipset failure",
        "Dropped from telecom pole during emergency maintenance"
    ]
    
    damage_records = []
    for i in range(1, 501):
        mat = all_materials[(i * 3) % total_mats]
        dmg_time = now - timedelta(days=random.randint(0, 15), hours=random.randint(0, 23))
        reason = damage_reasons[i % len(damage_reasons)]
        
        dmg = DamageMaterial(
            branch_user=feni_user,
            material=mat,
            quantity=random.randint(1, 8),
            damage_reason=f"{reason} (Incident Log #{i:04d})",
            status=random.choice(['Pending', 'Confirmed']),
            admin_note="Damage inspected and logged by Feni regional NOC technician.",
            added_at=dmg_time
        )
        damage_records.append(dmg)

    created_damages = DamageMaterial.objects.bulk_create(damage_records, batch_size=500)
    print(f"   ✓ Created {len(created_damages):,} Damaged Material entries!")

    print("\n=======================================================")
    print("ALL FENI BRANCH DATA POPULATED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == '__main__':
    populate_feni_extra_data()
