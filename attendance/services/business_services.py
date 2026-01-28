from django.db import transaction
from math import radians, cos, sin, asin, sqrt
from ..models import PickupRequest, Student , StudentStatus
from rest_framework.exceptions import ValidationError
from .notification_services import WSService
import logging
from django.utils import timezone


logger = logging.getLogger(__name__)

class LocationService:
    @staticmethod
    def verify_proximity(school, *,user_lat=None, user_lng=None, barcode=None, wifi_ssid=None):
        """التحقق حسب الطريقة المعتمدة في المدرسة"""
        method = school.location_method

        if method == 'GPS':
            if not (user_lat and user_lng): return False
            R = 6371008.8
            lat1, lon1, lat2, lon2 = map(radians, [float(user_lat), float(user_lng), float(school.location_lat), float(school.location_lng)])
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            distance = 2 * asin(sqrt(a)) * R
            return distance <= (school.location_radius + 5)

        if method == 'BARCODE':
            return barcode == school.public_code

        if method == 'WIFI':
            # منطق التحقق من الـ SSID (يُرسل من الموبايل ويقارن بإعدادات مسبقة)
            return wifi_ssid == "SCHOOL_OFFICIAL_WIFI"

        return False
    

class AttendanceService:
    @staticmethod
    @transaction.atomic
    def process_pickup_request(user, student_id, lat=None, lng=None, barcode=None):
        # 1. جلب الطالب مع قفل السطر (Locking)
        # ملاحظة: select_for_update() ستنتظر في PostgreSQL وتعمل كـ Guard في SQLite
        student = Student.objects.select_for_update().get(id=student_id)
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
        """
        تحديث حالة الطالب ومزامنة طلب الاستلام المرتبط به تلقائياً.
        """
        current_status = student.status
        
        # 1. التحقق من صلاحية الانتقال (State Validation)
        StateService.validate_transition(current_status, new_status)

        # 2. تحديث حالة الطالب
        student.change_status(new_status)
        student.save(update_fields=['status'])

        # 3. إدارة حالة "طلب الاستلام" (PickupRequest)
        if new_status == 'DELIVERED':
            # إغلاق الطلب عند التسليم النهائي
            PickupRequest.objects.filter(
                student=student, 
                status='CREATED'
            ).update(status='COMPLETED', processed_by=teacher_user)
            
        elif new_status == 'PRESENT' and current_status == 'REQUESTED':
            # في حال إلغاء الطلب وإعادة الطالب لحالة "حاضر"
            PickupRequest.objects.filter(
                student=student, 
                status='CREATED'
            ).update(status='CANCELLED')

        # 4. إرسال التحديثات عبر الـ WebSocket
        WSService.broadcast_student_update(student)
        
        return student
    


class StateService:
    @staticmethod
    def validate_transition(current, target):
        if target not in StudentStatus.TRANSITIONS.get(current, []):
            raise ValidationError(f"انتقال غير مسموح من {current} إلى {target}")

    @staticmethod
    @transaction.atomic
    def transition_student_status(student, new_status):
        # 1. تحديث حالة الطالب أولاً
        student.change_status(new_status)
        student.save(update_fields=['status'])

        # 2. مزامنة "طلب الاستلام" (PickupRequest)
        # إذا أصبح الطالب DELIVERED، نغلق الطلب بـ COMPLETED
        if new_status == 'DELIVERED':
            PickupRequest.objects.filter(
                student=student,
                status__in=['CREATED', 'ACCEPTED'] # الحالات النشطة في الموديل عندك
            ).update(
                status='COMPLETED', 
                completed_at=timezone.now()
            )
            logger.info(f"PickupRequest for student {student.id} marked as COMPLETED.")
            
        # إذا عاد الطالب PRESENT، نلغي الطلب (يمكنك إضافة حالة CANCELLED للموديل أو حذفه)
        elif new_status == 'PRESENT':
            PickupRequest.objects.filter(
                student=student,
                status__in=['CREATED', 'ACCEPTED']
            ).delete() # أو تحويله لـ Cancelled إذا أضفتها للموديل