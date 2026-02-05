from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from .utils import ensure_userprofile
from .models import UsedMaterial, Material


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            ensure_userprofile(instance)
        except Exception:
            # Avoid raising during user creation if profile can't be created
            pass


@receiver(post_save, sender=UsedMaterial)
def subtract_used_material_from_inventory(sender, instance, created, **kwargs):
    """
    Automatically subtract used materials from the material's stock quantity.
    This is called when a UsedMaterial is created or updated.
    """
    if created:
        # When a new UsedMaterial is created, subtract its quantity from the material's stock
        material = instance.material
        if material:
            # Deduct the used quantity from available material stock
            material.quantity = max(0, material.quantity - instance.quantity)
            material.save(update_fields=['quantity'])


@receiver(post_delete, sender=UsedMaterial)
def restore_used_material_to_inventory(sender, instance, **kwargs):
    """
    Automatically restore used materials back to inventory when a UsedMaterial record is deleted.
    This ensures we don't lose track of material quantities if a record is removed.
    """
    material = instance.material
    if material:
        # Restore the deleted used material quantity back to inventory
        material.quantity += instance.quantity
        material.save(update_fields=['quantity'])
