import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
django.setup()
from isp_inventory.models import UsedMaterial, DamageMaterial
print("UsedMaterial fields:", [f.name for f in UsedMaterial._meta.get_fields()])
print()
print("DamageMaterial fields:", [f.name for f in DamageMaterial._meta.get_fields()])
