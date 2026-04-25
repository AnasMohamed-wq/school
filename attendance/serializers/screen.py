from rest_framework import serializers
from ..models import Student

class SmartScreenStudentSerializer(serializers.ModelSerializer):
    # إضافة زمن الطلب واسم ولي الأمر للشاشة الذكية
    request_time = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'status', 'request_time', 'parent_name']

    def get_request_time(self, obj):
        last_request = obj.pickuprequest_set.filter(status__in=['CREATED', 'ACCEPTED']).last()
        if last_request:
            # تحويل الوقت إلى نص بصيغة الساعات والدقائق
            return last_request.requested_at.strftime('%H:%M') 
        return None

    def get_parent_name(self, obj):
        last_request = obj.pickuprequest_set.filter(status__in=['CREATED', 'ACCEPTED']).last()
        return last_request.parent.user.full_name if last_request else "غير محدد"