import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from urllib.parse import parse_qs
from .models import SmartScreen, Student



class SmartScreenConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # استخراج التوكن من Query String
        query_string = self.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if not token:
            await self.close(code=4003)
            return

        screen = await self.verify_screen(token)

        if not screen:
            await self.close(code=4003)
            return

        # حفظ السياق
        self.school_id = screen["school_id"]
        self.class_id = screen["class_id"]

        # اسم مجموعة موحد وواضح
        self.group_name = f"school_{self.school_id}_class_{self.class_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # إرسال الحالة الأولية مباشرة بعد الاتصال
        await self.send_initial_students()


    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

        print(f"[SmartScreen] disconnected ({close_code})")


    @database_sync_to_async
    def verify_screen(self, token):
        try:
            screen = SmartScreen.objects.select_related(
                "school", "school_class"
            ).get(
                screen_token=token,
                is_active=True
            )

            # تحقق أمني صارم
            if not screen.school_class:
                return None

            if screen.school_class.school_id != screen.school_id:
                return None

            return {
                "school_id": screen.school_id,
                "class_id": screen.school_class_id
            }

        except SmartScreen.DoesNotExist:
            return None




    async def pickup_update(self, event):
        await self.send(text_data=json.dumps({
            "action": "UPDATE_STUDENT_STATUS",
            "student_id": event["student_id"],
            "full_name": event["full_name"],
            "status": event["status"],
        }))


    @database_sync_to_async
    def get_initial_students(self):
        students = Student.objects.filter(
            school_id=self.school_id,
            school_class_id=self.class_id,
            is_active=True
        )

        return [
            {
                "student_id": s.id,
                "full_name": s.full_name,
                "status": s.status,
            }
            for s in students
        ]



    async def send_initial_students(self):
        students = await self.get_initial_students()

        await self.send(text_data=json.dumps({
            "action": "INITIAL_SYNC",
            "students": students
        }))


class TeacherConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")

        # التحقق من الهوية والدور
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4003)
            return

        if self.user.role != "TEACHER":
            await self.close(code=4003)
            return

        try:
            # جلب بيانات الفصل (المدرسة والفصل المرتبط بالمعلم)
            teacher_info = await self.get_teacher_data()
            self.school_id = teacher_info['school_id']
            self.class_id = teacher_info['class_id']
            
            # 1. مجموعة التنبيهات الخاصة بالمعلم (رسائل شخصية)
            self.teacher_group = f"teacher_user_{self.user.id}"
            await self.channel_layer.group_add(self.teacher_group, self.channel_name)

            # 2. مجموعة الفصل (لمراقبة الطلاب وتحديثاتهم)
            self.class_group = f"school_{self.school_id}_class_{self.class_id}"
            await self.channel_layer.group_add(self.class_group, self.channel_name)

            await self.accept()
            
            # 3. إرسال الحالة الأولية (جميع طلاب الفصل) فور الاتصال [تلبية لطلبك]
            await self.send_initial_students()

            # تأكيد نجاح الاتصال
            await self.send(text_data=json.dumps({
                "action": "CONNECTION_SUCCESS",
                "message": f"Welcome Teacher {self.user.id}",
                "monitoring_group": self.class_group
            }))

        except Exception as e:
            # طباعة الخطأ في التيرمينال لمعرفة السبب الحقيقي (مثل عدم وجود Teacher Profile)
            print(f"Error in Teacher connect: {e}")
            await self.close(code=1011) # خطأ داخلي في السيرفر

    @database_sync_to_async
    def get_teacher_data(self):
        # التأكد من وجود بروفايل للمعلم لتجنب الـ Abnormal Closure
        # ملاحظة: استخدمت getattr لتجنب توقف الكود إذا لم يوجد البروفايل
        teacher_profile = getattr(self.user, 'teacher', None)
        if not teacher_profile:
            raise Exception("المستخدم مسجل كمعلم ولكن ليس لديه بيانات (Teacher Profile) مرتبطة")
            
        return {
            "school_id": teacher_profile.school_id,
            "class_id": teacher_profile.school_class_id
        }

    @database_sync_to_async
    def get_class_students(self):
        """جلب جميع طلاب الفصل الحالي"""
        students = Student.objects.filter(
            school_class_id=self.class_id,
            is_active=True
        )
        return [
            {
                "student_id": s.id,
                "full_name": s.full_name,
                "status": s.status,
            }
            for s in students
        ]

    async def send_initial_students(self):
        """إرسال القائمة الكاملة للطلاب عند الاتصال الأول"""
        students = await self.get_class_students()
        await self.send(text_data=json.dumps({
            "action": "INITIAL_SYNC",
            "students": students
        }))

    async def pickup_update(self, event):
        """استقبال تحديثات الطلاب اللحظية"""
        await self.send(text_data=json.dumps({
            "action": "UPDATE_STUDENT_STATUS",
            "student_id": event["student_id"],
            "full_name": event["full_name"],
            "status": event["status"],
        }))

    async def notification(self, event):
        """استقبال التنبيهات الخاصة (رسائل من النظام)"""
        await self.send(text_data=json.dumps({
            "action": "NEW_NOTIFICATION",
            "message": event["message"]
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "teacher_group"):
            await self.channel_layer.group_discard(self.teacher_group, self.channel_name)
        if hasattr(self, "class_group"):
            await self.channel_layer.group_discard(self.class_group, self.channel_name)