# This migration is intentionally empty.
# The phone field was added correctly in 0032 (without unique=True).
# This file is kept only to preserve the migration dependency chain.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isp_inventory', '0033_remove_userprofile_phone'),
    ]

    operations = [
        # no-op: phone was handled correctly in 0032
    ]
