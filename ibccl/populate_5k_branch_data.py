import os
import sys
import django
import time
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest, UsedMaterial, UserProfile

def populate_branch_data():
    print("=== Starting 20 New Branch Users & 5,000 Branch Stock Population ===")
    start_time = time.time()

    # 1. Create 20 New Branch Users
    branch_names = [
        'dhanmondi', 'gulshan2', 'uttara_north', 'mohakhali', 'motijheel',
        'farmgate', 'mirpur10', 'mirpur12', 'bashundhara', 'badda',
        'ramna', 'khilgaon', 'jatrabari', 'savar', 'gazipur',
        'narayanganj', 'sylhet', 'chittagong', 'khulna', 'rajshahi'
    ]

    branch_users = []
    print("\n1. Creating / Verifying 20 New Branch Users (Password: Admin123@)...")
    for b_name in branch_names:
        user, created = User.objects.get_or_create(
            username=b_name,
            defaults={
                'email': f"{b_name}@ibccl.com",
                'first_name': b_name.capitalize(),
                'last_name': 'Branch'
            }
        )
        if created:
            user.set_password('Admin123@')
            user.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'Branch', 'is_active': True}
            )
            print(f"   [+] Created User: {b_name} (Role: Branch)")
        else:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role != 'Branch':
                profile.role = 'Branch'
                profile.save()
            print(f"   [=] Existing User: {b_name} (Role: Branch)")
        branch_users.append(user)

    # Include existing mirpur user
    try:
        mirpur = User.objects.get(username='mirpur')
        if mirpur not in branch_users:
            branch_users.append(mirpur)
    except User.DoesNotExist:
        pass

    print(f"Total Active Branch Users: {len(branch_users)}")

    # 2. Populate 5,000 Branch Used Material Records
    existing_used_count = UsedMaterial.objects.count()
    print(f"\n2. Current Used Material Count in Database: {existing_used_count}")

    target_used = 5000
    needed_used = max(0, target_used - existing_used_count)

    if needed_used > 0:
        print(f"Generating {needed_used} Used Material records for Branch users...")
        all_materials = list(Material.objects.all())
        if not all_materials:
            print("ERROR: No materials found in database!")
            return

        statuses = ['Accepted', 'Pending', 'Rejected']
        clients = ['Abul Kalam', 'Rahim Uddin', 'Karim Hossain', 'Kamal Ahmed', 'Nusrat Jahan', 'Standard Chartered Bank', 'Grameenphone POP', 'Labaid Hospital']
        issues = ['New Client Connection', 'Router Upgrade', 'Fiber Line Maintenance', 'ONU Replacement', 'Cable Repair Work']

        batch_size = 1000
        total_batches = (needed_used + batch_size - 1) // batch_size
        total_inserted = 0

        for b_idx in range(total_batches):
            batch_list = []
            curr_count = min(batch_size, needed_used - total_inserted)
            for _ in range(curr_count):
                tech = random.choice(branch_users)
                mat = random.choice(all_materials)
                qty = random.randint(1, 10)
                st = random.choice(statuses)

                batch_list.append(UsedMaterial(
                    technician=tech,
                    material=mat,
                    client_name=random.choice(clients),
                    client_address=f"House #{random.randint(1,99)}, Road #{random.randint(1,50)}, Dhaka",
                    client_phone=f"0171{random.randint(1000000, 9999999)}",
                    quantity=qty,
                    issue=random.choice(issues),
                    status=st
                ))

            UsedMaterial.objects.bulk_create(batch_list, batch_size=batch_size, ignore_conflicts=True)
            total_inserted += len(batch_list)
            print(f"   Inserted Batch {b_idx + 1}/{total_batches} ({total_inserted}/{needed_used})")

    final_used_count = UsedMaterial.objects.count()
    print(f"\nTotal Used Material Records in Database: {final_used_count}")

    # 3. Create 5,000 Material Requests across all 20 Branch Users
    existing_req_count = MaterialRequest.objects.count()
    target_req = 5000
    needed_req = max(0, target_req - existing_req_count)

    if needed_req > 0:
        print(f"\n3. Generating {needed_req} Material Requests across 20 Branch Users...")
        all_materials = list(Material.objects.all())
        req_types = ['Regular', 'Advance']
        req_statuses = ['Received', 'Approved', 'Dispatched', 'Pending']

        batch_size = 1000
        total_batches = (needed_req + batch_size - 1) // batch_size
        total_inserted = 0

        for b_idx in range(total_batches):
            batch_list = []
            curr_count = min(batch_size, needed_req - total_inserted)
            for _ in range(curr_count):
                b_user = random.choice(branch_users)
                mat = random.choice(all_materials)
                qty = random.randint(5, 100)
                st = random.choice(req_statuses)

                batch_list.append(MaterialRequest(
                    requester=b_user,
                    material=mat,
                    quantity=qty,
                    request_type=random.choice(req_types),
                    status=st,
                    pass_on="Storekeeper Issued",
                    received_by=b_user.username,
                    admin_note="Branch stock load testing"
                ))

            MaterialRequest.objects.bulk_create(batch_list, batch_size=batch_size, ignore_conflicts=True)
            total_inserted += len(batch_list)
            print(f"   Inserted Batch {b_idx + 1}/{total_batches} ({total_inserted}/{needed_req})")

    final_req_count = MaterialRequest.objects.count()
    print(f"\nTotal Material Requests in Database: {final_req_count}")

    elapsed = time.time() - start_time
    print(f"\nCompleted Branch Users & 5K Stock Population in {elapsed:.2f} seconds!")

if __name__ == '__main__':
    populate_branch_data()
