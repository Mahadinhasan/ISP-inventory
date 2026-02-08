# Generated migration to remove material_request field from UsedMaterial

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isp_inventory', '0017_usedmaterial_material_request_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usedmaterial',
            name='material_request',
        ),
    ]
