import uuid
from django.contrib import admin, messages
from django.utils import timezone
from django.db import models

from .models import (
    User, School, SchoolManager, SchoolClass, Teacher,
    Parent, ParentSchool, Student, StudentParent,
    PickupRequest, SmartScreen
)

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


class SchoolManagerInline(admin.StackedInline):
    model = SchoolManager
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    inlines = [SchoolManagerInline]

    list_display = ('full_name', 'phone', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('phone', 'full_name')
    ordering = ('phone',)

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'full_name', 'role', 'password1', 'password2'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        # مدير مدرسة يرى فقط مستخدمي مدرسته
        try:
            school = request.user.schoolmanager.school
        except Exception:
            return qs.none()

        return qs.filter(
            models.Q(teacher__school=school) |
            models.Q(parent__parentschool__school=school)
        ).distinct()
    
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False
    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return request.user.role == 'MANAGER'
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.role == 'MANAGER'




# =====================================================
# helpers
# =====================================================

def get_user_school(user):
    if user.is_superuser:
        return None
    return getattr(getattr(user, 'schoolmanager', None), 'school', None)


# =====================================================
# Base Admin (School Scoped)
# =====================================================

class SchoolScopedAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        school = get_user_school(request.user)
        if not school:
            return qs.none()

        if hasattr(self.model, 'school'):
            return qs.filter(school=school)

        if self.model.__name__ == 'Student':
            return qs.filter(school_class__school=school)

        if self.model.__name__ == 'PickupRequest':
            return qs.filter(student__school_class__school=school)

        if self.model.__name__ == 'StudentParent':
            return qs.filter(student__school_class__school=school)

        return qs.none()


    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(obj, 'school'):
            obj.school = get_user_school(request.user)
        super().save_model(request, obj, form, change)

     # ===== السماح بالرؤية =====
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.role == 'MANAGER'

    # ===== السماح بالإضافة =====
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return request.user.role == 'MANAGER'

    # ===== السماح بالتعديل =====
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.role == 'MANAGER'

    # ===== منع الحذف (اختياري) =====
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False
    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return request.user.role == 'MANAGER'


# =====================================================
# Actions
# =====================================================

@admin.action(description='الموافقة على أولياء الأمور المختارين')
def approve_parents(modeladmin, request, queryset):
    school = get_user_school(request.user)

    if not request.user.is_superuser and not school:
        modeladmin.message_user(
            request, "لا تملك مدرسة مرتبطة", messages.ERROR
        )
        return

    count = 0
    for rel in queryset:
        if not rel.is_approved:
            rel.is_approved = True
            rel.parent_school_token = rel.parent_school_token or f"ps_{uuid.uuid4().hex[:8]}"
            rel.approved_by = request.user
            rel.approved_at = timezone.now()
            rel.save()
            count += 1

    modeladmin.message_user(
        request, f"تمت الموافقة على {count} ولي أمر", messages.SUCCESS
    )


# =====================================================
# Admins
# =====================================================

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_method', 'is_active')

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser



@admin.register(SchoolManager)
class SchoolManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'is_active')


@admin.register(SchoolClass)
class SchoolClassAdmin(SchoolScopedAdmin):
    list_display = ('name', 'number', 'school', 'is_active')
    search_fields = ('name', 'number')


@admin.register(Student)
class StudentAdmin(SchoolScopedAdmin):
    list_display = ('full_name', 'student_code', 'school_class', 'status')
    search_fields = ('full_name', 'student_code')
    list_filter = ('school_class', 'status')


@admin.register(Teacher)
class TeacherAdmin(SchoolScopedAdmin):
    list_display = ('user', 'school', 'school_class')
    search_fields = ('user__full_name',)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active')
    search_fields = ('user__full_name', 'user__phone')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        school = get_user_school(request.user)
        return qs.filter(
            parentschool__school=school
        ).distinct()


@admin.register(ParentSchool)
class ParentSchoolAdmin(SchoolScopedAdmin):
    list_display = (
        'parent_name', 'parent_phone', 'school',
        'parent_school_token', 'is_approved'
    )
    search_fields = (
        'parent__user__full_name',
        'parent__user__phone'
    )
    list_filter = ('is_approved',)
    readonly_fields = ('parent_school_token', 'approved_by', 'approved_at')
    actions = [approve_parents]

    @admin.display(description='Parent')
    def parent_name(self, obj):
        return obj.parent.user.full_name

    @admin.display(description='Phone')
    def parent_phone(self, obj):
        return obj.parent.user.phone


@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ('parent_name', 'student_name', 'student_class')
    search_fields = (
        'parent__user__full_name',
        'student__full_name'
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        school = get_user_school(request.user)
        return qs.filter(student__school=school)

    @admin.display(description='Parent')
    def parent_name(self, obj):
        return obj.parent.user.full_name

    @admin.display(description='Student')
    def student_name(self, obj):
        return obj.student.full_name

    @admin.display(description='Class')
    def student_class(self, obj):
        return obj.student.school_class.name


@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = (
        'student_name', 'student_class',
        'parent_name', 'status',
        'student_status', 'requested_at'
    )

    search_fields = (
        'student__full_name',
        'parent__user__full_name',
        'student__school_class__name',
        'student__school_class__number',
    )

    list_filter = ('status', 'student__school_class')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        school = get_user_school(request.user)
        return qs.filter(student__school=school)

    def student_name(self, obj):
        return obj.student.full_name

    def student_class(self, obj):
        return obj.student.school_class.name

    def parent_name(self, obj):
        return obj.parent.user.full_name

    def student_status(self, obj):
        return obj.student.status


@admin.register(SmartScreen)
class SmartScreenAdmin(SchoolScopedAdmin):
    list_display = (
        'screen_name', 'school_class',
        'school', 'screen_token', 'is_active'
    )
    search_fields = (
        'school_class__name',
        'school_class__number'
    )
    list_filter = ('is_active',)
