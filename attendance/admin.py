import uuid
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.db import models
from django.db.models import Q
from .models import (
    User, School, SchoolManager, SchoolClass, Teacher,
    Parent, ParentSchool, Student, StudentParent,
    PickupRequest, SmartScreen, StudentStatus
)



class SchoolIsolatedAdmin(admin.ModelAdmin):
    """كلاس أساسي لعزل البيانات بناءً على مدرسة المدير"""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # 1. السوبر آدمين يرى كل شيء
        if request.user.is_superuser:
            return qs
        
        # 2. التحقق من وجود حساب مدير مدرسة
        manager = getattr(request.user, 'schoolmanager', None)
        if manager:
            # --- حالة موديل المستخدم User ---
            # if self.model == User:
            #     # المعلمون التابعون للمدير في مدرسته
            #     teacher_user_ids = Teacher.objects.filter(school=manager.school).values_list('user_id', flat=True)
            #     # يرى نفسه + معلميه + أي مستخدم دوره أب
            #     return qs.filter(
            #         Q(id=request.user.id) | 
            #         Q(id__in=teacher_user_ids) | 
            #         Q(role='PARENT')
            #     )

            # # --- حالة موديل الأب Parent ---
            # if self.model == Parent:
            #     # نرجع الكل ليتمكن من البحث عن الأب وربطه بالطالب
            #     return qs

            # --- الموديلات التي تحتوي حقل مدرسة مباشر ---
            if hasattr(self.model, 'school'):
                return qs.filter(school=manager.school)
            
            # --- الموديلات المرتبطة بطالب (مثل StudentParent) ---
            elif hasattr(self.model, 'student'):
                return qs.filter(student__school=manager.school)

            return qs
            
        # إذا لم يكن مديراً ولا سوبر آدمين (مثل المعلم)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        # ربط العنصر بمدرسة المدير تلقائياً عند الإنشاء
        if not request.user.is_superuser:
            manager = getattr(request.user, 'schoolmanager', None)
            if manager and hasattr(obj, 'school'):
                obj.school = manager.school
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """تقييد القوائم المنسدلة ليرى المدير فقط بيانات مدرسته"""
        if not request.user.is_superuser:
            manager = getattr(request.user, 'schoolmanager', None)
            if manager:
                # 1. إذا كان الحقل يشير للمدرسة
                if db_field.name == "school":
                    kwargs["queryset"] = School.objects.filter(id=manager.school.id)
                
                # 2. إذا كان الحقل يشير للفصل (موجود في Teacher, Student, SmartScreen)
                if db_field.name == "school_class":
                    kwargs["queryset"] = SchoolClass.objects.filter(school=manager.school)
                
                # 3. إذا كان الحقل يشير للطالب (موجود في PickupRequest, StudentParent)
                if db_field.name == "student":
                    kwargs["queryset"] = Student.objects.filter(school=manager.school)
                
                # 4. إذا كان الحقل يشير لولي الأمر (موجود في PickupRequest, StudentParent)
                # ملاحظة: أولياء الأمور ليس لديهم حقل مدرسة مباشر، لذا نظهرهم جميعاً 
                # أو نفلتر المرتبطين بالمدرسة عبر ParentSchool
                if db_field.name == "parent":
                    parent_ids = ParentSchool.objects.filter(school=manager.school).values_list('parent_id', flat=True)
                    kwargs["queryset"] = Parent.objects.filter(id__in=parent_ids)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
# ----------------------------------------------------------------
# 3. إدارة المستخدمين (User)
# ----------------------------------------------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'colored_role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'created_at')
    search_fields = ('full_name', 'phone')
    ordering = ('-created_at',)
    
    # تعريف واحد شامل لجميع الـ Actions
    actions = ['make_active_users', 'make_inactive_users', 'setup_manager_group']

    @admin.display(description='الدور')
    def colored_role(self, obj):
        colors = {
            'SUPER_ADMIN': 'red',
            'MANAGER': 'blue',
            'TEACHER': 'green',
            'PARENT': 'orange',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.role, 'black'),
            obj.get_role_display()
        )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        manager = getattr(request.user, 'schoolmanager', None)
        if manager:
            # جلب المعلمين التابعين لمدرسته
            teacher_ids = Teacher.objects.filter(school=manager.school).values_list('user_id', flat=True)
            # الفلترة: نفسه + معلميه + كل من هو ولي أمر
            return qs.filter(Q(id=request.user.id) | Q(id__in=teacher_ids) | Q(role='PARENT'))
        return qs.none()
    
    def get_readonly_fields(self, request, obj=None):
        # إذا كان سوبر أدمن
        if request.user.is_superuser:
            return ['created_at', 'last_login']
            
        # إذا كان مديراً
        if obj: # عند التعديل
            return ['phone', 'role', 'national_id', 'created_at']
        return ['created_at']
    
    def get_fieldsets(self, request, obj=None):
        """تخصيص الحقول التي تظهر بناءً على نوع المستخدم"""
        # إذا كان سوبر أدمن، تظهر كل الحقول (الوضع الافتراضي)
        if request.user.is_superuser:
            return [
                (None, {'fields': ('phone', 'password')}),
                ('معلومات الشخصية', {'fields': ('full_name', 'national_id', 'role')}),
                ('الصلاحيات', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
                ('التواريخ', {'fields': ('last_login', 'created_at')}),
            ]
        
        # إذا كان مديراً، تظهر المعلومات الأساسية فقط ويختفي صندوق الصلاحيات والتواريخ
        return [
            (None, {'fields': ('phone',)}),
            ('معلومات الشخصية', {'fields': ('full_name', 'national_id', 'role', 'is_active')}),
        ]

    def has_view_permission(self, request, obj=None):
    # السماح للمدير بالعرض دائماً إذا كانstaff
    if request.user.role == 'MANAGER': return True
    return super().has_view_permission(request, obj)
    
    
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if request.user.role == 'MANAGER': return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if request.user.role == 'MANAGER': return False
        return super().has_delete_permission(request, obj)

    # أكشن لتفعيل المستخدمين
    @admin.action(description='✅ تفعيل المستخدمين المختارة')
    def make_active_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "تم تفعيل المستخدمين بنجاح.")

    # أكشن لتعطيل المستخدمين
    @admin.action(description='❌ تعطيل المستخدمين المختارة')
    def make_inactive_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "تم تعطيل المستخدمين بنجاح.")

    # الأكشن الأهم الخاص بالصلاحيات
    @admin.action(description='🛠️ إنشاء/تحديث صلاحيات مجموعة مدراء المدارس')
    def setup_manager_group(self, request, queryset):
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType
        
        group, created = Group.objects.get_or_create(name='School Managers')
        
        # الموديلات التي يحكمها المدير
        all_models = [Student, Teacher, SchoolClass, SmartScreen, PickupRequest, ParentSchool, StudentParent, User, Parent]
        
        for model in all_models:
            content_type = ContentType.objects.get_for_model(model)
            
            # حالة خاصة: المستخدمين والآباء (رؤية وإضافة فقط)
            if model in [User, Parent]:
                perms = Permission.objects.filter(
                    content_type=content_type, 
                    codename__in=[f'view_{model._meta.model_name}', f'add_{model._meta.model_name}']
                )
            else:
                # بقية الموديلات: صلاحيات كاملة
                perms = Permission.objects.filter(content_type=content_type)
            
            for perm in perms:
                group.permissions.add(perm)
        
        self.message_user(request, "تم تحديث الصلاحيات: (User/Parent) رؤية وإضافة فقط، البقية كاملة.", messages.SUCCESS)

# ----------------------------------------------------------------
# 4. إدارة المدارس والفصول (Structure)
# ----------------------------------------------------------------
class SchoolClassInline(admin.TabularInline):
    model = SchoolClass
    extra = 1

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'public_code', 'location_method','id', 'is_active')
    search_fields = ('name', 'public_code')
    list_filter = ('location_method', 'is_active')
    inlines = [SchoolClassInline]

@admin.register(SchoolClass)
class SchoolClassAdmin(SchoolIsolatedAdmin):
    list_display = ('name', 'number', 'school','id' ,'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('name', 'number', 'school__name')

# ----------------------------------------------------------------
# 5. المعلمون وأولياء الأمور (Profiles)
# ----------------------------------------------------------------
@admin.register(Teacher)
class TeacherAdmin(SchoolIsolatedAdmin):
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # المدير يرى جميع أولياء الأمور ليتمكن من ربطهم بالطلاب
        if hasattr(request.user, 'schoolmanager'):
            return qs
        return qs.none()

    @admin.display(description='اسم ولي الأمر')
    def get_name(self, obj): return obj.user.full_name

    @admin.display(description='الهاتف')
    def get_phone(self, obj): return obj.user.phone

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if request.user.role == 'MANAGER': return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if request.user.role == 'MANAGER': return False
        return super().has_delete_permission(request, obj)

# ----------------------------------------------------------------
# 6. الطلاب (Students) - الجزء الأكثر تفصيلاً
# ----------------------------------------------------------------
class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 1
    raw_id_fields = ('parent',)

@admin.register(Student)
class StudentAdmin(SchoolIsolatedAdmin):
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
class PickupRequestAdmin(SchoolIsolatedAdmin):
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
class SmartScreenAdmin(SchoolIsolatedAdmin):
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
class ParentSchoolAdmin(SchoolIsolatedAdmin):
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
class StudentParentAdmin(SchoolIsolatedAdmin):
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
