import os
import django
import time
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest, MacSerialNumber, UsedMaterial, DamageMaterial
import django.db.models


def populate_feni_used_damaged():
    print("=== Feni Branch: Used & Damaged Materials Population ===")
    start_time = time.time()

    feni_user = User.objects.get(username='feni')

    # Get feni's received non-Internet materials (storekeeper materials)
    received_reqs = list(
        MaterialRequest.objects.filter(
            requester=feni_user,
            status='Received',
        ).exclude(material__category='Internet')
        .select_related('material')
    )
    print(f"   Found {len(received_reqs)} received storekeeper requests for feni.")

    if len(received_reqs) < 10:
        print("   ERROR: Not enough received materials found! Run populate_feni_branch_data.py first.")
        return

    # ================================================================
    # PART 1: 1,500 UsedMaterial records (status='Accepted')
    # ================================================================
    print("\n1/2. Creating 1,500 UsedMaterial records...")

    client_names = [
        "Rahim Uddin", "Karim Ahmed", "Sohel Rana", "Nasrin Begum", "Faruk Hossain",
        "Rubi Akter", "Jakir Hosen", "Salma Khatun", "Belal Ahmed", "Mitu Begum",
        "Sirajul Islam", "Fatema Begum", "Mosharraf Hossain", "Laila Arjumand", "Delwar Hossain",
    ]
    client_addresses = [
        "Feni Sadar, Feni", "Daganbhuiyan, Feni", "Chhagalnaiya, Feni",
        "Sonagazi, Feni", "Parshuram, Feni", "Fulgazi, Feni",
        "Mirsarai, Chittagong", "Companiganj, Noakhali",
    ]
    issues = [
        "Client internet disconnected", "Router replacement needed",
        "Cable damage", "ONU device faulty", "New connection installation",
        "Fiber cut repair", "Splitter replacement", "Speed issue resolved",
        "Power issue - UPS replacement", "Device upgrade",
    ]

    qty_choices = [1, 1, 1, 2, 2, 3, 5, 10]

    # Shuffle and pick materials with enough quantity
    random.shuffle(received_reqs)
    used_batch = []
    for i in range(1500):
        req = received_reqs[i % len(received_reqs)]
        qty = random.choice(qty_choices)
        days_ago = random.randint(0, 25)
        used_batch.append(UsedMaterial(
            technician=feni_user,
            material=req.material,
            material_request=req,
            client_name=random.choice(client_names),
            client_address=random.choice(client_addresses),
            client_phone=f"017{random.randint(10000000, 99999999)}",
            quantity=qty,
            issue=random.choice(issues),
            status='Accepted',
            admin_note="Auto-generated field work record",
            added_at=timezone.now() - timezone.timedelta(days=days_ago),
        ))

    UsedMaterial.objects.bulk_create(used_batch, batch_size=500)
    print(f"   Created 1,500 UsedMaterial records (status=Accepted) for Feni!")

    # ================================================================
    # PART 2: 200 DamageMaterial records (status='Confirmed')
    # ================================================================
    print("\n2/2. Creating 200 DamageMaterial records (status=Confirmed)...")

    damage_reasons = [
        "Physical damage during installation",
        "Water damage due to flooding",
        "Lightning strike - device burned",
        "Accidental cable cut",
        "Rodent damage to cable",
        "Overheating - device failure",
        "Manufacturing defect",
        "Vandalism by third party",
        "Short circuit damage",
        "Falling from height during work",
    ]

    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.filter(is_superuser=True).first()

    # Also get Internet/NOC materials for damage reports
    noc_reqs = list(
        MaterialRequest.objects.filter(
            requester=feni_user,
            status='Received',
            material__category='Internet'
        ).select_related('material')
    )
    all_reqs = received_reqs + noc_reqs
    random.shuffle(all_reqs)

    damage_batch = []
    for i in range(200):
        req = all_reqs[i % len(all_reqs)]
        qty = random.randint(1, 3)
        days_ago = random.randint(1, 20)
        confirmed_days = random.randint(0, days_ago)

        # For NOC/Internet materials, optionally add MAC serial object
        mac_serial_obj = None
        if req.material.category == 'Internet':
            mac_serial_obj = MacSerialNumber.objects.filter(
                assigned_to=feni_user,
                material=req.material,
                status='Active'
            ).first()

        damage_batch.append(DamageMaterial(
            branch_user=feni_user,
            material=req.material,
            quantity=qty,
            damage_reason=random.choice(damage_reasons),
            status='Confirmed',
            admin_note="Damage confirmed by admin after field inspection",
            added_at=timezone.now() - timezone.timedelta(days=days_ago),
            confirmed_at=timezone.now() - timezone.timedelta(days=confirmed_days),
            confirmed_by=admin_user,
        ))

    DamageMaterial.objects.bulk_create(damage_batch, batch_size=200)
    print(f"   Created 200 DamageMaterial records (status=Confirmed) for Feni!")

    # ================================================================
    # SUMMARY
    # ================================================================
    total_used = UsedMaterial.objects.filter(technician=feni_user, status='Accepted').count()
    total_dmg = DamageMaterial.objects.filter(branch_user=feni_user, status='Confirmed').count()

    print("\n================ SUCCESS SUMMARY ================")
    print(f"  UsedMaterial  (Accepted)  : {total_used:,}")
    print(f"  DamageMaterial (Confirmed) : {total_dmg:,}")
    print(f"  Completed in              : {time.time() - start_time:.2f}s")
    print("=================================================")


if __name__ == '__main__':
    populate_feni_used_damaged()
