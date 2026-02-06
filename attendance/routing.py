from django.urls import re_path
from . import consumers

websocket_urlpatterns = [


    re_path(r"ws/pickup/screen/$", consumers.SmartScreenConsumer.as_asgi()),
    re_path(r"ws/pickup/teacher/$", consumers.TeacherConsumer.as_asgi()),


]


