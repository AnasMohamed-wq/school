from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import SmartScreen, SchoolClass

class SmartScreenService:

    @staticmethod
    @transaction.atomic
    def create_screen(manager_user, class_id, screen_name):
        """إضافة شاشة جديدة لفصل محدد داخل المدرسة."""
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        school = manager_profile.school

        # التأكد من تبعية الفصل للمدرسة
        try:
            school_class = SchoolClass.objects.get(id=class_id, school=school)
        except SchoolClass.DoesNotExist:
            raise ValidationError("الفصل المختار غير موجود ضمن مدرستك.")

        # إنشاء الشاشة (التوكن يتولد تلقائياً في الـ Model.save)
        return SmartScreen.objects.create(
            school=school,
            school_class=school_class,
            screen_name=screen_name,
            is_active=True
        )

    @staticmethod
    @transaction.atomic
    def update_screen(manager_user, screen_id, data):
        school = manager_user.schoolmanager.school
        
        try:
            screen = SmartScreen.objects.select_for_update().get(id=screen_id, school=school)
        except SmartScreen.DoesNotExist:
            raise ValidationError("الشاشة غير موجودة أو تتبع لمدرسة أخرى.")

        if 'class_id' in data:
            try:
                # التأكد أن الفصل الجديد يتبع لنفس المدرسة
                new_class = SchoolClass.objects.get(id=data['class_id'], school=school)
                screen.school_class = new_class
            except SchoolClass.DoesNotExist:
                raise ValidationError("الفصل المختار غير صالح.")

        if 'screen_name' in data:
            screen.screen_name = data['screen_name']
        
        # --- الإضافة هنا للسماح بتفعيل/تعطيل الشاشة من التعديل ---
        if 'is_active' in data:
            screen.is_active = data['is_active']

        screen.save()
        return screen

    @staticmethod
    @transaction.atomic
    def deactivate_screen(manager_user, screen_id):
        """تعطيل الشاشة."""
        school = manager_user.schoolmanager.school
        SmartScreen.objects.filter(id=screen_id, school=school).update(is_active=False)
        return True