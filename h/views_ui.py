from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.exceptions import ValidationError, PermissionDenied

from .utils.decorators import manager_required

# استيراد الخدمات التي أرسلتها سابقاً
from .services.student_services import StudentManagementService
from .services.classmanagementservice import ClassManagementService
from .services.parent_services import ParentManagementService
from .services.teacher_services import TeacherManagementService
from .services.screen_services import SmartScreenService
from .services.school_settings_service import SchoolSettingsService
from .models import SchoolClass, Student, Teacher, SmartScreen, ParentSchool
from .services.identity_services import AuthService
from django.contrib.auth import login as django_login, logout as django_logout


# -------- Login / Logout (session-based) --------
@require_http_methods(["GET", "POST"])
def ui_login(request):
    if request.method == "GET":
        # إذا كان المستخدم مسجل دخوله بالفعل كمدير، وجهه للوحة التحكم
        if request.user.is_authenticated and getattr(request.user, 'role', None) == 'MANAGER':
            return redirect('ui_dashboard')
        return render(request, "login.html")

    phone = request.POST.get('phone')
    password = request.POST.get('password')

    try:
        # 1. استخدام AuthService لتنفيذ عملية التحقق وتوليد التوكنات
        auth_data = AuthService.login_user(phone, password)
        
        # 2. الحصول على كائن المستخدم الفعلي للقيام بـ session login
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(phone=phone)

        # 3. التحقق من الصلاحية للمدير فقط في هذه الواجهة
        if user.role != 'MANAGER':
            return render(request, "login.html", {
                "error": "هذه الواجهة مخصصة لمدير المدرسة فقط.", 
                "phone": phone
            })

        # 4. تسجيل الدخول في الجلسة (Session) لتعمل الـ Decorators مثل @manager_required
        django_login(request, user)

        # 5. اختيارياً: تخزين التوكن في الـ Cookies إذا كنت ستحتاجه في JavaScript لاحقاً
        response = redirect('ui_dashboard')
        response.set_cookie('access_token', auth_data['access'], httponly=True)
        response.set_cookie('refresh_token', auth_data['refresh'], httponly=True)
        
        return response

    except Exception as e:
        # استخراج رسالة الخطأ من الـ Exception (مثل AuthenticationFailed)
        error_msg = str(e.detail) if hasattr(e, 'detail') else "بيانات الدخول غير صحيحة"
        return render(request, "login.html", {"error": error_msg, "phone": phone})

@require_http_methods(["POST", "GET"]) # أضفنا GET ليسهل تسجيل الخروج من رابط سريع إذا أردت
def ui_logout(request):
    # 1. إبطال التوكن إذا كان مخزناً في الكوكي (باستخدام AuthService)
    refresh_token = request.COOKIES.get('refresh_token')
    if refresh_token:
        try:
            AuthService.logout_user(refresh_token)
        except:
            pass # نتجاهل الخطأ في تسجيل الخروج لضمان مسح الجلسة المحلية

    # 2. تسجيل الخروج من Django Session
    django_logout(request)
    
    response = redirect('ui_login')
    # 3. مسح الكوكيز
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response

# -------- Dashboard --------
@manager_required
def ui_dashboard(request):
    # إحصاءات مبسطة: العدادات تستخرج عبر Services أو Queries سريعة
    manager_school = request.user.schoolmanager.school
    present_count = Student.objects.filter(school=manager_school, status='PRESENT', is_active=True).count()
    requested_count = Student.objects.filter(school=manager_school, status='REQUESTED').count()
    at_gate_count = Student.objects.filter(school=manager_school, status='AT_GATE').count()
    delivered_count = Student.objects.filter(school=manager_school, status='DELIVERED').count()

    stats = {
        "present_count": present_count,
        "requested_count": requested_count,
        "at_gate_count": at_gate_count,
        "delivered_count": delivered_count,
    }
    return render(request, "dashboard.html", {"stats": stats})


# -------- Students Views --------
@manager_required
def ui_students(request):
    manager_school = request.user.schoolmanager.school
    students = Student.objects.filter(school=manager_school).select_related('school_class')
    classes = SchoolClass.objects.filter(school=manager_school, is_active=True)
    return render(request, "students.html", {"students": students, "classes": classes})


@manager_required
@require_http_methods(["POST"])
def ui_students_create(request):
    try:
        StudentManagementService.create_student(
            manager_user=request.user,
            full_name=request.POST.get('full_name'),
            class_id=request.POST.get('class_id')
        )
        messages.success(request, "تم إنشاء الطالب بنجاح.")
    except (ValidationError, PermissionDenied) as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, "حدث خطأ أثناء إنشاء الطالب.")
    return redirect('ui_students')


@manager_required
@require_http_methods(["POST"])
def ui_students_transfer(request):
    try:
        StudentManagementService.transfer_student(
            manager_user=request.user,
            student_id=request.POST.get('student_id'),
            new_class_id=request.POST.get('new_class_id')
        )
        messages.success(request, "تم ن��ل الطالب بنجاح.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_students')


@manager_required
@require_http_methods(["POST"])
def ui_students_assign_parent(request):
    try:
        StudentManagementService.assign_parent_to_student(
            manager_user=request.user,
            student_id=request.POST.get('student_id'),
            parent_phone=request.POST.get('parent_phone'),
            parent_name=request.POST.get('parent_name')
        )
        messages.success(request, "تم ربط ولي الأمر بالطالب.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_students')


# -------- Classes Views --------
@manager_required
def ui_classes(request):
    manager_school = request.user.schoolmanager.school
    classes = SchoolClass.objects.filter(school=manager_school, is_active=True)
    return render(request, "classes.html", {"classes": classes})


@manager_required
@require_http_methods(["POST"])
def ui_classes_create(request):
    try:
        ClassManagementService.create_class(
            manager_user=request.user,
            name=request.POST.get('name'),
            number=request.POST.get('number')
        )
        messages.success(request, "تم إنشاء الفصل.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_classes')


@manager_required
@require_http_methods(["POST"])
def ui_classes_update(request):
    try:
        ClassManagementService.update_class(
            manager_user=request.user,
            class_id=request.POST.get('class_id'),
            data={'name': request.POST.get('name'), 'number': request.POST.get('number')}
        )
        messages.success(request, "تم تحديث بيانات الفصل.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_classes')


@manager_required
@require_http_methods(["POST"])
def ui_classes_deactivate(request):
    try:
        ClassManagementService.deactivate_class(
            manager_user=request.user,
            class_id=request.POST.get('class_id')
        )
        messages.success(request, "تم تعطيل الفصل.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_classes')


# -------- Parents Views --------
@manager_required
def ui_parents(request):
    parent_schools = ParentManagementService.get_parents_for_school(request.user)
    return render(request, "parents.html", {"parent_schools": parent_schools})


@manager_required
@require_http_methods(["POST"])
def ui_parents_approve(request):
    try:
        ParentManagementService.approve_parent_school(
            manager_user=request.user,
            parent_school_id=request.POST.get('parent_school_id')
        )
        messages.success(request, "تم اعتماد ولي الأمر.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_parents')


# -------- Screens Views --------
@manager_required
def ui_screens(request):
    manager_school = request.user.schoolmanager.school
    screens = SmartScreen.objects.filter(school=manager_school, is_active=True).select_related('school_class')
    classes = SchoolClass.objects.filter(school=manager_school, is_active=True)
    return render(request, "screens.html", {"screens": screens, "classes": classes})


@manager_required
@require_http_methods(["POST"])
def ui_screens_create(request):
    try:
        SmartScreenService.create_screen(
            manager_user=request.user,
            class_id=request.POST.get('class_id'),
            screen_name=request.POST.get('screen_name')
        )
        messages.success(request, "تم إنشاء الشاشة.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_screens')


# -------- Settings Views --------
@manager_required
def ui_settings(request):
    school = request.user.schoolmanager.school
    return render(request, "settings.html", {"school": school})


@manager_required
@require_http_methods(["POST"])
def ui_settings_update(request):
    try:
        SchoolSettingsService.update_location_settings(
            manager_user=request.user,
            data={
                "location_method": request.POST.get('location_method'),
                "location_lat": request.POST.get('location_lat'),
                "location_lng": request.POST.get('location_lng'),
                "location_radius": int(request.POST.get('location_radius') or 100)
            }
        )
        messages.success(request, "تم تحديث إعدادات المدرسة.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('ui_settings')