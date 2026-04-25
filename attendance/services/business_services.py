from django.db import transaction
from math import radians, cos, sin, asin, sqrt
from ..models import PickupRequest, Student , StudentStatus , StudentParent ,ClassSequence
from rest_framework.exceptions import ValidationError
from .notification_services import WSService
import logging
from django.utils import timezone


logger = logging.getLogger(__name__)

class LocationService:
    @staticmethod
    def verify_proximity(school, *, user_lat=None, user_lng=None, barcode=None, wifi_ssid=None):
        method = school.location_method

        if method == 'GPS':
            if user_lat is None or user_lng is None:
                raise ValidationError("إحداثيات الموقع مطلوبة لتفعيل الطلب عبر GPS.")
            
            try:
                lat1, lon1 = radians(float(user_lat)), radians(float(user_lng))
                lat2, lon2 = radians(float(school.location_lat)), radians(float(school.location_lng))
            except (ValueError, TypeError):
                raise ValidationError("إحداثيات غير صالحة.")

            R = 6371000  # نصف قطر الأرض بالأمتار
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            distance = 2 * asin(sqrt(a)) * R
            
            # إضافة هامش خطأ 5 أمتار لتحسين تجربة المستخدم
            if distance > (school.location_radius + 5):
                raise ValidationError(f"أنت بعيد جداً عن المدرسة. المسافة الحالية: {int(distance)} متر.")
            return True

        if method == 'BARCODE':
            if barcode != school.public_code:
                raise ValidationError("رمز الباركود غير صحيح.")
            return True

        if method == 'WIFI':
            if wifi_ssid != "SCHOOL_OFFICIAL_WIFI": # يفضل جلبها من إعدادات المدرسة في قاعدة البيانات
                raise ValidationError("يجب الاتصال بشبكة الواي فاي الخاصة بالمدرسة.")
            return True

        return False
    

class AttendanceService:
    @staticmethod
    @transaction.atomic
    def process_pickup_request(user, student_id, lat=None, lng=None, barcode=None):
        # 1. جلب الطالب مع قفل السطر (Locking)
        # ملاحظة: select_for_update() ستنتظر في PostgreSQL وتعمل كـ Guard في SQLite
        student = Student.objects.select_for_update().get(id=student_id)

        # --- الإضافة الجديدة: التحقق من ملكية الطالب ---
        is_his_child = StudentParent.objects.filter(
            student=student, 
            parent=user.parent
        ).exists()
        
        if not is_his_child:
            raise ValidationError("عذراً، هذا الطالب ليس مسجلاً ضمن أبنائك.")
        # ----------------------------------------------

        school = student.school

        # 2. التحقق الجغرافي بناءً على إعدادات المدرسة
        if not LocationService.verify_proximity(school, user_lat=lat, user_lng=lng, barcode=barcode):
            raise ValidationError("التحقق من الموقع فشل. لست في النطاق المسموح.")

        # 3. التحقق من الحالة عبر المركزية (SSoT)
        StateService.validate_transition(student.status, 'REQUESTED')

        # 4. إنشاء الطلب (القيد الفريد في الـ Model سيمنع التكرار هنا كخط دفاع أخير)
        pickup_req = PickupRequest.objects.create(
            parent=user.parent,
            student=student,
            school=school,
            status='CREATED'
        )

        # 5. تحديث الحالة
        StateService.transition_student_status(student, 'REQUESTED')

        # 6. إطلاق الـ WebSocket (Service واحدة تطلق الحدث)
        WSService.broadcast_student_update(student)

        logger.info(f"طلب استلام جديد: الطالب {student_id} من قبل ولي الأمر {user.id}")

        return pickup_req
    
    @staticmethod
    @transaction.atomic
    def update_student_and_request_status(student, new_status, teacher_user):
        # ببساطة استدعِ الدالة الموحدة
        return StateService.transition_student_status(student, new_status)
        
    


class StateService:
    @staticmethod
    def validate_transition(current, target):
        if target not in StudentStatus.TRANSITIONS.get(current, []):
            raise ValidationError(f"انتقال غير مسموح من {current} إلى {target}")
        

    @staticmethod
    @transaction.atomic
    def transition_student_status(student, new_status):
        """
        الدالة المركزية لتحديث حالة الطالب ومزامنة الطلبات وإرسال التنبيهات.
        تم دمج منطق الأمان والحفظ المضمون هنا.
        """
        # 1. قفل سطر الطالب في قاعدة البيانات لمنع التضارب (Race Condition)
        student_locked = Student.objects.select_for_update().get(id=student.id)
        current_status = student_locked.status

        # 2. التحقق من صلاحية الانتقال
        StateService.validate_transition(current_status, new_status)

        # 3. تحديث حالة الطالب والحفظ فوراً
        student_locked.change_status(new_status)
        student_locked.save(update_fields=['status'])

        # 4. مزامنة "طلب الاستلام" (PickupRequest)
        if new_status == StudentStatus.DELIVERED:
            PickupRequest.objects.filter(
                student=student_locked,
                status__in=['CREATED', 'ACCEPTED']
            ).update(
                status='COMPLETED', 
                completed_at=timezone.now()
            )
            logger.info(f"Student {student_locked.id} DELIVERED - Request COMPLETED.")
            
        elif new_status == StudentStatus.PRESENT:
            # تحديث الطلب إلى ملغي بدلاً من الحذف لضمان وجود سجل (Logs)
            PickupRequest.objects.filter(
                student=student_locked,
                status__in=['CREATED', 'ACCEPTED']
            ).update(status='CANCELLED')
            logger.info(f"Student {student_locked.id} returned to PRESENT - Request CANCELLED.")

        # 5. الجزء الأهم: إرسال التحديث للحظي (WebSocket)
        # نستخدم on_commit لضمان أن الرسالة لا تخرج إلا بعد نجاح الحفظ في الداتابيز
        transaction.on_commit(lambda: WSService.broadcast_student_update(student_locked))

        return student_locked






class StudentService:
    @staticmethod
    def get_next_student_code(school, school_class):
        """يولد كود متسلسل آمن باستخدام قفل قاعدة البيانات"""
        with transaction.atomic():
            # قفل السطر الخاص بهذا الفصل لمنع أي عملية متزامنة
            sequence, created = ClassSequence.objects.select_for_update().get_or_create(
                school=school,
                school_class=school_class
            )
            sequence.last_number += 1
            sequence.save()
            
            # تنسيق الكود: مثال (SCH1-CLS5-0001)
            return f"SCH{school.id}-CLS{school_class.id}-{str(sequence.last_number).zfill(4)}"