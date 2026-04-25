from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from ..models import (
    Student, SchoolClass, Parent, ParentSchool, 
    StudentParent, User
)

User = get_user_model()

class StudentManagementService:

    @staticmethod
    def _get_manager_school(manager_user):
        """دالة حماية لاستخراج مدرسة المدير ومنع العمليات خارج الصلاحية."""
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        if not manager_profile:
            raise PermissionDenied("يجب أن تكون مديراً مسجلاً للقيام بهذه العملية.")
        return manager_profile.school

    @staticmethod
    @transaction.atomic
    def create_student(manager_user, full_name, class_id):
        """إنشاء طالب جديد مع ضمان تبعية الفصل للمدرسة."""
        school = StudentManagementService._get_manager_school(manager_user)
        
        # التأكد أن الفصل يتبع لنفس مدرسة المدير (الحماية من الثغرات)
        try:
            school_class = SchoolClass.objects.get(id=class_id, school=school)
        except SchoolClass.DoesNotExist:
            raise ValidationError("الفصل المختار غير موجود أو لا يتبع لمدرستك.")

        return Student.objects.create(
            school=school, # السورس الوحيد للحقيقة هو مدرسة المدير
            school_class=school_class,
            full_name=full_name
        )

    @staticmethod
    @transaction.atomic
    def update_student(manager_user, student_id, data):
        """تحديث بيانات الطالب مع منع تغيير مدرسته."""
        school = StudentManagementService._get_manager_school(manager_user)
        
        # جلب الطالب بشرط المدرسة لضمان العزل
        try:
            student = Student.objects.select_for_update().get(id=student_id, school=school)
        except Student.DoesNotExist:
            raise ValidationError("الطالب غير موجود ضمن نطاق مدرستك.")

        # السماح بتحديث حقول محددة فقط
        allowed_fields = ['full_name', 'is_active']
        for field in allowed_fields:
            if field in data:
                setattr(student, field, data[field])
        
        student.save(update_fields=allowed_fields)
        return student

    @staticmethod
    @transaction.atomic
    def transfer_student(manager_user, student_id, new_class_id):
        """نقل طالب بين الفصول داخل نفس المدرسة."""
        school = StudentManagementService._get_manager_school(manager_user)

        # التأكد من وجود الطالب والفصل الجديد في مدرسة المدير
        student = Student.objects.select_for_update().filter(id=student_id, school=school).first()
        new_class = SchoolClass.objects.filter(id=new_class_id, school=school).first()

        if not student or not new_class:
            raise ValidationError("تعذر إكمال النقل: الطالب أو الفصل لا ينتمي لمدرستك.")

        student.school_class = new_class
        student.save(update_fields=['school_class'])
        return student

    @staticmethod
    @transaction.atomic
    def assign_parent_to_student(manager_user, student_id, parent_phone, parent_name):
        """ربط ولي الأمر بالطالب وإنشاء حساب له إذا لم يكن موجوداً."""
        school = StudentManagementService._get_manager_school(manager_user)
        
        # 1. التأكد من تبعية الطالب للمدرسة
        student = Student.objects.get(id=student_id, school=school)

        # 2. البحث عن المستخدم أو إنشاؤه (Global User)
        user, created = User.objects.select_for_update().get_or_create(
            phone=parent_phone,
            defaults={'full_name': parent_name, 'role': 'PARENT'}
        )

        if not created and user.role != 'PARENT':
            raise ValidationError(f"هذا الرقم مسجل مسبقاً بدور {user.role} ولا يمكن استخدامه كولي أمر.")

        # 3. التأكد من وجود بروفايل Parent
        parent, _ = Parent.objects.get_or_create(user=user)

        # 4. ربط ولي الأمر بالمدرسة (ParentSchool) لتمكينه من الدخول للمدرسة الحالية
        ParentSchool.objects.get_or_create(
            parent=parent,
            school=school,
            defaults={'is_approved': True, 'approved_by': manager_user}
        )

        # 5. الربط بين الطالب وولي الأمر (StudentParent) مع منع التكرار
        sp_obj, sp_created = StudentParent.objects.get_or_create(
            student=student,
            parent=parent
        )

        return sp_obj