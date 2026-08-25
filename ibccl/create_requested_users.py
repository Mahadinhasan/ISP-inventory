import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()

from django.contrib.auth.models import User, Group
from isp_inventory.models import UserProfile

for g in ['Admin', 'Storekeeper', 'Branch', 'NOC']:
    Group.objects.get_or_create(name=g)

password = 'Password@123'

roles_config = [
    ('Branch', 'branch', 10),
    ('Storekeeper', 'store', 5),
    ('NOC', 'noc', 5),
    ('Admin', 'admin', 10),
]

summary = []

for role, prefix, count in roles_config:
    grp = Group.objects.get(name=role)
    for i in range(1, count + 1):
        username = f'{prefix}{i}'
        email = f'{username}@ibccl.com'
        
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=f'{role}',
                last_name=f'User {i}',
                is_active=True,
                is_staff=(role == 'Admin'),
                is_superuser=(role == 'Admin' and username in ['admin', 'admin1'])
            )
        else:
            user.set_password(password)
            user.email = email
            user.is_active = True
            user.is_staff = (role == 'Admin')
            user.is_superuser = (role == 'Admin' and username in ['admin', 'admin1'])
            user.save()
            
        user.groups.clear()
        user.groups.add(grp)
        
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.phone = f'+8801711{i:05d}'
        profile.address = f'IBCCL {role} Office Zone {i}'
        profile.city = 'Dhaka'
        profile.zip_code = '1200'
        profile.is_active = True
        profile.is_verified = True
        profile.save()
        
        summary.append((username, role, email))

print(f"Total Users configured: {len(summary)}")
