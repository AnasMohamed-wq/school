from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from ..models import ParentSchool, Parent

class ParentManagementService:

    @staticmethod
    def _get_manager_school(manager_user):
        manager_profile = getattr(manager_user, 'schoolmanager', None)
        if not manager_profile:
            raise PermissionDenied("يجب أن تكون مديراً للوصول لبيانات أولياء الأمور.")
        return manager_profile.school
    

    @staticmethod
    @transaction.atomic
    def approve_parent_school(manager_user, parent_school_id):
        """اعتماد انضمام ولي الأمر للمدرسة."""
        school = ParentManagementService._get_manager_school(manager_user)

        try:
            # جلب طلب الربط الخاص بهذه المدرسة حصراً
            ps_request = ParentSchool.objects.select_for_update().get(
                id=parent_school_id, 
                school=school
            )
        except ParentSchool.DoesNotExist:
            raise ValidationError("طلب الارتباط غير موجود ضمن مدرستك.")

        ps_request.is_approved = True
        ps_request.approved_by = manager_user
        ps_request.approved_at = timezone.now()
        ps_request.save()
        
        return ps_request

    @staticmethod
    def get_parents_for_school(manager_user):
        """جلب قائمة أولياء الأمور المرتبطين بالمدرسة الحالية فقط."""
        school = ParentManagementService._get_manager_school(manager_user)
        
        # نرجع العلاقة ParentSchool لأنها تحتوي على بيانات الموافقة والارتباط بالمدرسة
        return ParentSchool.objects.filter(school=school).select_related('parent__user')

    @staticmethod
    @transaction.atomic
    def update_parent(manager_user, parent_id, data):
        """تحديث بيانات ولي الأمر (الاسم، الهاتف، الهوية)."""
        school = ParentManagementService._get_manager_school(manager_user)

        # التأكد من التبعية للمدرسة
        if not ParentSchool.objects.filter(parent_id=parent_id, school=school).exists():
            raise PermissionDenied("لا تملك صلاحية تعديل بيانات هذا المستخدم.")

        try:
            parent = Parent.objects.get(id=parent_id)
            user = parent.user
        except (Parent.DoesNotExist, User.DoesNotExist):
            raise ValidationError("بيانات ولي الأمر غير موجودة.")

        # الحقول المسموح بتحديثها في موديل User
        update_fields = []
        if 'full_name' in data:
            user.full_name = data['full_name']
            update_fields.append('full_name')
        
        if 'phone' in data:
            # نتحقق من عدم وجود رقم الهاتف لمستخدم آخر
            if User.objects.filter(phone=data['phone']).exclude(id=user.id).exists():
                raise ValidationError("رقم الهاتف مسجل لمستخدم آخر بالفعل.")
            user.phone = data['phone']
            update_fields.append('phone')
            
        if 'national_id' in data:
            user.national_id = data['national_id']
            update_fields.append('national_id')

        if update_fields:
            user.save(update_fields=update_fields)
        
        return parent