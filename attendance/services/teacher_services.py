from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from ..models import Teacher, SchoolClass, User

User = get_user_model()

class TeacherManagementService:

    @staticmethod
    def _get_manager_school(manager_user):
        """استخراج مدرسة المدير بآمان لضمان العزل التام."""
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        if not manager_profile:
            raise PermissionDenied("ليس لديك صلاحيات مدير مدرسة.")
        return manager_profile.school

    @staticmethod
    @transaction.atomic
    def create_teacher(manager_user, full_name, phone, national_id=None):
        """إنشاء معلم جديد مع تشفير كلمة المرور وضمان العزل."""
        school = TeacherManagementService._get_manager_school(manager_user)

        # 1. البحث أو الإنشاء (مع قفل السطر)
        user, created = User.objects.select_for_update().get_or_create(
            phone=phone,
            defaults={
                'full_name': full_name, 
                'role': 'TEACHER',
                'national_id': national_id
            }
        )

        # 2. إذا كان جديداً، نشفر كلمة المرور فوراً
        if created:
            user.set_password(phone)
            user.save()
        else:
            # تنبيه: الرقم موجود بدور مختلف
            if user.role != 'TEACHER':
                raise ValidationError(f"هذا الرقم مسجل مسبقاً بدور {user.role}. لا يمكن تعيينه كمعلم.")
            # تحديث الهوية إذا كانت ناقصة (اختياري حسب رغبتك)
            if national_id and not user.national_id:
                user.national_id = national_id
                user.save(update_fields=['national_id'])

        # 3. قيود مدرسة المعلم (SSoT)
        existing_teacher = Teacher.objects.filter(user=user).first()
        if existing_teacher:
            if existing_teacher.school == school:
                raise ValidationError("هذا المعلم مسجل بالفعل في مدرستك.")
            else:
                raise ValidationError(f"هذا المعلم مرتبط بمدرسة ({existing_teacher.school.name})، لا يمكن ربطه بمدرستين.")

        # 4. إنشاء بروفايل المعلم
        return Teacher.objects.create(user=user, school=school, is_active=True)
    

    @staticmethod
    @transaction.atomic
    def assign_teacher_to_class(manager_user, teacher_id, class_id):
        """ربط المعلم بفصل دراسي محدد داخل نفس المدرسة."""
        school = TeacherManagementService._get_manager_school(manager_user)

        # التحقق من أن المعلم والفصل يتبعان لمدرسة المدير
        teacher = Teacher.objects.select_for_update().filter(id=teacher_id, school=school).first()
        school_class = SchoolClass.objects.filter(id=class_id, school=school).first()

        if not teacher or not school_class:
            raise ValidationError("المعلم أو الفصل غير موجود ضمن نطاق مدرستك.")

        teacher.school_class = school_class
        teacher.save(update_fields=['school_class'])
        return teacher

    @staticmethod
    @transaction.atomic
    def deactivate_teacher(manager_user, teacher_id):
        """إيقاف نشاط المعلم داخل المدرسة (Soft Delete)."""
        school = TeacherManagementService._get_manager_school(manager_user)
        
        teacher = Teacher.objects.select_for_update().filter(id=teacher_id, school=school).first()
        if not teacher:
            raise ValidationError("المعلم غير موجود أو لا يتبع لمدرستك.")

        teacher.is_active = False
        teacher.save(update_fields=['is_active'])
        return True
    
    @staticmethod
    @transaction.atomic
    def transfer_teacher_to_class(manager_user, teacher_id, new_class_id):
        """نقل المعلم من فصل إلى آخر أو تعيينه لأول مرة."""
        school = TeacherManagementService._get_manager_school(manager_user)
        teacher = Teacher.objects.select_for_update().get(id=teacher_id, school=school)
        
        if new_class_id:
            new_class = SchoolClass.objects.get(id=new_class_id, school=school)
            teacher.school_class = new_class
        else:
            teacher.school_class = None # فك الارتباط بالفصل
            
        teacher.save(update_fields=['school_class'])
        return teacher

    @staticmethod
    @transaction.atomic
    def unlink_teacher_from_school(manager_user, teacher_id):
        """فك ارتباط المعلم بالمدرسة نهائياً (حذف البروفايل الخاص بالمدرسة)."""
        school = TeacherManagementService._get_manager_school(manager_user)
        teacher = Teacher.objects.get(id=teacher_id, school=school)
        teacher.delete() # نحذف بروفايل المعلم في هذه المدرسة فقط، ويبقى المستخدم (User) موجوداً
        return True
    


    @staticmethod
    @transaction.atomic
    def update_teacher(manager_user, teacher_id, data):
        """تحديث بيانات الأستاذ الشاملة (الاسم، الهاتف، الهوية)."""
        school = TeacherManagementService._get_manager_school(manager_user)
        
        # التأكد من أن الأستاذ يتبع لمدرسة المدير
        teacher = Teacher.objects.select_for_update().filter(id=teacher_id, school=school).first()
        if not teacher:
            raise PermissionDenied("لا تملك صلاحية تعديل بيانات هذا الأستاذ.")

        user = teacher.user
        update_fields = []

        if 'full_name' in data:
            user.full_name = data['full_name']
            update_fields.append('full_name')
        
        if 'phone' in data:
            if User.objects.filter(phone=data['phone']).exclude(id=user.id).exists():
                raise ValidationError("رقم الهاتف مسجل لمستخدم آخر.")
            user.phone = data['phone']
            update_fields.append('phone')
            
        if 'national_id' in data:
            user.national_id = data['national_id']
            update_fields.append('national_id')

        if update_fields:
            user.save(update_fields=update_fields)
        
        return teacher