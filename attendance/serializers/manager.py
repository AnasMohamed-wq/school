from rest_framework import serializers
from ..models import (
    Student,
    Parent,
    Teacher,
    ParentSchool,
    StudentParent,
    User
)
from .common import SchoolClassSerializer
from django.db import transaction


class ManagerStudentSerializer(serializers.ModelSerializer):
    school_class = SchoolClassSerializer(read_only=True)

    class Meta:
        model = Student
        fields = [
            'id',
            'full_name',
            'student_code',
            'status',
            'school_class',
            'is_active',
        ]

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'phone']


class ManagerParentSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='user.full_name')
    phone = serializers.ReadOnlyField(source='user.phone')
    user= UserUpdateSerializer()

    class Meta:
        model = Parent
        fields = [
            'id',
            'full_name',
            'phone',
            'is_active',
            'user',


        ]


    def update(self, instance, validated_data):
        with transaction.atomic():
            if not hasattr(instance, 'user'):
                raise serializers.ValidationError("خطأ خطير: لا يوجد مستخدم مرتبط بولي الأمر هذا.")
            # 1. استخراج بيانات المستخدم من البيانات المرسلة
            user_data = validated_data.pop('user', {})
            user = instance.user

            # 2. تحديث بيانات موديل User
            if user_data:
                user.full_name = user_data.get('full_name', user.full_name)
                new_phone = user_data.get('phone')
                if new_phone and new_phone != user.phone:
                    if User.objects.filter(phone=new_phone).exists():
                        raise serializers.ValidationError({"phone": "رقم الهاتف مسجل لمستخدم آخر."})
                    user.phone = new_phone
                user.save()

            instance.is_active = validated_data.get('is_active', instance.is_active)
            instance.save()
        return instance

        


class ManagerParentSchoolSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.user.full_name', read_only=True)

    class Meta:
        model = ParentSchool
        fields = [
            'id',
            'parent_name',
            'parent_school_token',
            'is_approved',
            'approved_at',
        ]


class ManagerTeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='user.full_name')
    school_class_name = serializers.StringRelatedField(source='school_class', read_only=True)

    class Meta:
        model = Teacher
        fields = [
            'id',
            'full_name',
            'school_class',
            'school_class_name',
            'is_active',
        ]
