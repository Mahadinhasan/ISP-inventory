import os
import django
import random
import time
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest, UsedMaterial, UserProfile

def run():
    print("=== Populating 200 Used Materials for Each Branch User ===")
    start_time = time.time()
    
    branch_users = list(User.objects.filter(userprofile__role='Branch').order_by('username'))
    print(f"Found {len(branch_users)} Branch Users.")
    
    client_names = [
        "Abul Kalam", "Rahim Uddin", "Karim Hossain", "Kamal Ahmed", "Nusrat Jahan",
        "Faruk Hossain", "Rubi Akter", "Jakir Hosen", "Salma Khatun", "Belal Ahmed",
        "Mitu Begum", "Sirajul Islam", "Fatema Begum", "Mosharraf Hossain", "Delwar Hossain",
        "Standard Chartered Bank", "Grameenphone POP", "Labaid Hospital", "Brac Bank POP"
    ]
    
    client_addresses = [
        "Dhanmondi, Dhaka", "Gulshan 2, Dhaka", "Uttara North, Dhaka", "Mohakhali, Dhaka",
        "Motijheel, Dhaka", "Farmgate, Dhaka", "Mirpur 10, Dhaka", "Mirpur 12, Dhaka",
        "Bashundhara R/A, Dhaka", "Badda, Dhaka", "Ramna, Dhaka", "Khilgaon, Dhaka",
        "Jatrabari, Dhaka", "Savar, Dhaka", "Gazipur Sadar", "Narayanganj Sadar",
        "Sylhet Sadar", "Chittagong Sadar", "Khulna Sadar", "Rajshahi Sadar", "Feni Sadar"
    ]
    
    issues = [
        "New Client Connection", "Router Upgrade", "Fiber Line Maintenance",
        "ONU Replacement", "Cable Repair Work", "Client internet disconnected",
        "Splitter replacement", "Speed issue resolved", "Device upgrade"
    ]
    
    qty_choices = [1, 1, 1, 2, 2, 3, 5]
    all_materials = list(Material.objects.all())
    
    total_created = 0
    
    for u in branch_users:
        received_reqs = list(
            MaterialRequest.objects.filter(
                requester=u,
                status='Received'
            ).select_related('material')
        )
        
        materials_pool = [req.material for req in received_reqs] if received_reqs else all_materials
        req_map = {req.material_id: req for req in received_reqs}
        
        used_batch = []
        now = timezone.now()
        for _ in range(200):
            mat = random.choice(materials_pool)
            req_obj = req_map.get(mat.id, None)
            qty = random.choice(qty_choices)
            days_ago = random.randint(0, 30)
            created_time = now - timezone.timedelta(days=days_ago, minutes=random.randint(0, 1440))
            
            used_batch.append(UsedMaterial(
                technician=u,
                material=mat,
                material_request=req_obj,
                client_name=random.choice(client_names),
                client_address=random.choice(client_addresses),
                client_phone=f"017{random.randint(10000000, 99999999)}",
                quantity=qty,
                issue=random.choice(issues),
                status='Accepted',
                admin_note="Auto-populated branch stock material usage (200 records)",
                added_at=created_time
            ))
        
        UsedMaterial.objects.bulk_create(used_batch, batch_size=200)
        total_created += len(used_batch)
        print(f"   [+] Added 200 UsedMaterial records for branch user: {u.username}")
        
    print(f"\n================ SUCCESS SUMMARY ================")
    print(f"  Total UsedMaterial Records Created: {total_created:,}")
    print(f"  Branch Users Processed           : {len(branch_users)}")
    print(f"  Time Taken                      : {time.time() - start_time:.2f}s")
    print("=================================================")

if __name__ == '__main__':
    run()
