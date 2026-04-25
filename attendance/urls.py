from django.urls import path
from .views import (
    LoginView,LogoutView,
    ParentSchoolListView, StudentListView, CreateRequestView,
    ClassDashboardView, ActiveRequestsView,
    ApprovalActionView ,StudentActionView ,
    UnifiedStudentActionView ,
    PasswordResetView,screen
)
from attendance import views

urlpatterns = [
    # --- المسار العام (المصادقة) ---
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'), # المسار الجديد
    path('auth/reset-password/', PasswordResetView.as_view(), name='password-reset'),

    # --- مسارات ولي الأمر (Parent) ---
    path('parent/schools/', ParentSchoolListView.as_view(), name='parent-schools'),
    path('parent/students/', StudentListView.as_view(), name='parent-students'),
    path('parent/pickup/create/', CreateRequestView.as_view(), name='create-pickup'),

    # --- مسارات المعلم (Teacher) ---
    path('teacher/dashboard/', ClassDashboardView.as_view(), name='teacher-dashboard'),
    path('teacher/requests/active/', ActiveRequestsView.as_view(), name='active-requests'),
    # ملاحظة: يمكنك إضافة ActionUpdateView هنا لتغيير حالة الطلب (قبول/تسليم)
    path('teacher/student/<int:student_id>/update-status/', StudentActionView.as_view(), name='student-action-update'),
    path('teacher/student/<int:student_id>/action/', UnifiedStudentActionView.as_view(), name='student-action'),

    # --- مسارات المدير (Manager) ---   
    path('manager/approve-parent/<int:parent_id>/', ApprovalActionView.as_view(), name='approve-parent'),
    path('screen/', screen, name='screen'),  # مسار الشاشة العامة

    
]