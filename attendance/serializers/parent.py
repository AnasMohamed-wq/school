from rest_framework import serializers
from ..models import (
    Student,
    PickupRequest,
    School,
)

class ParentSchoolStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'id',
            'name',
        ]


class ParentStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'id',
            'full_name',
            'status',
        ]


class ParentPickupRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupRequest
        fields = [
            'id',
            'status',
            'requested_at',
            'accepted_at',
            'completed_at',
        ]
