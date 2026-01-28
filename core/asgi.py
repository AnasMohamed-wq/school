import os
import django
from django.core.asgi import get_asgi_application
from channels.security.websocket import OriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack 
from attendance.middleware import JWTAuthMiddleware # استيراد الميدل وير الخاص بك
# استيراد الـ routing من تطبيقك
import attendance.routing 



application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": OriginValidator(
        JWTAuthMiddleware(
            URLRouter(attendance.routing.websocket_urlpatterns)
        ),
        ["*"] # يسمح بالاتصال من أي مكان في مرحلة التطوير
    ),
})