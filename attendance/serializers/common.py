from rest_framework import serializers
from ..models import School, SchoolClass, Student
from ..services.identity_services import AuthService

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'id',
            'name',
            'public_code',
            'location_method',
            'is_active',
        ]


class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = [
            'id',
            'name',
            'number',
            'is_active',
        ]


class StudentBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'id',
            'full_name',
            'student_code',
            'status',
        ]




class PasswordResetSerializer(serializers.Serializer):
    phone = serializers.CharField()
    national_id = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("كلمتا السر غير متطابقتين.")
        return data

    def save(self):
        # استدعاء الخدمة بدلاً من الحفظ المباشر
        return AuthService.reset_password(
            phone=self.validated_data['phone'],
            national_id=self.validated_data['national_id'],
            new_password=self.validated_data['new_password']
        )