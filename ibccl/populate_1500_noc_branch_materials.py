import os
import sys
import django
import time
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User
from isp_inventory.models import Material, MaterialRequest

def populate_1500_noc_materials_for_branches():
    print("=== Starting Population of 1,500 NOC Received Materials for ALL Branch Users ===")
    start_time = time.time()

    # Find all Branch users
    branch_users = list(User.objects.filter(userprofile__role='Branch'))
    if not branch_users:
        print("ERROR: No Branch users found in database!")
        return

    print(f"Found {len(branch_users)} Branch user(s): {[u.username for u in branch_users]}")

    # Ensure NOC / Internet materials
    noc_user = User.objects.filter(userprofile__role='NOC').first()
    noc_materials = list(Material.objects.filter(category='Internet'))
    
    if not noc_materials:
        print("No 'Internet' category materials found. Creating NOC materials...")
        noc_materials = [
            Material.objects.create(name="ZTE Dual Band ONU Router", category="Internet", Type="Piece", quantity=50000, rate=2500, total_price=125000000, created_by=noc_user),
            Material.objects.create(name="Huawei OptiXstar ONU", category="Internet", Type="Piece", quantity=50000, rate=2800, total_price=140000000, created_by=noc_user),
            Material.objects.create(name="Tenda Fiber ONU Box", category="Internet", Type="Piece", quantity=50000, rate=1800, total_price=90000000, created_by=noc_user),
            Material.objects.create(name="FiberHome Gigabit SFP Module", category="Internet", Type="Piece", quantity=50000, rate=1200, total_price=60000000, created_by=noc_user)
        ]

    requests_to_create = []
    target_quantity_per_branch = 1500

    for branch_user in branch_users:
        print(f"\nProcessing Branch User: '{branch_user.username}'...")
        
        # Check existing NOC received quantity for this branch user
        existing_received = MaterialRequest.objects.filter(
            requester=branch_user,
            material__category='Internet',
            status='Received'
        ).aggregate(total=django.db.models.Sum('quantity'))['total'] or 0

        print(f" - Existing NOC Received Material Quantity: {existing_received}")
        
        if existing_received < target_quantity_per_branch:
            needed_quantity = target_quantity_per_branch - existing_received
            print(f" - Adding {needed_quantity} units across NOC materials to reach {target_quantity_per_branch}...")
            
            # Distribute quantity evenly across available NOC materials
            selected_mats = noc_materials[:5] if len(noc_materials) >= 5 else noc_materials
            qty_per_item = max(1, needed_quantity // len(selected_mats))
            remaining = needed_quantity

            for idx, mat in enumerate(selected_mats):
                if remaining <= 0:
                    break
                
                chunk_qty = min(remaining, qty_per_item if idx < len(selected_mats) - 1 else remaining)
                remaining -= chunk_qty

                requests_to_create.append(MaterialRequest(
                    requester=branch_user,
                    material=mat,
                    quantity=chunk_qty,
                    rate=mat.rate or 0,
                    total_price=chunk_qty * (mat.rate or 0),
                    status='Received',
                    request_type='Regular',
                    pass_on='NOC Team Direct Distribution',
                    pass_on_at=timezone.now(),
                    received_by=branch_user.username,
                    received_at=timezone.now(),
                    admin_note=f"NOC 1500 Material Allocation - Batch #{idx+1}"
                ))

    if requests_to_create:
        MaterialRequest.objects.bulk_create(requests_to_create)
        print(f"\nSuccessfully created {len(requests_to_create)} MaterialRequest records with status='Received'!")
    else:
        print("\nAll branch users already have at least 1,500 NOC Received materials!")

    elapsed = time.time() - start_time
    print(f"=== Population Completed in {elapsed:.2f} seconds ===")

if __name__ == '__main__':
    populate_1500_noc_materials_for_branches()
