from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()

class JWTCookieAuthMiddleware(MiddlewareMixin):
    """
    Reads 'jwt_access_<tab_id>' cookie, validates it and sets request.user.
    Runs after AuthenticationMiddleware so it can override the session-based user.
    """

    def process_request(self, request):
        tab_id = request.GET.get('tab_id') or request.POST.get('tab_id')
        request.user = AnonymousUser()

        if tab_id:
            request.tab_id = tab_id
            cookie_name = f'jwt_access_{tab_id}'
            token = request.COOKIES.get(cookie_name)
            if token:
                try:
                    validated = AccessToken(token)
                    user_id = validated['user_id']
                    user = User.objects.get(pk=user_id)
                    if user.is_active:
                        request.user = user
                        request._jwt_authenticated = True
                except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
                    pass

    def process_response(self, request, response):
        """If returning a redirect, append tab_id to keep the tab session."""
        if hasattr(request, 'tab_id') and hasattr(response, 'url'):
            url = response.url
            if url.startswith('/') or url.startswith(request.build_absolute_uri('/')):
                from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
                parsed = urlparse(url)
                query = dict(parse_qsl(parsed.query))
                if 'tab_id' not in query:
                    query['tab_id'] = request.tab_id
                    new_query = urlencode(query)
                    new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                    response['Location'] = new_url
        return response
