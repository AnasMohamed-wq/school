### 2️⃣ ClassManagementService
# تتعامل هذه الخدمة مع الكيانات داخل المدرسة مع ضمان عدم "تسريب" بيانات من مدرسة لأخرى.

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from ..models import (
    Parent, Teacher, SchoolManager, ParentSchool, 
    School, User ,SchoolClass
)
User = get_user_model()

class ClassManagementService:

    @staticmethod
    def get_manager_school(manager_user):
        """دالة مساعدة لضمان استخراج مدرسة المدير بأمان."""
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        if not manager_profile:
            raise PermissionDenied("صلاحيات غير كافية: يجب أن تكون مديراً.")
        return manager_profile.school

    @staticmethod
    @transaction.atomic
    def create_class(manager_user, name, number):
        """إنشاء فصل دراسي جديد مربوط بمدرسة المدير تلقائياً."""
        school = ClassManagementService.get_manager_school(manager_user)
        
        # التحقق من عدم تكرار رقم الفصل داخل نفس المدرسة
        if SchoolClass.objects.filter(school=school, number=number, is_active=True).exists():
            raise ValidationError(f"يوجد فصل مسجل مسبقاً بالرقم {number} في مدرستك.")

        return SchoolClass.objects.create(
            school=school,
            name=name,
            number=number,
            is_active=True 
        )

    @staticmethod
    @transaction.atomic
    def update_class(manager_user, class_id, data):
        """تحديث بيانات الفصل مع ضمان العزل التام."""
        school = ClassManagementService.get_manager_school(manager_user)
        
        # جلب الفصل مع قفل السطر وضمان تبعيته لمدرسة المدير
        try:
            school_class = SchoolClass.objects.select_for_update().get(
                id=class_id, 
                school=school
            )
        except SchoolClass.DoesNotExist:
            raise ValidationError("الفصل غير موجود أو لا يتبع لصلاحيات مدرستك.")

        # تحديث الحقول المسموحة فقط (Name, Number, Is_Active)
        # نمنع تعديل الـ School لضمان عدم نقل فصل لمدرسة أخرى
        allowed_fields = ['name', 'number', 'is_active']
        updated_fields = []
        
        for field in allowed_fields:
            if field in data:
                setattr(school_class, field, data[field])
                updated_fields.append(field)
        
        if updated_fields:
            school_class.save(update_fields=updated_fields)
            
        return school_class

    @staticmethod
    @transaction.atomic
    def deactivate_class(manager_user, class_id):
        """إيقاف نشاط الفصل (Soft Delete)."""
        school = ClassManagementService.get_manager_school(manager_user)
        
        try:
            school_class = SchoolClass.objects.select_for_update().get(
                id=class_id, 
                school=school
            )
        except SchoolClass.DoesNotExist:
            raise ValidationError("لم يتم العثور على الفصل المطلوب ضمن مدرستك.")

        school_class.is_active = False
        school_class.save(update_fields=['is_active'])
        return True