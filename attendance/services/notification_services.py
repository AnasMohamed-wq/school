from asgiref.sync import async_to_sync


class WSService:
    @staticmethod
    def broadcast_student_update(student):
        from channels.layers import get_channel_layer
        if not student.school_class:
            return
        
        channel_layer = get_channel_layer()
        # توحيد اسم المجموعة: school_{id}_class_{id}
        group_name = f"school_{student.school.id}_class_{student.school_class.id}"
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "pickup_update",
                "student_id": student.id,
                "full_name": student.full_name,
                "status": student.status,
            }
        )

    @staticmethod
    def notify_teacher(teacher_user_id, message):
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        # تصحيح الخطأ (13): إضافة teacher_ لضمان التطابق مع Consumer
        async_to_sync(channel_layer.group_send)(
            f"teacher_user_{teacher_user_id}",
            {
                "type": "notification",
                "message": message
            }
        )