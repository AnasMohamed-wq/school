from django.urls import path
from . import views_ui

urlpatterns = [
    path('ui/login/', views_ui.ui_login, name='ui_login'),
    path('ui/logout/', views_ui.ui_logout, name='ui_logout'),
    path('ui/', views_ui.ui_dashboard, name='ui_dashboard'),
    path('ui/students/', views_ui.ui_students, name='ui_students'),
    path('ui/students/create/', views_ui.ui_students_create, name='ui_students_create'),
    path('ui/students/transfer/', views_ui.ui_students_transfer, name='ui_students_transfer'),
    path('ui/students/assign-parent/', views_ui.ui_students_assign_parent, name='ui_students_assign_parent'),

    path('ui/classes/', views_ui.ui_classes, name='ui_classes'),
    path('ui/classes/create/', views_ui.ui_classes_create, name='ui_classes_create'),
    path('ui/classes/update/', views_ui.ui_classes_update, name='ui_classes_update'),
    path('ui/classes/deactivate/', views_ui.ui_classes_deactivate, name='ui_classes_deactivate'),

    path('ui/parents/', views_ui.ui_parents, name='ui_parents'),
    path('ui/parents/approve/', views_ui.ui_parents_approve, name='ui_parents_approve'),

    path('ui/screens/', views_ui.ui_screens, name='ui_screens'),
    path('ui/screens/create/', views_ui.ui_screens_create, name='ui_screens_create'),

    path('ui/settings/', views_ui.ui_settings, name='ui_settings'),
    path('ui/settings/update/', views_ui.ui_settings_update, name='ui_settings_update'),
]