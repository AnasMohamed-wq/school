from django.urls import re_path
from . import consumers

websocket_urlpatterns = [


    # re_path(
#         r"ws/pickup/screen/(?P<school_id>\d+)/(?P<class_id>\d+)/$",
#         consumers.SmartScreenConsumer.as_asgi()
#     ),

#     re_path(
#         r"ws/pickup/teacher/$",
#         consumers.TeacherConsumer.as_asgi()
    # ),


        # بدلاً من المسار القديم الذي يحتوي على ID المدارس والفصول

    re_path(r"ws/pickup/screen/$", consumers.SmartScreenConsumer.as_asgi()),
    re_path(r"ws/pickup/teacher/$", consumers.TeacherConsumer.as_asgi()),


]


