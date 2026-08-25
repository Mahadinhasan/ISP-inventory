import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User, Group
from isp_inventory.models import Material, MaterialRequest, UserProfile

def setup_feni_branch():
    print("=== Step 1: Configuring Feni Branch User ===")
    branch_group, _ = Group.objects.get_or_create(name='Branch')
    
    feni_user, created = User.objects.get_or_create(
        username='Feni',
        defaults={
            'email': 'feni@ibccl.com',
            'first_name': 'Feni',
            'last_name': 'Branch',
            'is_active': True
        }
    )
    feni_user.set_password('Admin123@')
    feni_user.is_active = True
    feni_user.email = 'feni@ibccl.com'
    feni_user.save()
    
    feni_user.groups.clear()
    feni_user.groups.add(branch_group)
    
    profile, _ = UserProfile.objects.get_or_create(user=feni_user)
    profile.role = 'Branch'
    profile.phone = '+8801711003344'
    profile.address = 'IBCCL Feni Branch Regional Hub, Trunk Road, Feni'
    profile.city = 'Feni'
    profile.zip_code = '3900'
    profile.is_active = True
    profile.is_verified = True
    profile.save()
    print(f"User 'Feni' successfully configured with Password 'Admin123@' and Role 'Branch'!")

    # Step 2: Ensure we have at least 10,000 materials in the database
    print("\n=== Step 2: Ensuring 10,000 Total Materials Exist in Database ===")
    current_mat_count = Material.objects.count()
    target_mat_count = 10000
    
    admin_users = list(User.objects.filter(userprofile__role='Admin'))
    store_users = list(User.objects.filter(userprofile__role='Storekeeper'))
    creators = (admin_users + store_users) or [feni_user]
    
    if current_mat_count < target_mat_count:
        needed = target_mat_count - current_mat_count
        print(f"Current Materials: {current_mat_count:,}. Creating {needed:,} additional materials from Admin/Storekeeper...")
        
        categories = ['Fiber', 'Internet', 'Dish', 'Common item', 'Work shop']
        types_map = {'Fiber': 'Meter', 'Internet': 'Piece', 'Dish': 'Piece', 'Common item': 'Piece', 'Work shop': 'Piece'}
        
        base_names = [
            "Optical Fiber G.652D Core", "Armored Underground Cable", "Drop Fiber Cable 2-Core",
            "ONU EPON/GPON Dual Mode", "Gigabit Router AC1200", "WiFi6 Mesh Router AX3000",
            "SFP Module Single Mode 20KM", "SFP+ 10G Optical Transceiver", "Media Converter 1000Base-TX",
            "PLC Splitter 1:8 Cassette", "PLC Splitter 1:16 Box", "PLC Splitter 1:32 Rack Mount",
            "Fiber Fast Connector SC/UPC", "Fiber Fast Connector SC/APC", "Fiber Splice Protection Sleeve",
            "Cat6 UTP Solid Cable 305M", "Cat6 SFTP Outdoor Cable", "RJ45 Modular Plug Gold Plated",
            "Cat6 Keystone Jack Toolless", "Patch Panel 24 Port Loaded", "Server Rack Cabinet 32U",
            "Wallmount Mini Rack 6U", "Core Layer 3 Switch 24G", "PoE+ Managed Switch 16 Port",
            "Coaxial Cable RG6 Shielded", "Coaxial Trunk Cable RG11", "BNC Compression Connector",
            "Satellite Dish 120cm Prime", "Ku-Band Single LNB", "RF Signal Amplifier 30dB",
            "Power Adapter 12V 3A DC", "Telecom SMPS Power 48V", "Online Industrial UPS 3KVA",
            "Fiber Cleaver High Precision", "Optical Power Meter -70~+10", "VFL Laser Pointer 50mW"
        ]
        
        new_materials = []
        for i in range(current_mat_count + 1, target_mat_count + 1):
            base = base_names[(i - 1) % len(base_names)]
            batch = ((i - 1) // len(base_names)) + 1
            name = f"{base} Enterprise Grade SKU-{batch:03d}-{i:05d}"
            cat = categories[i % len(categories)]
            mtype = types_map.get(cat, 'Piece')
            qty = 50000
            rate = round(random.uniform(40.0, 950.0), 2)
            total_price = round(qty * rate, 2)
            creator = creators[i % len(creators)]
            
            new_materials.append(Material(
                name=name,
                category=cat,
                Type=mtype,
                quantity=qty,
                rate=rate,
                total_price=total_price,
                Remaining_stock=qty,
                min_stock_level=500,
                status='Normal',
                notes=f"Created by {creator.username} ({creator.userprofile.role}) for network distribution.",
                created_by=creator,
                is_deleted=False
            ))
            
        Material.objects.bulk_create(new_materials, batch_size=1000, ignore_conflicts=True)
        print(f"Materials population finished! Total in DB: {Material.objects.count():,}")

    # Step 3: Create 10,000 Received Material Requests for Feni branch
    print("\n=== Step 3: Assigning 10,000 Materials (Quantity 15,000 each) to Feni Branch (Status: Received) ===")
    
    # Clean previous requests for Feni to ensure clean 10,000 set
    MaterialRequest.objects.filter(requester=feni_user).delete()
    
    all_materials = list(Material.objects.all()[:10000])
    requests_to_create = []
    now = timezone.now()
    quantity_received = 15000
    
    for mat in all_materials:
        rate = mat.rate or 100.0
        req = MaterialRequest(
            material=mat,
            requester=feni_user,
            quantity=quantity_received,
            rate=rate,
            total_price=round(quantity_received * rate, 2),
            status='Received',
            request_type='Regular',
            notes='Stock allocation for Feni regional network deployment.',
            send_by='Feni Branch Network Operations',
            admin_note='Approved & Authorized for Feni Branch',
            pass_on='Dispatched from Central Storekeeper Warehouse',
            pass_on_at=now,
            received_by='Feni Branch Manager',
            received_at=now,
            requested_at=now,
            deducted_from_quantity=quantity_received,
            is_archived=False,
            is_hidden_by_admin=False,
            is_hidden_by_noc=False
        )
        requests_to_create.append(req)

    created_reqs = MaterialRequest.objects.bulk_create(requests_to_create, batch_size=1000)
    print(f"Successfully created {len(created_reqs):,} Received Material Requests for user 'Feni'!")
    print(f"Total Received Quantity in Feni Branch Stock: {len(created_reqs) * quantity_received:,} units")
    print("\n=== All Tasks Completed Successfully! ===")

if __name__ == '__main__':
    setup_feni_branch()
