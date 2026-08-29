import os
import sys
import random
from datetime import datetime
import django

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from isp_inventory.models import Material, MaterialRequest, UsedMaterial

def run_seed():
    print("Starting generation script...")
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.get(username='admin')
    feni_user = User.objects.get(username='Feni')
    
    print(f"Using Admin: {admin_user.username} (ID: {admin_user.id})")
    print(f"Using Branch User: {feni_user.username} (ID: {feni_user.id})")

    # Item name bases grouped by category
    CAT_TEMPLATES = {
        'Internet': {
            'type': 'Piece',
            'bases': [
                "Cat6 UTP Patch Cord 3M High Speed",
                "Cat6A STP Shielded Patch Cable 5M",
                "Fiber ONU GPON Router Dual-Band Gigabit",
                "XPON ONU 1GE+1FE WiFi Multi-Mode Router",
                "SFP Optical Transceiver 1.25G 20KM LC",
                "SFP+ 10G LR Single Mode Transceiver 10KM",
                "Media Converter 10/100/1000M Single Fiber",
                "Gigabit PoE Switch 8-Port + 2 SFP Uplink",
                "Managed Core Switch 24-Port Gigabit L2+",
                "Outdoor Wireless Access Point 5GHz AC1200",
                "Patch Cord SC-UPC to SC-UPC Single Mode 3M",
                "Patch Cord LC-UPC to LC-UPC Duplex 5M",
                "Fast Ethernet Switch 16-Port 10/100M Desktop",
                "High Gain 5dBi Dual Antenna Wireless Router",
                "VLAN Managed Layer-2 Access Switch 16-Port"
            ],
            'rates': (80.0, 1800.0)
        },
        'Fiber': {
            'type': 'Meter',
            'bases': [
                "Core Armored Optical Fiber Cable 24-Core G652D",
                "Core Aerial ADSS Fiber Optic Cable 12-Core Single Mode",
                "Core Drop Cable FTTH 2-Core Single Mode Steel",
                "Core Drop Cable FTTH 4-Core Steel Messenger Outdoor",
                "Core Ribbon Fiber Optic Cable 48-Core Trunk",
                "Fiber Joint Closure Dome 48-Core IP68 Waterproof",
                "Fiber Joint Box Inline 24-Core Waterproof Splicing",
                "PLC Optical Splitter 1:8 Cassette SC-APC",
                "PLC Optical Splitter 1:16 Mini Steel Tube SC-UPC",
                "PLC Optical Splitter 1:4 Box Type SC-UPC Insertion",
                "PLC Optical Splitter 1:32 Rack Mount 19-inch 1U",
                "Fiber Optical Distribution Frame ODF 24-Port Loaded",
                "Fiber Terminal Box 4-Port Wall Mount ABS",
                "FTTH Fiber Termination Socket 2-Port Faceplate",
                "Optical Time Domain Reflectometer Launch Cable Box 1KM"
            ],
            'rates': (25.0, 950.0)
        },
        'Dish': {
            'type': 'Piece',
            'bases': [
                "Coaxial Cable RG6 High Shielding 75-Ohm 300M Roll",
                "Coaxial Cable RG11 Trunk Cable 500M Wooden Drum",
                "CATV Amplifier Optical Receiver 860MHz AGC",
                "CATV Inline RF Trunk Amplifier 24V 30dB Gain",
                "CATV Two-Way Power Passing RF Splitter 2-Way 5-1000MHz",
                "CATV RF Splitter 3-Way Balanced High Isolation",
                "CATV RF Directional Coupler 4-Way Tap 12dB",
                "CATV RF Directional Coupler 8-Way Tap 16dB",
                "Optical Transmitter 1550nm CATV DFB Laser 10mW",
                "CATV Optical Node EDFA 1550nm 4-Port High Output",
                "F-Type Male RG6 Compression Crimp Connector Nickel",
                "F-Type RG11 Hardline Pin Connector CATV Waterproof",
                "CATV High Pass Filter 54-1000MHz Ground Isolator",
                "Satellite Dish Antenna 6-Foot Solid Prime Focus Heavy",
                "C-Band Single Polarity LNBF High Stability 5150MHz"
            ],
            'rates': (40.0, 2200.0)
        },
        'Common item': {
            'type': 'Piece',
            'bases': [
                "Heavy Duty Cable Tie 300x4.8mm UV Resistant Black Pack",
                "Nylon Cable Tie 200x3.6mm Industrial Grade Pack",
                "PVC Electrical Insulation Tape 20M Premium Flame Retardant",
                "Expansion Wall Anchor with Heavy Screw M6x40 Set",
                "Stainless Steel Drop Wire Dead-End Clamp Tensioner",
                "Suspension Hook J-Type Galvanized Pole Bracket Heavy",
                "Fiber Cable Suspension Clamp Aluminum Alloy Pole Fitting",
                "Waterproof Heat Shrink Tube 60mm with Internal Sealant",
                "Plastic Spiral Cable Wrap Protective Sleeve 10M",
                "Heavy Duty Cable Tray Perforated 100x50mm Galvanized",
                "Cable Number Marker Sleeve Clip 0-9 Set 1000pcs",
                "RJ45 Modular Plug Connector 8P8C Gold Plated Cat6 Box",
                "RJ45 Keystone Jack Toolless Cat6 UTP Snap-in",
                "Wall Mount Faceplate Single Port 86x86mm White Gloss",
                "Cable Management Rack Panel 1U 24-Slot Horizontal"
            ],
            'rates': (15.0, 350.0)
        },
        'Work shop': {
            'type': 'Piece',
            'bases': [
                "Precision Optical Fiber Cleaver High Precision FC-6S",
                "Fiber Optic Fusion Splicer Electrodes Replacement Pair",
                "FTTH Drop Cable Wire Stripper Double Hole Ergonomic",
                "Fiber Optic Miller Stripper 3-Hole Precision Tool",
                "Optical Power Meter -70 to +10dBm FC/SC Universal",
                "Visual Fault Locator Red Laser 30mW VFL Tester",
                "RJ45 RJ11 Modular Ratchet Crimping Tool Professional",
                "Heavy Duty Coaxial Cable Rotary Stripper RG6/11 Dual Blade",
                "Network Multi-function Cable Wire Tracker Tester RJ45",
                "Digital Multimeter True RMS Auto-Ranging 6000 Counts",
                "Rechargeable Cordless Impact Drill Kit 20V Lithium-Ion",
                "Heavy Duty Electric Hot Melt Glue Gun 100W Quick Heat",
                "Electric Rotary Blower Heavy Duty Dust Cleaner 600W",
                "Portable Fiber Optic Microscope Inspection Probe 400X",
                "Precision Screwdriver Toolkit 45-in-1 Magnetic Professional"
            ],
            'rates': (120.0, 3500.0)
        }
    }

    # Find existing material names to guarantee no collisions
    existing_names = set(Material.objects.values_list('name', flat=True))
    print(f"Existing materials in DB: {len(existing_names)}")

    now = timezone.now()

    # 1. CREATE 20,000 MATERIALS
    # Target quantity average: 100 / 200 / 250
    quantity_choices_material = [100, 150, 200, 250]
    
    print("\n--- 1. Generating 20,000 New Unique Materials ---")
    materials_to_create = []
    categories = list(CAT_TEMPLATES.keys())
    
    generated_count = 0
    seq_id = 1
    
    while generated_count < 20000:
        cat = categories[generated_count % len(categories)]
        cat_info = CAT_TEMPLATES[cat]
        base_name = cat_info['bases'][(generated_count // len(categories)) % len(cat_info['bases'])]
        
        # Unique name format
        name = f"{base_name} Model-X{seq_id:05d} (SKU-{cat[:3].upper()}-{seq_id:05d})"
        seq_id += 1
        
        if name in existing_names:
            continue
        existing_names.add(name)
        
        qty = random.choice(quantity_choices_material)
        min_rate, max_rate = cat_info['rates']
        rate = round(random.uniform(min_rate, max_rate), 2)
        total_price = round(qty * rate, 2)
        
        m = Material(
            name=name,
            category=cat,
            Type=cat_info['type'],
            quantity=qty,
            rate=rate,
            total_price=total_price,
            Remaining_stock=qty,
            min_stock_level=15,
            notes=f"Standard ISP inventory material - Batch 2026-X{seq_id:05d}",
            status='Normal',
            added_at=now,
            updated_at=now,
            created_by=admin_user,
            is_deleted=False
        )
        materials_to_create.append(m)
        generated_count += 1

    print(f"Prepared {len(materials_to_create)} Material objects. Performing bulk_create...")
    created_materials = Material.objects.bulk_create(materials_to_create, batch_size=2500)
    print(f"Successfully inserted {len(created_materials)} materials into database!")

    # Fetch the newly created materials from DB to have their IDs
    new_materials = list(Material.objects.filter(is_deleted=False).order_by('-id')[:20000])
    new_materials.reverse() # chronological order
    print(f"Retrieved {len(new_materials)} new materials with IDs from DB (ID range: {new_materials[0].id} to {new_materials[-1].id})")

    # 2. CREATE 20,000 MATERIAL REQUESTS FOR FENI BRANCH
    # Quantity average: 100 / 150 / 200
    quantity_choices_request = [100, 150, 200]
    
    print("\n--- 2. Generating 20,000 Material Requests for Feni Branch ---")
    requests_to_create = []
    
    for idx, mat in enumerate(new_materials):
        req_qty = random.choice(quantity_choices_request)
        rate = mat.rate or 100.0
        tot_price = round(req_qty * rate, 2)
        
        mr = MaterialRequest(
            material=mat,
            requester=feni_user,
            quantity=req_qty,
            rate=rate,
            total_price=tot_price,
            notes=f"Stock allocation request for Feni regional distribution #{idx+1}.",
            send_by="Feni Branch Operations Center",
            status='Received',
            request_type='Regular',
            admin_note="Approved & Dispatched by Central Store for Feni Branch",
            pass_on="Dispatched via Central Logistics to Feni Main Store",
            pass_on_at=now,
            received_by="Feni Store Manager",
            received_at=now,
            requested_at=now,
            deducted_from_quantity=req_qty,
            deducted_from_remaining=0,
            is_archived=False,
            is_hidden_by_admin=False,
            is_hidden_by_noc=False
        )
        requests_to_create.append(mr)

    print(f"Prepared {len(requests_to_create)} MaterialRequest objects. Performing bulk_create...")
    created_requests = MaterialRequest.objects.bulk_create(requests_to_create, batch_size=2500)
    print(f"Successfully inserted {len(created_requests)} MaterialRequests for Feni into database!")

    # Fetch created requests with their IDs
    new_requests = list(MaterialRequest.objects.filter(requester=feni_user).order_by('-id')[:20000])
    new_requests.reverse()

    # Map material_id -> request
    mat_to_req = {req.material_id: req for req in new_requests}

    # 3. CREATE 15,000 USED MATERIAL RECORDS FOR FENI
    # Across 15,000 unique materials from the 20,000 new materials
    # Quantity choices: 10 / 20 / 30
    quantity_choices_used = [10, 20, 30]

    CLIENT_NAMES = [
        "Abdur Rahman", "Mohammad Tanvir Ahmed", "Shahriar Kabir", "Nazmul Huda Chowdhury",
        "Kamrul Hasan", "Farhan Ishraq", "Mehedi Hasan", "Anisur Rahman", "Sultan Mahmud",
        "Zakir Hossain", "Feni Digital Cable Net", "Sonali Bank Feni Main Branch",
        "Feni Model High School & College", "M/S Haque Enterprise", "Al-Amin Telecom & Network",
        "Chowdhury Trade Center", "Prime Bank Feni Sub-Branch", "Green Valley IT Solution",
        "Apex Hospital Feni", "Modern Diagnostic Center Feni", "Feni Computer Institute",
        "Star IT Zone Feni", "Bismillah Traders Feni", "Rahmatullah Plaza", "Shahjalal Cyber Net"
    ]

    FENI_ADDRESSES = [
        "SSK Road, Feni Sadar, Feni",
        "Trunk Road, Feni Sadar, Feni",
        "Masterpara, Feni Sadar, Feni",
        "Daganbhuiyan Main Bazar Road, Feni",
        "Chhagalnaiya Main Road, Feni",
        "Sonagazi Bazar Road, Feni",
        "Fulgazi Station Road, Feni",
        "Parshuram Bazar, Feni",
        "Hospital Road, Doctor Para, Feni",
        "Mizan Road, Feni Sadar, Feni",
        "Rampura Road, Feni",
        "College Road, Feni",
        "Shaheed Minar Road, Feni",
        "Islampur, Feni Sadar, Feni",
        "Puran Jail Road, Feni"
    ]

    DISPATCHED_TO_OPTIONS = [
        "Feni Trunk Road POP",
        "Feni Sadar Client Connection",
        "Daganbhuiyan Hub Distribution",
        "Sonagazi Substation Point",
        "Chhagalnaiya POP Center",
        "Masterpara Client Site",
        "Fulgazi Area Node",
        "Hospital Road Distribution Hub",
        "Feni Server Room / Core POP"
    ]

    ISSUES = [
        "New High-Speed Broadband Client Connection Installation",
        "Optical Fiber Core Splicing & SFP Setup",
        "Gigabit Router & Dual-Band ONU Configuration",
        "CATV RF Signal Amplification & Line Restoration",
        "Distribution Box & PLC Splitter Maintenance",
        "Backbone Fiber Link Optimization & Testing",
        "Client Premises Equipment Replacement & Re-termination"
    ]

    print("\n--- 3. Generating 15,000 UsedMaterial Records for Feni Branch (15,000 Unique Materials) ---")
    # Select 15,000 unique materials out of the 20,000 new materials
    selected_materials_for_used = new_materials[:15000]

    used_materials_to_create = []

    for idx, mat in enumerate(selected_materials_for_used):
        used_qty = random.choice(quantity_choices_used)
        client = CLIENT_NAMES[idx % len(CLIENT_NAMES)]
        addr = FENI_ADDRESSES[idx % len(FENI_ADDRESSES)]
        phone = f"018{random.randint(10000000, 99999999)}"
        dispatched = DISPATCHED_TO_OPTIONS[idx % len(DISPATCHED_TO_OPTIONS)]
        issue = ISSUES[idx % len(ISSUES)]
        req_obj = mat_to_req.get(mat.id)

        um = UsedMaterial(
            technician=feni_user,
            material=mat,
            material_request=req_obj,
            client_name=client,
            client_address=addr,
            client_phone=phone,
            dispatched_to=dispatched,
            quantity=used_qty,
            issue=issue,
            status='Accepted',
            admin_note="Verified & approved by NOC & Store Admin",
            added_at=now,
            updated_at=now,
            is_archived=False,
            is_pop_entry=False
        )
        used_materials_to_create.append(um)

    print(f"Prepared {len(used_materials_to_create)} UsedMaterial objects. Performing bulk_create...")
    created_used = UsedMaterial.objects.bulk_create(used_materials_to_create, batch_size=2500)
    print(f"Successfully inserted {len(created_used)} UsedMaterial records into database!")

    print("\n=== VERIFICATION SUMMARY ===")
    total_materials = Material.objects.count()
    total_requests = MaterialRequest.objects.count()
    feni_requests = MaterialRequest.objects.filter(requester=feni_user).count()
    total_used = UsedMaterial.objects.count()
    feni_used = UsedMaterial.objects.filter(technician=feni_user).count()
    feni_used_unique_materials = UsedMaterial.objects.filter(technician=feni_user).values('material_id').distinct().count()

    print(f"Total Materials in DB: {total_materials}")
    print(f"Total Material Requests in DB: {total_requests} (Feni: {feni_requests})")
    print(f"Total Used Materials in DB: {total_used} (Feni: {feni_used}, Unique Materials used: {feni_used_unique_materials})")
    print("Done!")

if __name__ == '__main__':
    run_seed()
