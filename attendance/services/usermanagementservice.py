from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password # لاستخدام التشفير اليدوي إذا لزم الأمر

from ..models import (
    Parent, Teacher, SchoolManager, ParentSchool, 
    School, User
)

User = get_user_model()


class UserManagementService:

    @staticmethod
    def _get_manager_school(manager_user):
        """دالة مساعدة لضمان العزل الأمني واستخراج مدرسة المدير."""
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        if not manager_profile or not manager_profile.is_active:
            raise PermissionDenied("المستخدم ليس مديراً نشطاً لمدرسة.")
        return manager_profile.school

    @staticmethod
    @transaction.atomic
    def create_or_link_parent(manager_user, full_name, phone, national_id=None):
        """
        خاص بولي الأمر: 
        1. ينشئ مستخدم جديد بكلمة مرور مشفرة (رقم الهاتف) إذا لم يوجد.
        2. يربط المستخدم بالمدرسة الحالية إذا كان ولي أمر مسجل مسبقاً.
        3. يحدث رقم الهوية إذا كان مفقوداً.
        """
        target_school = UserManagementService._get_manager_school(manager_user)

        # 1. البحث عن المستخدم أو إنشاؤه مع قفل السطر للحماية
        user, created = User.objects.select_for_update().get_or_create(
            phone=phone,
            defaults={
                'full_name': full_name, 
                'role': 'PARENT',
                'national_id': national_id
            }
        )

        if created:
            # تشفير كلمة المرور فور الإنشاء (رقم الهاتف ككلمة مرور افتراضية)
            user.set_password(phone)
            user.save()
        else:
            # 2. التحقق من دور المستخدم الموجود مسبقاً
            if user.role != 'PARENT':
                raise ValidationError(f"هذا الرقم مسجل مسبقاً بدور {user.role}. لا يمكن ربطه كولي أمر.")
            
            # 3. تحديث الهوية الوطنية إذا كانت فارغة في السجل الموجود
            if national_id and not user.national_id:
                user.national_id = national_id
                user.save(update_fields=['national_id'])

        # 4. التأكد من وجود بروفايل ولي أمر (Parent Profile)
        parent, _ = Parent.objects.get_or_create(user=user)

        # 5. ربط ولي الأمر بالمدرسة (علاقة Many-to-Many)
        # نستخدم get_or_create لمنع تكرار الربط وللسماح بالربط بأكثر من مدرسة
        ParentSchool.objects.get_or_create(
            parent=parent, 
            school=target_school,
            defaults={'is_approved': False} # تتطلب اعتماد المدير لاحقاً
        )
        
        return user
    

    @staticmethod
    @transaction.atomic
    def create_or_link_user(manager_user, full_name, phone, role, national_id=None):

        manager_profile = getattr(manager_user, 'schoolmanager', None)
        if not manager_profile or not manager_profile.is_active:
            raise PermissionDenied("المستخدم ليس مديراً نشطاً لمدرسة.")
        
        target_school = manager_profile.school

    
        user = User.objects.select_for_update().filter(phone=phone).first()
        created = False

        if not user:
            # إنشاء مستخدم جديد بكلمة مرور مشفرة
            user = User.objects.create(
                phone=phone,
                full_name=full_name,
                role=role,
                national_id=national_id,
                is_active=True
            )
            # تعيين رقم الهاتف ككلمة مرور افتراضية وتشفيرها
            # دالة set_password تتكفل بالتشفير (Hashing) المتوافق مع Django
            user.set_password(phone) 
            user.save()
            created = True
        else:
            # إذا كان المستخدم موجوداً، نقوم بتحديث الهوية إذا كانت فارغة
            if national_id and not user.national_id:
                user.national_id = national_id
                user.save(update_fields=['national_id'])

        # 3. التحقق من قواعد الدور (Business Rules)
        UserManagementService.validate_role_rules(user, role, target_school, is_new=created)

        # 4. معالجة الـ Profile والربط
        if role == 'PARENT':
            parent, _ = Parent.objects.get_or_create(user=user)
            UserManagementService.link_parent_to_school(parent, target_school)
            
        elif role == 'TEACHER':
            UserManagementService.create_teacher_for_school(user, target_school)
            
        return user
    

    @staticmethod
    def validate_role_rules(user, role, school, is_new):
        """
        محرك التحقق من قوانين العمل (Business Rules Validation).
        """
        # إذا كان المستخدم موجوداً مسبقاً، يمنع تغيير دوره الأساسي
        if not is_new and user.role != role:
            raise ValidationError(f"المستخدم مسجل مسبقاً بدور {user.role}، لا يمكن تغييره إلى {role}.")

        if role == 'TEACHER':
            # المعلم ينتمي لمدرسة واحدة فقط (حسب المتطلبات)
            teacher_profile = getattr(user, 'teacher', None)
            if teacher_profile and teacher_profile.school != school:
                raise ValidationError(f"هذا المعلم مرتبط بالفعل بمدرسة أخرى: {teacher_profile.school.name}")

    @staticmethod
    def link_parent_to_school(parent, school):
        """
        ربط ولي الأمر بالمدرسة (علاقة Many-to-Many عبر ParentSchool).
        """
        ParentSchool.objects.get_or_create(
            parent=parent,
            school=school,
            defaults={'is_approved': False} # التسجيل يتطلب موافقة لاحقة
        )

    @staticmethod
    def create_teacher_for_school(user, school):
        """
        إنشاء بروفايل معلم وربطه بمدرسة المدير حصراً.
        """
        teacher_profile = getattr(user, 'teacher', None)
        
        if not teacher_profile:
            Teacher.objects.create(user=user, school=school, is_active=True)
        else:
            # إذا كان موجوداً، نتحقق أنه لنفس المدرسة (إضافة طبقة حماية)
            if teacher_profile.school != school:
                raise ValidationError("المعلم مسجل في مدرسة مختلفة.")


