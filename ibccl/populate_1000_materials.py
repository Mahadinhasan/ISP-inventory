import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material

def create_materials():
    admin_user = User.objects.filter(username__in=['admin', 'admin1']).first()
    if not admin_user:
        admin_user = User.objects.first()

    categories = ['Fiber', 'Internet', 'Dish', 'Common item', 'Work shop']
    types_map = {
        'Fiber': 'Meter',
        'Internet': 'Piece',
        'Dish': 'Piece',
        'Common item': 'Piece',
        'Work shop': 'Piece'
    }

    base_names = [
        "Fiber Optical Cable Core", "Patch Cord SC-LC", "ONU XPON Gigabit Router", 
        "Optical Distribution Frame", "SFP Transceiver 1.25G", "SFP+ 10G Module",
        "Micro Splitter 1:8 PLC", "Cassette Splitter 1:16", "Fusion Splice Protection Sleeve",
        "RJ45 Cat6 UTP Cable Roll", "Modular Plug Connector RJ45", "Fast Connector SC/UPC",
        "Fast Connector SC/APC", "Drop Cable Clamp Fastener", "Fiber Joint Closure Dome Type",
        "OLT EPON 8-Port Switch", "OLT GPON 16-Port Chassis", "Media Converter 10/100/1000M",
        "VLAN Managed Switch 24-Port", "POE Switch 8-Port Gigabit", "Outdoor Waterproof Enclosure Box",
        "Fiber Cleaver Precision Blade", "Optical Power Meter Tester", "Visual Fault Locator 10mW",
        "Cat6 Patch Panel 24-Port", "Server Rack 42U Ground Standing", "Mini Wallmount Rack 9U",
        "Coaxial Cable RG6 Roll", "BNC Connector Male", "Dish Receiver HD Digital",
        "LNB Universal Single Output", "Splitter 2-Way TV Signal", "Amplifier RF Inline 20dB",
        "Power Adapter 12V 2A DC", "Power Supply Unit 48V Telecom", "UPS 1200VA Offline Backup",
        "Crimping Tool Network Heavy Duty", "Wire Stripper Multi-function", "Cable Tie Nylon 200mm",
        "Heat Shrink Tube 4mm", "Galvanized Steel Suspension Clamp", "Dead End Guy Grip Clamp"
    ]

    materials_to_create = []
    
    # We will generate 1,000 uniquely named materials
    item_count = 1000
    quantity_per_item = 50000
    
    print(f"Generating {item_count} materials with {quantity_per_item:,} quantity each...")
    
    for i in range(1, item_count + 1):
        base = base_names[(i - 1) % len(base_names)]
        batch_num = ((i - 1) // len(base_names)) + 1
        
        if batch_num == 1:
            name = f"{base} (Model #{i:04d})"
        else:
            name = f"{base} Series-B{batch_num} #{i:04d}"
            
        cat = categories[i % len(categories)]
        mtype = types_map.get(cat, 'Piece')
        rate = round(random.uniform(50.0, 850.0), 2)
        total_price = round(quantity_per_item * rate, 2)
        
        mat = Material(
            name=name,
            category=cat,
            Type=mtype,
            quantity=quantity_per_item,
            rate=rate,
            total_price=total_price,
            Remaining_stock=quantity_per_item,
            min_stock_level=500,
            status='Normal',
            notes=f"Batch generated inventory material #{i} with initial 50,000 units.",
            created_by=admin_user,
            is_deleted=False
        )
        materials_to_create.append(mat)

    # Bulk create in batches of 500
    created = Material.objects.bulk_create(materials_to_create, batch_size=500, ignore_conflicts=True)
    print(f"Successfully created {len(created)} materials in database!")
    print(f"Total Materials in DB: {Material.objects.count():,}")

if __name__ == '__main__':
    create_materials()
