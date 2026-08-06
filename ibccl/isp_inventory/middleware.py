import threading
from django.utils import timezone
from .utils import ensure_userprofile

_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_request():
    return getattr(_thread_locals, 'request', None)

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store current user and request in thread-local storage
        _thread_locals.user = request.user if request.user.is_authenticated else None
        _thread_locals.request = request
        
        if request.user.is_authenticated:
            try:
                profile = ensure_userprofile(request.user)
                now = timezone.now()
                # Throttle DB updates: update last_active at most once every 60 seconds
                if not profile.last_active or (now - profile.last_active).total_seconds() > 60:
                    profile.last_active = now
                    profile.is_active = True
                    profile.save(update_fields=['last_active', 'is_active'])
            except Exception:
                pass
                
        response = self.get_response(request)
        
        # Clear storage at the end of the request
        _thread_locals.user = None
        _thread_locals.request = None
        
        return response
