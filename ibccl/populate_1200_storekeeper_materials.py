import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, UserProfile

def create_storekeeper_materials():
    storekeepers = list(User.objects.filter(userprofile__role='Storekeeper'))
    if not storekeepers:
        print("No storekeeper users found. Creating fallback storekeeper user...")
        user, _ = User.objects.get_or_create(username='store1', defaults={'email': 'store1@ibccl.com'})
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = 'Storekeeper'
        profile.save()
        storekeepers = [user]

    print(f"Active Storekeeper Users: {[u.username for u in storekeepers]}")

    categories = ['Fiber', 'Internet', 'Dish', 'Common item', 'Work shop']
    types_map = {
        'Fiber': 'Meter',
        'Internet': 'Piece',
        'Dish': 'Piece',
        'Common item': 'Piece',
        'Work shop': 'Piece'
    }

    base_names = [
        "Store Warehouse Cable Core", "Store SC-SC Simplex Cord", "Store Dual Band ONU Terminal",
        "Store Distribution Enclosure", "Store SFP BiDi Transceiver", "Store 10G DAC Twinax Cable",
        "Store PLC Splitter 1:4 Box", "Store PLC Splitter 1:32 Rack", "Store Protection Sleeves 60mm",
        "Store Cat6 FTP Shielded Cable", "Store RJ45 Pass-Through Plugs", "Store Fast Connector UPC Blue",
        "Store Fast Connector APC Green", "Store Drop Wire Tension Clamp", "Store Horizontal Joint Box",
        "Store OLT EPON 4-Port Fixed", "Store OLT GPON 8-Port Card", "Store Gigabit PoE Injector",
        "Store Core Switch 48-Port L3", "Store Desktop Switch 16-Port", "Store Stainless Steel Strapping Band",
        "Store High-Precision Optical Cleaver", "Store Mini Optical Power Meter", "Store Red Laser VFL 30mW",
        "Store 24-Port Cat6 Keystones", "Store Network Cabinet 15U", "Store Heavy Duty Wall Box 6U",
        "Store RG11 Coaxial Trunk Line", "Store F-Type Compression Connectors", "Store Digital Satellite Dish 90cm",
        "Store Quad Output LNB Feedhorn", "Store 4-Way RF Signal Splitter", "Store Distribution Trunk Amplifier",
        "Store Industrial Adapter 12V 5A", "Store Dual Output SMPS 48V", "Store Online Smart UPS 2kVA",
        "Store Ratchet Crimping Plier", "Store Fiber Stripping Pliers 3-Hole", "Store Stainless Cable Clips 100pk",
        "Store Cold Shrink Tube Waterproof", "Store Pole Mount Bracket Hook", "Store Fiber Cable Tensioner Grip"
    ]

    materials_to_create = []
    item_count = 1200
    
    print(f"Generating {item_count} materials created by Storekeepers...")
    
    for i in range(1, item_count + 1):
        base = base_names[(i - 1) % len(base_names)]
        batch_num = ((i - 1) // len(base_names)) + 1
        
        name = f"{base} SKU-SK{batch_num:02d}-{i:04d}"
        cat = categories[i % len(categories)]
        mtype = types_map.get(cat, 'Piece')
        qty = random.choice([500, 1000, 2500, 5000, 10000, 25000, 50000])
        rate = round(random.uniform(30.0, 750.0), 2)
        total_price = round(qty * rate, 2)
        creator = storekeepers[i % len(storekeepers)]
        
        mat = Material(
            name=name,
            category=cat,
            Type=mtype,
            quantity=qty,
            rate=rate,
            total_price=total_price,
            Remaining_stock=qty,
            min_stock_level=100,
            status='Normal',
            notes=f"Storekeeper warehouse stock entry #{i} managed by {creator.username}.",
            created_by=creator,
            is_deleted=False
        )
        materials_to_create.append(mat)

    created = Material.objects.bulk_create(materials_to_create, batch_size=500, ignore_conflicts=True)
    print(f"Successfully created {len(created)} storekeeper materials!")
    print(f"Total Materials in Database now: {Material.objects.count():,}")

if __name__ == '__main__':
    create_storekeeper_materials()
