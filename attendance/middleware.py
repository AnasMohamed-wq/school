from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()



class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope['user'] = AnonymousUser()

        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]

        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                if user_id:
                    scope['user'] = await get_user(user_id)
            except Exception:
                pass

        return await self.app(scope, receive, send)
