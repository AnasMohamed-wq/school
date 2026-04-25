
from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Student, SchoolClass, Parent, ParentSchool , StudentParent , Teacher ,SmartScreen, SchoolManager
from django.core.paginator import Paginator
from django.db.models import Q


from .services.identity_services import AuthService # استدعاء خدمتك الحالية
from .services.student_services import StudentManagementService
from .services.parent_services import ParentManagementService
from .services.usermanagementservice import UserManagementService # الخدمة المركزية للمستخدمين
from .services.teacher_services import TeacherManagementService
from .services.classmanagementservice import ClassManagementService
from .services.screen_services  import SmartScreenService


def web_login_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        print(f"DEBUG: Attempting login for phone: {phone}")

        try:
            # 1. نستخدم منطق التوثيق الموجود فعلياً في خدمتك
            # ملاحظة: authenticate() داخل الخدمة ترجع كائن الـ User
            from django.contrib.auth import authenticate
            user = authenticate(username=phone, password=password)

            if user is not None:
                # 2. القيد المطلوب: السماح فقط لمدير المدرسة (MANAGER)
                if user.role == 'MANAGER' and user.is_active:
                    login(request, user)
                    messages.success(request, f"مرحباً بك   {user.full_name}")
                    return redirect('web_students') # وجهه للوحة التحكم
                else:
                    messages.error(request, "عذراً، هذا الدخول مخصص لمديري المدارس فقط.")
            else:
                print("DEBUG: Authenticate returned None. Check password or phone number.")
                messages.error(request, "بيانات الدخول غير صحيحة.")
                
        except Exception as e:
            messages.error(request, f"حدث خطأ: {str(e)}")

    return render(request, 'login.html')

def web_logout_view(request):
    logout(request)
    return redirect('web_login')


#========================================================================

# دالة مساعدة للتأكد أن المستخدم مدير مدرسة (تُستخدم داخل الدوال)
def get_manager_school_or_none(user):
    if hasattr(user, 'schoolmanager'):
        return user.schoolmanager.school
    return None

@login_required
def student_management_main_view(request):
    school = get_manager_school_or_none(request.user)
    if not school:
        messages.error(request, "ليس لديك صلاحية الوصول.")
        return redirect('web_login')

    # --- 1. معالجة العمليات (POST) ---
    if request.method == 'POST':
        action = request.POST.get('action')
        student_id = request.POST.get('student_id')
        try:
            if action == 'create':
                StudentManagementService.create_student(
                    manager_user=request.user,
                    full_name=request.POST.get('full_name'),
                    class_id=request.POST.get('class_id')
                )
                messages.success(request, "تم إضافة الطالب بنجاح.")

            elif action == 'transfer' and student_id:
                StudentManagementService.transfer_student(
                    manager_user=request.user,
                    student_id=student_id,
                    new_class_id=request.POST.get('new_class_id')
                )
                messages.success(request, "تم نقل الطالب بنجاح.")

            elif action == 'assign_parent' and student_id:
                # تعديل: هنا نستخدم ولي الأمر المختار من القائمة المنسدلة (المسجلين مسبقاً)
                selected_parent_id = request.POST.get('parent_id')
                if selected_parent_id:
                    parent = Parent.objects.get(id=selected_parent_id)
                    StudentManagementService.assign_parent_to_student(
                        manager_user=request.user,
                        student_id=student_id,
                        parent_phone=parent.user.phone, # نمرر البيانات للخدمة الحالية
                        parent_name=parent.user.full_name
                    )
                    messages.success(request, "تم ربط ولي الأمر المختار بنجاح.")

            
            # 1. تحديث بيانات الطالب
            elif action == 'update' and student_id:
                data = {
                    'full_name': request.POST.get('full_name'),
                    'is_active': request.POST.get('is_active') == 'on'  #Checkbox المنطق الخاص بالـ 
                }
                StudentManagementService.update_student(
                    manager_user=request.user,
                    student_id=student_id,
                    data=data
                )
                messages.success(request, "تم تحديث بيانات الطالب بنجاح.")

            # 2. حذف الطالب (يجب إضافة خدمة الحذف أو استخدام المنطق المباشر)
            elif action == 'delete' and student_id:
                # تأكد من جلب الطالب بشرط المدرسة لضمان الأمان قبل الحذف
                student = get_object_or_404(Student, id=student_id, school=school)
                student.delete()
                messages.success(request, "تم حذف الطالب نهائياً من النظام.")

        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
        return redirect('web_students')

    # --- 2. معالجة البحث والفلترة (GET) ---
    search_query = request.GET.get('search', '')
    class_filter = request.GET.get('class_id', '')

    student_list = Student.objects.filter(school=school).select_related('school_class').order_by('-id')

    if search_query:
        student_list = student_list.filter(full_name__icontains=search_query)
    
    if class_filter:
        student_list = student_list.filter(school_class_id=class_filter)

    # --- 3. نظام التقسيم (Pagination) ---
    paginator = Paginator(student_list, 20) # 20 طالب في الصفحة
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)

    # --- 4. جلب بيانات المودالز ---
    classes = SchoolClass.objects.filter(school=school)
    
    # جلب أولياء الأمور المسجلين والمعتمدين في المدرسة فقط
    approved_parents = ParentManagementService.get_parents_for_school(request.user).filter(is_approved=True)

    return render(request, 'students.html', {
        'students': students,
        'classes': classes,
        'approved_parents': approved_parents,
        'search_query': search_query,
        'selected_class': class_filter
    })



#=======================================================================
# ادارة أولياء الأمور 




@login_required
def parent_management_main_view(request):
    school = get_manager_school_or_none(request.user)
    if not school:
        messages.error(request, "غير مسموح لك بالوصول.")
        return redirect('web_login')

    # --- 1. معالجة العمليات (POST) ---
    if request.method == 'POST':
        action = request.POST.get('action')
        parent_id = request.POST.get('parent_id') # معرف ولي الأمر (للعمليات المباشرة)
        parent_school_id = request.POST.get('ps_id') # معرف علاقة الربط (للاعتماد)

        try:
            # أ. إضافة مستخدم جديد وربطه بالمدرسة كولي أمر
            if action == 'create_and_link':
                user = UserManagementService.create_or_link_parent(
                    manager_user=request.user,
                    full_name=request.POST.get('full_name'),
                    phone=request.POST.get('phone'),
                    national_id=request.POST.get('national_id') # الحقل الجديد
                )
                
                # ميزة إضافية: إذا تم تمرير ID طالب، نربطه به فوراً
                student_id = request.POST.get('target_student_id')
                if student_id:
                    parent = user.parent
                    StudentParent.objects.get_or_create(student_id=student_id, parent=parent)
                    messages.success(request, f"تم إنشاء ولي الأمر وربطه بالطالب بنجاح.")
                else:
                    messages.success(request, "تمت إضافة ولي الأمر لقائمة الانتظار بالمدرسة.")

            # ب. اعتماد ولي أمر (موجود في قائمة الانتظار)
            elif action == 'approve' and parent_school_id:
                ParentManagementService.approve_parent_school(request.user, parent_school_id)
                messages.success(request, "تم اعتماد ولي الأمر بنجاح.")

            # ج. تحديث بيانات ولي الأمر (الاسم فقط حسب الخدمة)
            elif action == 'update' and parent_id:
                data = {
                    'full_name': request.POST.get('full_name'),
                    'phone': request.POST.get('phone'),
                    'national_id': request.POST.get('national_id')
                }
                ParentManagementService.update_parent(request.user, parent_id, data)
                messages.success(request, "تم تحديث البيانات الشخصية بنجاح.")

            # د. فك الارتباط بالمدرسة (حذف العلاقة وليس المستخدم)
            elif action == 'unlink' and parent_school_id:
                ps_relation = get_object_or_404(ParentSchool, id=parent_school_id, school=school)
                ps_relation.delete()
                messages.success(request, "تم فك ارتباط ولي الأمر بالمدرسة بنجاح.")

        except Exception as e:
            messages.error(request, f"فشلت العملية: {str(e)}")
        
        return redirect('web_parents')

    # --- 2. معالجة البحث والفلترة (GET) ---
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '') # 'approved' or 'pending'

    # نستخدم الخدمة لجلب العلاقات
    parent_list = ParentManagementService.get_parents_for_school(request.user)

    if search_query:
        parent_list = parent_list.filter(
            Q(parent__user__full_name__icontains=search_query) |
            Q(parent__user__phone__icontains=search_query)
        )
    
    if status_filter == 'approved':
        parent_list = parent_list.filter(is_approved=True)
    elif status_filter == 'pending':
        parent_list = parent_list.filter(is_approved=False)

    # --- 3. التقسيم (Pagination) ---
    paginator = Paginator(parent_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    # بيانات للمودالات (قائمة الطلاب لربطهم عند الإضافة)
    students = Student.objects.filter(school=school).order_by('full_name')

    return render(request, 'parent.html', {
        'parents_relations': page_obj,
        'students': students,
        'search_query': search_query,
        'status_filter': status_filter
    })



#=======================================================================
# ادارة الأساتذة

@login_required
def web_teachers_management(request):
    school = get_manager_school_or_none(request.user)
    if not school:
        messages.error(request, "غير مسموح لك بالوصول.")
        return redirect('web_login')

    if request.method == 'POST':
        action = request.POST.get('action')
        teacher_id = request.POST.get('teacher_id')

        try:
            if action == 'create':
                TeacherManagementService.create_teacher(
                    manager_user=request.user,
                    full_name=request.POST.get('full_name'),
                    phone=request.POST.get('phone'),
                    national_id=request.POST.get('national_id') # الحقل الجديد
                )
                messages.success(request, "تمت إضافة المعلم وتعيين كلمة المرور بنجاح.")

            elif action == 'update' and teacher_id:
                data = {
                    'full_name': request.POST.get('full_name'),
                    'phone': request.POST.get('phone'),
                    'national_id': request.POST.get('national_id')
                }
                TeacherManagementService.update_teacher(request.user, teacher_id, data)
                messages.success(request, "تم تحديث بيانات الأستاذ بنجاح.")

            elif action == 'transfer' and teacher_id:
                new_class_id = request.POST.get('new_class_id')
                TeacherManagementService.transfer_teacher_to_class(request.user, teacher_id, new_class_id)
                messages.success(request, "تم نقل الأستاذ للفصل بنجاح.")

            elif action == 'unlink' and teacher_id:
                TeacherManagementService.unlink_teacher_from_school(request.user, teacher_id)
                messages.success(request, "تم فك ارتباط الأستاذ بالمدرسة.")

        except Exception as e:
            messages.error(request, f"فشلت العملية: {str(e)}")
        return redirect('web_teachers')

    # معالجة البحث والفلترة (GET)
    search_query = request.GET.get('search', '')
    teacher_list = Teacher.objects.filter(school=school).select_related('user', 'school_class')

    if search_query:
        teacher_list = teacher_list.filter(
            Q(user__full_name__icontains=search_query) |
            Q(user__phone__icontains=search_query)
        )

    paginator = Paginator(teacher_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    classes = SchoolClass.objects.filter(school=school, is_active=True)

    return render(request, 'teacher.html', {
        'teachers': page_obj,
        'classes': classes,
        'search_query': search_query
    })



#=======================================================================
# ادارة الفصول الدراسية والشاشات الذكية



@login_required
def class_management_view(request):
    school = get_manager_school_or_none(request.user)
    if not school:
        messages.error(request, "صلاحيات غير كافية للوصول.")
        return redirect('web_login')

    # --- 1. معالجة العمليات (POST) ---
    if request.method == 'POST':
        action = request.POST.get('action')
        class_id = request.POST.get('class_id')
        screen_id = request.POST.get('screen_id')

        try:
            # أ. إدارة الفصول (Class Actions)
            if action == 'create_class':
                ClassManagementService.create_class(
                    manager_user=request.user,
                    name=request.POST.get('name'),
                    number=request.POST.get('number')
                )
                messages.success(request, "تم إنشاء الفصل بنجاح.")

            elif action == 'update_class' and class_id:
                is_active_val = request.POST.get('is_active') == 'true'
                data = {
                    'name': request.POST.get('name'),
                    'number': request.POST.get('number'),
                    'is_active': is_active_val
                }
                ClassManagementService.update_class(request.user, class_id, data)
                messages.success(request, f"تم تحديث بيانات الفصل {'وتفعيله' if is_active_val else 'وإيقافه'}.")


            elif action == 'deactivate_class' and class_id:
                ClassManagementService.deactivate_class(request.user, class_id)
                messages.success(request, "تم إيقاف نشاط الفصل بنجاح.")

            # ب. إدارة الشاشات (Screen Actions)
            elif action == 'create_screen':
                SmartScreenService.create_screen(
                    manager_user=request.user,
                    class_id=request.POST.get('target_class_id'),
                    screen_name=request.POST.get('screen_name')
                )
                messages.success(request, "تمت إضافة الشاشة الذكية للفصل.")

            elif action == 'update_screen' and screen_id:
                is_active_val = request.POST.get('is_active') == 'true'
                data = {
                    'screen_name': request.POST.get('screen_name'),
                    'class_id': request.POST.get('target_class_id'),
                    'is_active': is_active_val  
                }
                SmartScreenService.update_screen(request.user, screen_id, data)
                messages.success(request, "تم تحديث بيانات الشاشة.")

            elif action == 'deactivate_screen' and screen_id:
                SmartScreenService.deactivate_screen(request.user, screen_id)
                messages.success(request, "تم تعطيل الشاشة بنجاح.")

        except Exception as e:
            messages.error(request, f"خطأ في العملية: {str(e)}")
        
        return redirect('web_class') # افترضت أن هذا هو اسم الرابط في urls.py

    # --- 2. معالجة البحث والبيانات (GET) ---
    search_class = request.GET.get('search_class', '')
    search_screen = request.GET.get('search_screen', '')
    
    # استعلام الفصول
    classes_list = SchoolClass.objects.filter(school=school).order_by('number')
    if search_class:
        classes_list = classes_list.filter(
            Q(name__icontains=search_class) | Q(number__icontains=search_class)
        )
    
    # استعلام الشاشات
    screens_list = SmartScreen.objects.filter(school=school).select_related('school_class')
    if search_screen:
        screens_list = screens_list.filter(Q(screen_name__icontains=search_screen))

    # التقسيم للفصول فقط (كمثال)
    paginator = Paginator(classes_list, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'class.html', {
        'classes': page_obj,
        'all_classes': SchoolClass.objects.filter(school=school, is_active=True), 
        'screens': screens_list,
        'search_class': search_class,
        'search_screen': search_screen,
        'school': school
    })