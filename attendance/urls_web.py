from django.urls import path
from .view_web import (
    
        class_management_view, parent_management_main_view, web_login_view,web_logout_view,
        student_management_main_view,web_teachers_management,

                    
                    )






urlpatterns = [

        path('login/', web_login_view, name='web_login'),  # مسار تسجيل الدخول العام
        path('logout/', web_logout_view, name='web_logout'),  # مسار تسجيل الخروج العام
        #الطلاب 
        path('students/', student_management_main_view, name='web_students'),
        path('parents/', parent_management_main_view, name='web_parents'),
        path('teachers/', web_teachers_management, name='web_teachers'),
        path('class/', class_management_view, name='web_class'),

]