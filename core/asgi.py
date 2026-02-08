# import os
# import django
# from django.core.asgi import get_asgi_application
# from channels.security.websocket import OriginValidator
# from django.conf import settings

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# django.setup()

# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack 
# from attendance.middleware import JWTAuthMiddleware # استيراد الميدل وير الخاص بك
# # استيراد الـ routing من تطبيقك
# import attendance.routing 



# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": OriginValidator(
#         JWTAuthMiddleware(
#             URLRouter(attendance.routing.websocket_urlpatterns)
#         ),
#         ["*"] if settings.DEBUG else settings.CHANNELS_CORS_ALLOWED_ORIGINS
#         #settings.CHANNELS_CORS_ALLOWED_ORIGINS     في مرحلة الانتاج 
#     ),
# })


import os
import django
from django.core.asgi import get_asgi_application
from channels.security.websocket import OriginValidator ,AllowedHostsOriginValidator
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from attendance.middleware import JWTAuthMiddleware
import attendance.routing

# تحديد قائمة الـ origins للاستخدام في OriginValidator
if settings.DEBUG:
    # أثناء التطوير نسمح للمحليين فقط؛ لا تستخدم '*' حتى في التطوير.
    allowed_origins = [
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:8000",   # إضافة نطاق السيرفر نفسه
        "http://127.0.0.1:8000",
        "https://used-alex-techcodesdn-bdb25f1f.koyeb.app",
    ]
else:
    allowed_origins = settings.CHANNELS_CORS_ALLOWED_ORIGINS

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator( # الطبقة الأولى: هل الطلب موجه لموقعي؟
        OriginValidator( # الطبقة الثانية: هل المصدر موثوق؟
            JWTAuthMiddleware( # الطبقة الثالثة: هل المستخدم مسجل دخول؟
                URLRouter(attendance.routing.websocket_urlpatterns)
            ),
            allowed_origins
        )
    ),
})

