from rest_framework import serializers
from ..models import School, SchoolClass, Student

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
