from rest_framework import serializers
from ..models import PickupRequest, Student


class TeacherPickupRequestSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.user.full_name', read_only=True)

    class Meta:
        model = PickupRequest
        fields = [
            'id',
            'student_id',
            'student_name',
            'parent_name',
            'status',
            'requested_at',
        ]


class TeacherStudentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'id',
            'full_name',
            'status',
        ]
        
class StudentActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['REQUESTED', 'AT_GATE', 'DELIVERED', 'PRESENT'])
