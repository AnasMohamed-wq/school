from rest_framework import serializers
from ..models import PickupRequest, Student, StudentParent
from math import radians, cos, sin, asin, sqrt
from ..services import business_services, identity_services

class CreatePickupRequestSerializer(serializers.ModelSerializer):
    # إشراك حقول الموقع الجغرافي كحقول إدخال فقط (لن تخزن في جدول الـ Request)
    lat = serializers.FloatField(write_only=True)
    lng = serializers.FloatField(write_only=True)

    class Meta:
        model = PickupRequest
        fields = ['student', 'lat', 'lng']

    def validate(self, attrs):
        user = self.context['request'].user
        student = attrs['student']
        
        # (2.3) حماية الافتراضات: التأكد من وجود بروفايل ولي أمر
        if not hasattr(user, 'parent'):
            raise serializers.ValidationError("عذراً، حسابك لا يمتلك صلاحيات ولي أمر (Profile Missing).")

        # التحقق من التبعية والموقع يتم هنا عبر استدعاء الخدمات (بدون تغيير بيانات)
        # ملاحظة: التحقق من "هل يوجد طلب نشط؟" سيتم داخل الـ Service لاحقاً لضمان الـ Race Condition
        return attrs

    def create(self, validated_data):
        """
        تعطيل الـ Create الافتراضي. 
        يتم استدعاء AttendanceService.process_pickup_request من الـ View بدلاً من هنا.
        """
        raise NotImplementedError("استخدم AttendanceService لإنشاء الطلب.")