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
    except:
        return AnonymousUser()
# class JWTAuthMiddleware:
#     def __init__(self, app):
#         self.app = app

#     async def __call__(self, scope, receive, send):


#         token = None
#         # 1. البحث في الـ Headers أولاً (مثل Postman)
#         headers = dict(scope['headers'])
#         if b'authorization' in headers:
#             try:
#                 auth_header = headers[b'authorization'].decode().split()
#                 if len(auth_header) == 2 and auth_header[0].lower() == 'bearer':
#                     token = auth_header[1]
#             except: pass
#         if not token:
#             query_string = scope.get("query_string", b"").decode("utf-8")
#             params = parse_qs(query_string)
#             token = params.get('token', [None])[0]

#         if token:
#             try:
#                 access_token = AccessToken(token)
#                 user_id = access_token.get("user_id")
#                 if user_id:
#                     scope['user'] = await get_user(user_id)
#             except Exception as e:
#                 # تسجيل الخطأ في اللوج دون إيقاف السيرفر
#                 logger.debug(f"WebSocket Auth Error: {e}")
#                 scope['user'] = AnonymousUser()
#         else:
#             scope['user'] = AnonymousUser()

#         return await self.app(scope, receive, send)


# attendance/middleware.py
class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get('headers', []))
        query_params = parse_qs(scope.get("query_string", b"").decode())
        
        # جلب التوكن من الهيدر أو الرابط
        token = None
        if b'authorization' in headers:
            try:
                auth_header = headers[b'authorization'].decode().split()
                if len(auth_header) == 2 and auth_header[0].lower() == 'bearer':
                    token = auth_header[1]
            except: pass
        
        if not token:
            token = query_params.get('token', [None])[0]

        # محاولة التحقق إذا كان JWT (للمعلم)
        scope['user'] = AnonymousUser()
        if token:
            try:
                # إذا كان توكن JWT صالح، نربط المستخدم
                access_token = AccessToken(token)
                scope['user'] = await get_user(access_token['user_id'])
            except Exception:
                # إذا فشل (مثل توكن الشاشة)، نتركه Anonymous 
                # والـ Consumer الخاص بالشاشة سيتولى التحقق من قاعدة البيانات
                pass

        return await self.app(scope, receive, send)