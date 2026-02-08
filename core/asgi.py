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
allowed_origins = getattr(settings, "CHANNELS_ALLOWED_ORIGINS", [])


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        # تم الاكتفاء بـ AllowedHosts لضمان قبول الاتصال من النطاق المعتمد في Koyeb
        JWTAuthMiddleware(
            URLRouter(attendance.routing.websocket_urlpatterns)
        )
    ),
})
