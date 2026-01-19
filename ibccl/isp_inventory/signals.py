from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .utils import ensure_userprofile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            ensure_userprofile(instance)
        except Exception:
            # Avoid raising during user creation if profile can't be created
            pass
