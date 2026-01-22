from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .models import SchoolManager, Teacher, ParentSchool ,School
from .services.identity_services import AccessService
from django.shortcuts import get_object_or_404

# 1. التحقق من أن الحساب نشط (أساسي لكل العمليات)
class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )

# 2. صلاحيات الأدوار (Roles)
class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) == 'TEACHER'

class IsParent(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) == 'PARENT'

class IsSchoolManager(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, 'role', None) == 'MANAGER'

# 3. دالة التحقق من التبعية (Helper) 
# تم تحديثها لتكون "نحيفة" وتعتمد على الـ Service
def authorize_request(request, school_id=None):
    user = request.user
    
    # استخدام الخدمة المركزية للتحقق
    
    
    if not AccessService.verify_school_affiliation(user, school_id):
        raise PermissionDenied("غير مصرح لك بالوصول لبيانات هذه المدرسة.")
    
    school = get_object_or_404(School, id=school_id, is_active=True)
    return school
    
    # # إرجاع كائن المدرسة لتسهيل العمل في الـ View
    # if user.role == 'SUPER_ADMIN': return school_id
    # if user.role == 'MANAGER': return user.schoolmanager.school
    # if user.role == 'TEACHER': return user.teacher.school
    # if user.role == 'PARENT': return ParentSchool.objects.get(parent__user=user, school_id=school_id).school
