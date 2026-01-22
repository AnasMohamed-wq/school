from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

class AuthService:
    @staticmethod
    def login_user(phone, password):
        user = authenticate(username=phone, password=password)
        if not user:
            raise AuthenticationFailed("بيانات الدخول غير صحيحة")
        if not user.is_active:
            raise PermissionDenied("هذا الحساب معطل")
        
        refresh = RefreshToken.for_user(user)
        # إضافة الـ Role للتوكن مباشرة
        refresh['role'] = user.role
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': user.role
        }
    
    @staticmethod
    def logout_user(refresh_token):
        try:
            # نقوم بإبطال الـ Refresh Token لمنع توليد Access Tokens جديدة
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            raise AuthenticationFailed("التوكن غير صالح أو منتهي الصلاحية")
        
        

class AccessService:
    @staticmethod
    def verify_school_affiliation(user, school_id):
        if not user or not user.is_authenticated:
            return False

        if user.role == 'SUPER_ADMIN':
            return True
        
        # استخدام getattr لتجنب الـ AttributeError
        if user.role == 'MANAGER':
            manager_profile = getattr(user, 'schoolmanager', None)
            return manager_profile and manager_profile.school_id == int(school_id)
            
        if user.role == 'TEACHER':
            teacher_profile = getattr(user, 'teacher', None)
            return teacher_profile and teacher_profile.school_id == int(school_id)
            
        if user.role == 'PARENT':
            parent_profile = getattr(user, 'parent', None)
            if not parent_profile:
                return False
            return parent_profile.parentschool_set.filter(
                school_id=school_id, is_approved=True
            ).exists()
            
        return False