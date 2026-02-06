import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from .models import SmartScreen, Student
import logging

logger = logging.getLogger(__name__)

class SmartScreenConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. استخراج التوكن من Query String
        query_string = self.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

     
        school_id = query_params.get("school_id", [None])[0]
        class_id = query_params.get("class_id", [None])[0]

        # قبول الاتصال أولاً ليتمكن السيرفر من إرسال رسائل JSON بالخطأ قبل الإغلاق
        await self.accept()

        if not all([token, school_id, class_id]):
            await self.send_error("MISSING_PARAMS", "التوكن، معرف المدرسة، ومعرف الفصل جميعها مطلوبة")
            await self.close(code=4003)
            return

        # 2. التحقق من التوكن وجلب بيانات الشاشة
        screen = await self.verify_screen(token , school_id, class_id)

        if not screen:
            await self.send_error("INVALID_TOKEN", "توكن الشاشة غير صالح أو غير نشط")
            await self.close(code=4003)
            return

        # 3. تثبيت "مصدر الحقيقة" من التوكن حصراً (SSoT)
        self.school_id = screen["school_id"]
        self.class_id = screen["class_id"]

        self.group_name = f"school_{self.school_id}_class_{self.class_id}"

        # 4. الانضمام للمجموعة وإرسال الحالة الأولية
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        # إرسال تأكيد نجاح الاتصال (مفيد جداً للمبرمج)
        await self.send(text_data=json.dumps({
            "action": "CONNECTION_ESTABLISHED",
            "message": "تم الاتصال بنجاح بمجموعة الفصل"
        }))

        await self.send_initial_students()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        if close_code != 1000:
            logger.warning(f"SmartScreen WebSocket disconnected abnormally. Code: {close_code}, School: {getattr(self, 'school_id', 'Unknown')}")
        else:
            logger.info(f"SmartScreen WebSocket closed normally. Code: {close_code}")

    @database_sync_to_async
    def verify_screen(self, token, school_id, class_id):
        try:
            screen = SmartScreen.objects.select_related("school_class").get(
                screen_token=token,
                school_id=school_id,
                school_class_id=class_id,
                is_active=True
            )
            return {
                "school_id": screen.school_id,
                "class_id": screen.school_class_id
            }
        except SmartScreen.DoesNotExist:
            return None
        
    @database_sync_to_async
    def get_initial_students(self):
        # المحور الثالث: حل مشكلة N+1 بجلب الحقول المطلوبة فقط كـ list of dicts
        return list(Student.objects.filter(
            school_id=self.school_id,
            school_class_id=self.class_id,
            status__in=['PRESENT', 'REQUESTED', 'AT_GATE'], # استثناء DELIVERED
            is_active=True
        ).values('id', 'full_name', 'status'))

    async def send_initial_students(self):
        students = await self.get_initial_students()
        await self.send(text_data=json.dumps({
            "action": "INITIAL_SYNC",
            "students": students
        }))

    async def pickup_update(self, event):
        """يستدعى عند وجود تحديث من الـ Service عبر Redis"""
        await self.send(text_data=json.dumps({
            "action": "UPDATE_STUDENT_STATUS",
            "student_id": event["student_id"],
            "full_name": event["full_name"],
            "status": event["status"],
        }))

    async def send_error(self, code, message):
        """دالة مساعدة لإرسال أخطاء واضحة قبل إغلاق القناة"""
        await self.send(text_data=json.dumps({
            "action": "ERROR",
            "code": code,
            "message": message
        }))


class TeacherConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")

        # 1. قبول الاتصال المبدئي لإرسال رسائل JSON عند وجود خلل
        await self.accept()

        # 2. التحقق من الهوية والصلاحيات
        if not self.user or not self.user.is_authenticated:
            await self.send_error("AUTH_FAILED", "يجب تسجيل الدخول للوصول لهذه القناة")
            await self.close(code=4003)
            return

        if self.user.role != "TEACHER":
            await self.send_error("PERMISSION_DENIED", "هذه القناة مخصصة للمعلمين فقط")
            await self.close(code=4003)
            return

        try:
            # 3. جلب بيانات المعلم (المدرسة والفصل)
            teacher_info = await self.get_teacher_data()
            self.school_id = teacher_info['school_id']
            self.class_id = teacher_info['class_id']
            
            # 4. مجموعات الاشتراك
            self.teacher_group = f"teacher_user_{self.user.id}" # تنبيهات خاصة
            self.class_group = f"school_{self.school_id}_class_{self.class_id}" # تحديثات الطلاب

            await self.channel_layer.group_add(self.teacher_group, self.channel_name)
            await self.channel_layer.group_add(self.class_group, self.channel_name)

            # 5. تأكيد النجاح وإرسال الحالة الأولية
            await self.send(text_data=json.dumps({
                "action": "CONNECTION_SUCCESS",
                "message": f"أهلاً بك يا أستاذ {self.user.full_name}",
            }))

            await self.send_initial_students()

        except Exception as e:
            # معالجة حالة المعلم الذي لا يملك ملف بيانات (Teacher Profile)
            await self.send_error("PROFILE_MISSING", str(e))
            await self.close(code=1011)

    @database_sync_to_async
    def get_teacher_data(self):
        teacher_profile = getattr(self.user, 'teacher', None)
        if not teacher_profile:
            raise Exception("حسابك غير مرتبط بملف معلم أو فصل دراسي.")
        if not teacher_profile.school_class_id:
            raise Exception("لم يتم تعيين فصل دراسي لحسابك بعد.")
            
        return {
            "school_id": teacher_profile.school_id,
            "class_id": teacher_profile.school_class_id
        }

    @database_sync_to_async
    def get_class_students(self):
        """تحسين المحور الثالث: جلب بيانات الطلاب بفعالية عالية"""
        return list(Student.objects.filter(
            school_class_id=self.class_id,
            is_active=True
        ).values('id', 'full_name', 'status'))

    async def send_initial_students(self):
        students = await self.get_class_students()
        await self.send(text_data=json.dumps({
            "action": "INITIAL_SYNC",
            "students": students
        }))

    async def pickup_update(self, event):
        """تحديث لحظي لحالة طالب (يصل من الـ Service)"""
        await self.send(text_data=json.dumps({
            "action": "UPDATE_STUDENT_STATUS",
            "student_id": event["student_id"],
            "full_name": event["full_name"],
            "status": event["status"],
        }))

    async def notification(self, event):
        """رسائل إدارية أو تنبيهات خاصة للمعلم فقط"""
        await self.send(text_data=json.dumps({
            "action": "NEW_NOTIFICATION",
            "message": event["message"]
        }))

    async def send_error(self, code, message):
        """إرسال رسالة خطأ مهيكلة لمطور الفرونت إند"""
        await self.send(text_data=json.dumps({
            "action": "ERROR",
            "code": code,
            "message": message
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "teacher_group"):
            await self.channel_layer.group_discard(self.teacher_group, self.channel_name)
        if hasattr(self, "class_group"):
            await self.channel_layer.group_discard(self.class_group, self.channel_name)