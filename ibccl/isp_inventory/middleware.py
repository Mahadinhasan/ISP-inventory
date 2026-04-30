from django.utils import timezone
from .utils import ensure_userprofile

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = ensure_userprofile(request.user)
                profile.last_active = timezone.now()
                profile.is_active = True
                profile.save(update_fields=['last_active', 'is_active'])
            except Exception:
                pass
        response = self.get_response(request)
        return response
