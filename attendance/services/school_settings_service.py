from django.db import transaction
from django.core.exceptions import ValidationError

class SchoolSettingsService:

    @staticmethod
    @transaction.atomic
    def update_location_settings(manager_user, data):
        """تحديث إعدادات الموقع الجغرافي للمدرسة."""
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        school = manager_profile.school # عزل تلقائي: التعديل يتم على مدرسة المدير فقط

        # 1. تحديث الطريقة (GPS / WIFI / BARCODE)
        location_method = data.get('location_method', school.location_method)
        
        # 2. قواعد التحقق (Validation Rules)
        if location_method == 'GPS':
            lat = data.get('location_lat')
            lng = data.get('location_lng')
            if lat is None or lng is None:
                raise ValidationError("عند اختيار GPS، يجب إدخال الإحداثيات (Lat & Lng).")
            
            school.location_lat = lat
            school.location_lng = lng

        # 3. تحديث باقي الحقول
        school.location_method = location_method
        school.location_radius = data.get('location_radius', school.location_radius)
        
        school.save()
        return school