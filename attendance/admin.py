import uuid
from django.utils import timezone
from django.contrib import admin, messages
from .models import (
    User, School, SchoolManager, SchoolClass, Teacher, 
    Parent, ParentSchool, Student, StudentParent, 
    PickupRequest, SmartScreen
)




# --- دالة مساعدة للحصول على مدرسة المستخدم الحالي ---
def get_user_school(user):
    if user.is_superuser:
        return None
    try:
        return user.schoolmanager.school
    except SchoolManager.DoesNotExist:
        return None

# --- Custom Admin Action: الموافقة على أولياء الأمور ---
@admin.action(description='الموافقة على أولياء الأمور المحددين وتوليد الأكواد')
def approve_parents(modeladmin, request, queryset):
    # منع السوبر أدمن من تنفيذ هذا الإجراء لضمان وجود مدرسة محددة أو معالجة حالته
    school = get_user_school(request.user)
    
    if not request.user.is_superuser and not school:
        modeladmin.message_user(request, "ليس لديك مدرسة مرتبطة لإتمام العملية", messages.ERROR)
        return

    updated_count = 0
    for obj in queryset:
        if not obj.is_approved:
            obj.is_approved = True
            # توليد توكن فريد إذا كان الحقل فارغاً
            if not obj.parent_school_token:
                obj.parent_school_token = str(uuid.uuid4()).split('-')[0].upper() # كود قصير وسهل
            
            # تسجيل من وافق وتاريخ الموافقة
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
            obj.save()
            updated_count += 1
    
    modeladmin.message_user(request, f"تمت الموافقة على {updated_count} من أولياء الأمور بنجاح.", messages.SUCCESS)


# --- تسجيل الموديلات مع العزل والصلاحيات ---

class BaseSchoolAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        school = get_user_school(request.user)
        return qs.filter(school=school)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            school = get_user_school(request.user)
            if school and hasattr(obj, 'school'):
                obj.school = school
        super().save_model(request, obj, form, change)

@admin.register(ParentSchool)
class ParentSchoolAdmin(BaseSchoolAdmin):

    list_display = ('parent', 'phone','school', 'parent_school_token', 'is_approved', 'approved_by', 'approved_at',)
    list_filter = ('is_approved', 'school')
    actions = [approve_parents] # إضافة الأكشن هنا
    readonly_fields = ('parent_school_token', 'approved_by', 'approved_at')

@admin.register(SchoolClass)
class SchoolClassAdmin(BaseSchoolAdmin):
    list_display = ('name', 'number', 'school', 'is_active')



@admin.register(Student)
class StudentAdmin(BaseSchoolAdmin):
    list_display = ('full_name', 'student_code', 'school_class', 'status')
    search_fields = ('full_name', 'student_code')

@admin.register(Teacher)
class TeacherAdmin(BaseSchoolAdmin):
    list_display = ('user', 'school', 'school_class')

@admin.register(SmartScreen)
class SmartScreenAdmin(BaseSchoolAdmin):
    list_display = ('screen_name', 'school_class', 'screen_token')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'role', 'is_active')
    list_filter = ('role',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        school = get_user_school(request.user)
        # المدير يرى المعلمين التابعين لمدرسته فقط
        return qs.filter(teacher__school=school)

# تسجيل الموديلات الأساسية
admin.site.register(School)
admin.site.register(SchoolManager)
admin.site.register(Parent)
admin.site.register(StudentParent)
admin.site.register(PickupRequest)