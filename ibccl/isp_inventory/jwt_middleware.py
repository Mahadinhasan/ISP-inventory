from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from urllib.parse import parse_qs

User = get_user_model()

class JWTCookieAuthMiddleware(MiddlewareMixin):
    """
    Reads 'jwt_access_<tab_id>' cookie, validates it and sets request.user.
    Runs after AuthenticationMiddleware so it can override the session-based user.
    """

    def process_request(self, request):
        tab_id = request.GET.get('tab_id') or request.POST.get('tab_id')
        if not tab_id:
            return

        request.tab_id = tab_id
        access_token = request.COOKIES.get(f'jwt_access_{tab_id}')
        user = None

        if access_token:
            try:
                validated = AccessToken(access_token)
                user = User.objects.get(pk=validated['user_id'])
            except:
                pass

        # If access token is invalid, try refresh token
        if not user:
            refresh_token = request.COOKIES.get(f'jwt_refresh_{tab_id}')
            if refresh_token:
                try:
                    from rest_framework_simplejwt.tokens import RefreshToken
                    rt = RefreshToken(refresh_token)
                    user = User.objects.get(pk=rt['user_id'])
                    # If we got here, we should issue a new access token
                    request._new_access_token = str(rt.access_token)
                except:
                    pass

        if user and user.is_active:
            request.user = user
            request._jwt_authenticated = True

    def process_response(self, request, response):
        tab_id = getattr(request, 'tab_id', None)
        if not tab_id:
            return response

        # 1. Handle auto-refresh of access token
        new_token = getattr(request, '_new_access_token', None)
        if new_token:
            from django.conf import settings
            jwt_cfg = getattr(settings, 'SIMPLE_JWT', {})
            response.set_cookie(
                f'jwt_access_{tab_id}',
                new_token,
                max_age=int(jwt_cfg.get('ACCESS_TOKEN_LIFETIME').total_seconds()),
                httponly=True,
                secure=jwt_cfg.get('AUTH_COOKIE_SECURE', False),
                samesite=jwt_cfg.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            )

        # 2. Append tab_id to redirects to maintain tab session
        if hasattr(response, 'url'):
            url = response.url
            if url.startswith('/') or url.startswith(request.build_absolute_uri('/')):
                from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
                parsed = urlparse(url)
                query = dict(parse_qsl(parsed.query))
                if 'tab_id' not in query:
                    query['tab_id'] = tab_id
                    new_query = urlencode(query)
                    new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                    response['Location'] = new_url
        return response


class JWTAuthMiddleware(BaseMiddleware):
    """
    Channels middleware that authenticates users via JWT cookies.
    Requires 'tab_id' in the query string.
    """
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        tab_id = query_params.get('tab_id', [None])[0]

        if tab_id:
            # Channels 3.0+ scope['cookies'] is available
            cookies = scope.get('cookies', {})
            # If scope['cookies'] is not populated, parse from headers
            if not cookies:
                from django.http import parse_cookie
                headers = dict(scope.get('headers', []))
                cookie_header = headers.get(b'cookie', b'').decode()
                cookies = parse_cookie(cookie_header)

            access_token = cookies.get(f'jwt_access_{tab_id}')
            if access_token:
                scope['user'] = await self.get_user_from_token(access_token)
            else:
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token_str):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            validated = AccessToken(token_str)
            user_id = validated['user_id']
            return User.objects.get(pk=user_id)
        except Exception:
            return AnonymousUser()


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
