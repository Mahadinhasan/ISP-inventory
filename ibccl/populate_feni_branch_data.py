import os
import django
import time
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest, MacSerialNumber, UserProfile
import django.db.models


def populate_feni():
    print("=== Starting Feni Branch (user: feni) Data Population ===")
    start_time = time.time()

    # --- Users setup ---
    feni_user, _ = User.objects.get_or_create(username='feni', defaults={'email': 'feni@isp.com'})
    feni_user.set_password('Admin123@')
    feni_user.is_active = True
    feni_user.save()

    feni_prof, _ = UserProfile.objects.get_or_create(user=feni_user, defaults={'role': 'Branch'})
    feni_prof.role = 'Branch'
    feni_prof.save()

    try:
        noc_user = User.objects.get(username='noc')
    except User.DoesNotExist:
        noc_user = User.objects.filter(is_superuser=True).first()

    try:
        store_user = User.objects.get(username='store')
    except User.DoesNotExist:
        store_user = User.objects.filter(is_superuser=True).first()

    print(f"User 'feni' ready | NOC: {noc_user.username} | Store: {store_user.username}")

    # Clean old feni data
    MaterialRequest.objects.filter(requester=feni_user).delete()
    MacSerialNumber.objects.filter(assigned_to=feni_user).delete()
    print("   Cleaned old feni data.")

    # ================================================================
    # PART 1: NOC 2,000 MAC/Serial Numbers (5 Internet materials × 400)
    # ================================================================
    print("\n1/2. Creating 2,000 MAC/Serial NOC Received Materials...")

    noc_mat_names = [
        "Feni NOC ONU Dual Band GPON",
        "Feni NOC Core Router 10G",
        "Feni NOC Media Converter 20KM",
        "Feni NOC SFP Transceiver 10G",
        "Feni NOC Switch 24 Port Gigabit",
    ]
    noc_materials = []
    for name in noc_mat_names:
        mat, _ = Material.objects.get_or_create(
            name=name,
            defaults={
                'category': 'Internet',
                'quantity': 10000,
                'min_stock_level': 50,
                'rate': 2500,
                'total_price': 25000000,
                'created_by': noc_user,
                'Type': 'Piece',
            }
        )
        noc_materials.append(mat)

    mac_batch = []
    counter = 1
    for mat in noc_materials:
        for _ in range(400):
            mac_batch.append(MacSerialNumber(
                mac_serial=f"MAC-FENI-{counter:05d}",
                material=mat,
                assigned_to=feni_user,
                status='Active',
                added_by=noc_user,
            ))
            counter += 1

        MaterialRequest.objects.create(
            requester=feni_user,
            material=mat,
            quantity=400,
            rate=mat.rate or 2500,
            total_price=400 * (mat.rate or 2500),
            status='Received',
            request_type='Advance',
            received_by=feni_user.username,
            received_at=timezone.now() - timezone.timedelta(days=random.randint(1, 15)),
            admin_note="NOC Approved 400 Devices for Feni Branch",
        )

    MacSerialNumber.objects.bulk_create(mac_batch, batch_size=1000)
    print("   NOC: 5 requests × 400 qty = 2,000 | MACs created: 2,000")

    # ================================================================
    # PART 2: 3,000 requests from EXISTING Admin/Storekeeper materials
    #         with varied quantities: 50, 75, 100, 125, 150, 200
    # ================================================================
    print("\n2/2. Creating 3,000 requests from EXISTING Admin/Storekeeper materials...")

    # Pick 3,000 unique non-Internet existing materials
    all_store_mats = list(
        Material.objects.filter(is_deleted=False)
        .exclude(category='Internet')
        .values_list('id', 'rate')
    )
    print(f"   Found {len(all_store_mats)} existing non-Internet materials in DB.")

    random.shuffle(all_store_mats)
    picked = all_store_mats[:3000]

    qty_pool = [50, 50, 75, 75, 100, 100, 100, 125, 150, 150, 200]

    req_batch = []
    for mat_id, mat_rate in picked:
        qty = random.choice(qty_pool)
        rate = mat_rate or 1500
        days_pass = random.randint(5, 30)
        days_recv = random.randint(1, min(days_pass, 10))
        req_batch.append(MaterialRequest(
            requester=feni_user,
            material_id=mat_id,
            quantity=qty,
            rate=rate,
            total_price=qty * rate,
            status='Received',
            request_type='Regular',
            pass_on='Storekeeper Dispatched Main Warehouse',
            pass_on_at=timezone.now() - timezone.timedelta(days=days_pass),
            received_by=feni_user.username,
            received_at=timezone.now() - timezone.timedelta(days=days_recv),
            admin_note=f"Storekeeper dispatched {qty} units to Feni Branch",
        ))

    MaterialRequest.objects.bulk_create(req_batch, batch_size=500)
    print(f"   Storekeeper: {len(req_batch)} requests | Total Qty: {sum(r.quantity for r in req_batch)}")

    # ================================================================
    # SUMMARY
    # ================================================================
    noc_reqs = MaterialRequest.objects.filter(requester=feni_user, status='Received', material__category='Internet')
    store_reqs = MaterialRequest.objects.filter(requester=feni_user, status='Received').exclude(material__category='Internet')
    total_noc_qty = noc_reqs.aggregate(s=django.db.models.Sum('quantity'))['s'] or 0
    total_store_qty = store_reqs.aggregate(s=django.db.models.Sum('quantity'))['s'] or 0
    total_macs = MacSerialNumber.objects.filter(assigned_to=feni_user, status='Active').count()

    print("\n================ SUCCESS SUMMARY FOR FENI BRANCH ================")
    print(f"  Username : feni | Password : Admin123@")
    print(f"  NOC Received Qty    : {total_noc_qty:,} items ({noc_reqs.count()} requests)")
    print(f"  Active MACs         : {total_macs:,}")
    print(f"  Storekeeper Qty     : {total_store_qty:,} items ({store_reqs.count()} requests)")
    print(f"  GRAND TOTAL Qty     : {total_noc_qty + total_store_qty:,} items")
    print(f"  Completed in        : {time.time() - start_time:.2f}s")
    print("=================================================================")


if __name__ == '__main__':
    populate_feni()
