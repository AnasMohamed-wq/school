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

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        if self.user.role != "TEACHER":
            await self.close()
            return

        self.group_name = f"teacher_user_{self.user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "NEW_PICKUP_REQUEST",
            "message": event["message"]
        }))

