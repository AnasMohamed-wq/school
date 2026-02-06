from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
import logging
import secrets

logger = logging.getLogger(__name__)

User = get_user_model()
      

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
        
    
    @staticmethod
    def verify_identity_for_reset(phone, national_id):
        """التحقق من الهوية (نفس منطقك السابق)"""
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise ValidationError("لا يوجد مستخدم مسجل بهذا الرقم.")

        if not user.national_id:
            raise ValidationError("الهوية غير معرفة. راجع الإدارة.")

        if user.national_id != national_id:
            raise ValidationError("بيانات الهوية غير متطابقة.")
        
        return user

    @staticmethod
    @transaction.atomic
    def reset_password(phone, national_id, new_password):
        """الدالة المركزية لتغيير كلمة السر"""
        # 1. التحقق من الهوية
        user = AuthService.verify_identity_for_reset(phone, national_id)
        
        # 2. التغيير الفعلي
        user.set_password(new_password)
        user.save()
        
        logger.info(f"تم تغيير كلمة السر للمستخدم {user.phone} بنجاح.")
        return user
        
    

    
        

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
    


class IdentityService:
    @staticmethod
    def generate_unique_public_code(model_class, field_name, length=8):
        """توليد كود فريد مع محاولة إعادة التشغيل في حال التصادم"""
        for attempt in range(5):  # 5 محاولات كحد أقصى
            code = secrets.token_urlsafe(length)[:length].upper()
            try:
                with transaction.atomic():
                    if not model_class.objects.filter(**{field_name: code}).exists():
                        return code
            except IntegrityError:
                continue 
        raise Exception("فشل توليد كود فريد بعد عدة محاولات - خطر تصادم عالي")