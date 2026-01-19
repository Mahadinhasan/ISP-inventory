from django.contrib.auth.models import Group
from .models import UserProfile

ROLE_GROUPS = ['Admin', 'Storekeeper', 'Technician']


def ensure_userprofile(user):
    """Ensure a UserProfile exists for `user` and return it.

    This function is defensive: it handles the case where the reverse
    OneToOne accessor (`user.userprofile`) does not exist yet and will
    create a `UserProfile` using the first matching role-group or the
    default role `'Technician'`.
    """
    if user is None or user.pk is None:
        return None

    # Try to access the reverse relation safely
    try:
        profile = user.userprofile
        if profile:
            return profile
    except Exception:
        profile = None

    # Infer role from group membership if possible
    role_name = None
    try:
        grp = user.groups.filter(name__in=ROLE_GROUPS).first()
        if grp:
            role_name = grp.name
    except Exception:
        role_name = None

    if not role_name:
        role_name = 'Technician'

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role_name})
    return profile
