import uuid
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.db import models
from .models import (
    User, School, SchoolManager, SchoolClass, Teacher,
    Parent, ParentSchool, Student, StudentParent,
    PickupRequest, SmartScreen, StudentStatus
)

# ----------------------------------------------------------------
# 1. تخصيص واجهة الآدمين الرئيسية
# ----------------------------------------------------------------
admin.site.site_header = "نظام إدارة الانصراف الذكي"
admin.site.site_title = "لوحة التحكم"
admin.site.index_title = "إدارة العمليات المدرسية"

# ----------------------------------------------------------------
# 2. أدوات مساعدة (Mixins & Actions)
# ----------------------------------------------------------------
@admin.action(description='تفعيل العناصر المختارة')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description='تعطيل العناصر المختارة')
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

# ----------------------------------------------------------------
# 3. إدارة المستخدمين (User)
# ----------------------------------------------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'colored_role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'created_at')
    search_fields = ('full_name', 'phone')
    ordering = ('-created_at',)
    actions = [make_active, make_inactive]

    @admin.display(description='الدور')
    def colored_role(self, obj):
        colors = {
            'SUPER_ADMIN': 'red',
            'MANAGER': 'blue',
            'TEACHER': 'green',
            'PARENT': 'orange',
        }
        # ✅ تصحيح: تمرير القيم كـ Arguments
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.role, 'black'),
            obj.get_role_display()
        )

# ----------------------------------------------------------------
# 4. إدارة المدارس والفصول (Structure)
# ----------------------------------------------------------------
class SchoolClassInline(admin.TabularInline):
    model = SchoolClass
    extra = 1

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'public_code', 'location_method', 'is_active')
    search_fields = ('name', 'public_code')
    list_filter = ('location_method', 'is_active')
    inlines = [SchoolClassInline]

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'school', 'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('name', 'number', 'school__name')

# ----------------------------------------------------------------
# 5. المعلمون وأولياء الأمور (Profiles)
# ----------------------------------------------------------------
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'school', 'school_class', 'get_phone', 'is_active')
    list_filter = ('school', 'school_class', 'is_active')
    search_fields = ('user__full_name', 'user__phone')
    raw_id_fields = ('user',)

    @admin.display(description='اسم المعلم')
    def get_name(self, obj): return obj.user.full_name

    @admin.display(description='الهاتف')
    def get_phone(self, obj): return obj.user.phone

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_phone', 'is_active')
    search_fields = ('user__full_name', 'user__phone')
    raw_id_fields = ('user',)

    @admin.display(description='اسم ولي الأمر')
    def get_name(self, obj): return obj.user.full_name

    @admin.display(description='الهاتف')
    def get_phone(self, obj): return obj.user.phone

# ----------------------------------------------------------------
# 6. الطلاب (Students) - الجزء الأكثر تفصيلاً
# ----------------------------------------------------------------
class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 1
    raw_id_fields = ('parent',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'student_code', 'school_class', 'colored_status', 'is_active')
    list_filter = ('school', 'school_class', 'status', 'is_active')
    search_fields = ('full_name', 'student_code')
    readonly_fields = ('student_code',)
    inlines = [StudentParentInline]
    ordering = ('school_class', 'full_name')

    @admin.display(description='الحالة الحالية')
    def colored_status(self, obj):
        color_map = {
            StudentStatus.PRESENT: 'gray',
            StudentStatus.REQUESTED: 'orange',
            StudentStatus.AT_GATE: 'blue',
            StudentStatus.DELIVERED: 'green',
        }
        # ✅ تصحيح: تمرير القيم كـ Arguments
        return format_html(
            '<b style="color: {};">{}</b>',
            color_map.get(obj.status, 'black'),
            obj.get_status_display()
        )

# ----------------------------------------------------------------
# 7. طلبات الاستلام (Pickup Requests)
# ----------------------------------------------------------------
@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'parent', 'status', 'requested_at', 'duration')
    list_filter = ('status', 'school', 'requested_at')
    search_fields = ('student__full_name', 'parent__user__full_name')
    readonly_fields = ('requested_at', 'accepted_at', 'completed_at')
    ordering = ('-requested_at',)

    @admin.display(description='مدة الانتظار')
    def duration(self, obj):
        if obj.completed_at:
            diff = obj.completed_at - obj.requested_at
            return f"{int(diff.total_seconds() / 60)} دقيقة"
        return "قيد الانتظار"

# ----------------------------------------------------------------
# 8. الشاشات الذكية (Smart Screens)
# ----------------------------------------------------------------
@admin.register(SmartScreen)
class SmartScreenAdmin(admin.ModelAdmin):
    list_display = ('screen_name', 'school', 'school_class', 'is_active', 'display_token')
    readonly_fields = ('screen_token',)
    list_filter = ('school', 'is_active')
    search_fields = ('screen_name',)

    @admin.display(description="رمز التوكن")
    def display_token(self, obj):
        # ✅ تصحيح: تمرير القيم كـ Arguments
        return format_html('<code>{}</code>', obj.screen_token)
# ----------------------------------------------------------------
# تسجيل بقية الموديلات التكميلية
# ----------------------------------------------------------------

@admin.register(SchoolManager)
class SchoolManagerAdmin(admin.ModelAdmin):
    # عرض البيانات الهامة في الجدول
    list_display = ('get_manager_name', 'get_manager_phone', 'school_info', 'status_badge')
    list_filter = ('school', 'is_active')
    search_fields = ('user__full_name', 'user__phone', 'school__name')
    raw_id_fields = ('user', 'school') # لتسريع البحث إذا كثرت المدارس
    
    @admin.display(description='المدير')
    def get_manager_name(self, obj):
        return obj.user.full_name

    @admin.display(description='رقم الهاتف')
    def get_manager_phone(self, obj):
        return obj.user.phone

    @admin.display(description='المدرسة المرتبطة')
    def school_info(self, obj):
        # ✅ الطريقة الصحيحة: نضع {} كـ placeholder ونمرر القيم بعدها
        return format_html(
            '<strong style="color: #2c3e50;">{}</strong><br>'
            '<small style="color: #7f8c8d;">كود: {}</small>',
            obj.school.name,          # القيمة الأولى
            obj.school.public_code    # القيمة الثانية
        )
   
    @admin.display(description='حالة الحساب')
    def status_badge(self, obj):
        status_text = "نشط" if obj.is_active else "معطل"
        color = "#27ae60" if obj.is_active else "#e74c3c"
        bg = "#eafaf1" if obj.is_active else "#fdedec"
        return format_html(
            '<span style="color: {}; background: {}; padding: 4px 12px; border-radius: 10px; font-weight: bold;">{}</span>',
            color, bg, status_text
        )
    
    actions = ['activate_managers', 'deactivate_managers']

    @admin.action(description="تنشيط حسابات المدراء")
    def activate_managers(self, request, queryset):
        queryset.update(is_active=True)
    
    @admin.action(description="تعطيل حسابات المدراء")
    def deactivate_managers(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(ParentSchool)
class ParentSchoolAdmin(admin.ModelAdmin):
    list_display = (
        'get_parent_name', 
        'get_parent_phone', 
        'school', 
        'status_tag', 
        'parent_school_token_styled', 
        'approved_by_info',
    )
    list_filter = ('is_approved', 'school', 'approved_at')
    search_fields = ('parent__user__full_name', 'parent__user__phone', 'parent_school_token')
    readonly_fields = ('parent_school_token', 'approved_by', 'approved_at')

    # --- تصحيح الدوال التي تسببت في الخطأ ---

    @admin.display(description='الحالة')
    def status_tag(self, obj):
        status_text = "✅ معتمد" if obj.is_approved else "⏳ معلق"
        bg = "#d4edda" if obj.is_approved else "#fff3cd"
        color = "#155724" if obj.is_approved else "#856404"
        return format_html(
            '<span style="background: {}; color: {}; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px;">{}</span>',
            bg, color, status_text
        )
    

    @admin.display(description='التوكن الأمني')
    def parent_school_token_styled(self, obj):
        return format_html(
            '<code style="color: #e83e8c; background: #f8f9fa; padding: 2px 5px; border-radius: 4px;">{}</code>',
            obj.parent_school_token
        )

    @admin.display(description='معلومات الاعتماد')
    def approved_by_info(self, obj):
        if obj.is_approved and obj.approved_by:
            return format_html(
                '<div style="font-size: 11px; color: #666;">بواسطة: <b>{}</b><br>في: {}</div>',
                obj.approved_by.full_name,
                obj.approved_at.strftime('%Y-%m-%d %H:%M')
            )
        return "-"

    # الميثودات المساعدة الأخرى
    @admin.display(description='ولي الأمر')
    def get_parent_name(self, obj):
        return obj.parent.user.full_name

    @admin.display(description='الهاتف')
    def get_parent_phone(self, obj):
        return obj.parent.user.phone

    # --- الأفعال (Actions) ---

    @admin.action(description='✅ الموافقة على الطلبات المختارة')
    def bulk_approve(self, request, queryset):
        updated = queryset.update(
            is_approved=True,
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f"تم اعتماد {updated} ولي أمر بنجاح.", messages.SUCCESS)

    @admin.action(description='❌ إلغاء اعتماد الطلبات المختارة')
    def bulk_disapprove(self, request, queryset):
        queryset.update(is_approved=False, approved_by=None, approved_at=None)
        self.message_user(request, "تم إلغاء اعتماد الطلبات.", messages.WARNING)


@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    # عرض معلومات الطالب وولي الأمر جنباً إلى جنب
    list_display = ('student_card', 'parent_card', 'class_info', 'action_links')
    list_filter = ('student__school', 'student__school_class')
    search_fields = (
        'student__full_name', 
        'student__student_code', 
        'parent__user__full_name', 
        'parent__user__phone'
    )
    raw_id_fields = ('student', 'parent')

    @admin.display(description='بيانات الطالب')
    def student_card(self, obj):
        return format_html(
            '<div style="border-left: 4px solid #3498db; padding-left: 10px;"><b>{}</b><br><small style="color: #666;">كود: {}</small></div>',
            obj.student.full_name, obj.student.student_code
        )


    @admin.display(description='ولي الأمر المرتبط')
    def parent_card(self, obj):
        return format_html(
            '<div style="border-left: 4px solid #f1c40f; padding-left: 10px;"><b>{}</b><br><small style="color: #666;">هاتف: {}</small></div>',
            obj.parent.user.full_name, obj.parent.user.phone
        )

    @admin.display(description='الفصل الدراسي')
    def class_info(self, obj):
        return format_html(
            '<span style="background: #f8f9fa; border: 1px solid #ddd; padding: 3px 8px; border-radius: 5px;">'
            '{}</span>',
            obj.student.school_class.name
        )
    
    @admin.display(description='روابط سريعة')
    def action_links(self, obj):
        # ملاحظة: تأكد أن اسم الـ app هو 'attendance' في الروابط أدناه
        student_url = f"/admin/attendance/student/{obj.student.id}/change/"
        parent_url = f"/admin/attendance/parent/{obj.parent.id}/change/"
        return format_html(
            '<a href="{}" style="color: #3498db;">👤 الطالب</a> | <a href="{}" style="color: #f39c12;">👨‍👩‍👧 ولي الأمر</a>',
            student_url, parent_url
        )