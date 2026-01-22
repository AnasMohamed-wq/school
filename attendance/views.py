from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from .serializers import common , manager,parent,PickupRequest,screen,teacher
from .services.identity_services import *
from .services.business_services import *
from .services.notification_services import *
from .permissions import IsAuthenticatedAndActive, IsParent , IsTeacher ,IsSchoolManager, authorize_request # استيراد الصلاحيات
from .models import *



# login
class LoginView(APIView):
    """
    View مخصصة لتسجيل الدخول باستخدام رقم الهاتف وكلمة المرور
    تستخدم AuthService لتوليد توكن يحتوي على Role المستخدم
    """
    permission_classes = [AllowAny] # السماح للجميع بالوصول لمحاولة الدخول

    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')

        # التحقق من وجود البيانات المطلوبة في الطلب
        if not phone or not password:
            return Response(
                {"error": "يرجى تقديم رقم الهاتف وكلمة المرور"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # استدعاء الخدمة التي شرحناها سابقاً
            auth_data =AuthService.login_user(phone, password)
            
            # في حال النجاح، نرسل التوكنات والـ Role
            return Response(auth_data, status=status.HTTP_200_OK)

        except Exception as e:
            # التعامل مع الأخطاء (بيانات خاطئة، حساب معطل، إلخ)
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        

class LogoutView(APIView):
    """
    تسجيل الخروج عبر وضع الـ Refresh Token في القائمة السوداء.
    """
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        
        if not refresh_token:
            return Response(
                {"error": "Refresh token مطلوب لإتمام العملية"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            AuthService.logout_user(refresh_token)
            # إضافة تسجيل للعملية (Auditing)
            logger.info(f"User {request.user.id} logged out successfully") #
            return Response({"message": "تم تسجيل الخروج بنجاح"}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)



class ParentSchoolListView(generics.ListAPIView):
    """عرض المدارس المرتبط بها ولي الأمر وموافقة الإدارة عليها"""
    permission_classes = [IsAuthenticatedAndActive, IsParent]
    serializer_class = common.SchoolSerializer

    def get_queryset(self):
        # (4.2) لا نعتمد على الفلترة فقط، بل نضمن أن العلاقة مفعلة (is_approved)
        user = self.request.user
        return School.objects.filter(
            parentschool__parent__user=user, 
            parentschool__is_approved=True,
            is_active=True # ضمان أن المدرسة نفسها لا تزال نشطة في النظام
        )
    
class StudentListView(generics.ListAPIView):
    """عرض أبناء ولي الأمر في مدرسة محددة"""
    permission_classes = [IsAuthenticatedAndActive, IsParent]
    serializer_class = parent.ParentStudentSerializer

    def get_queryset(self):
        school_id = self.request.query_params.get('school_id')
        user = self.request.user
        
        # (16) التحقق المزدوج: الطالب ينتمي للأب + الطالب ينتمي للمدرسة المحددة
        return Student.objects.filter(
            studentparent__parent__user=user, 
            school_id=school_id,
            school__parentschool__parent__user=user, # ضمان أن الأب مسجل في هذه المدرسة
            school__parentschool__is_approved=True,  # وضمان أن تسجيله مقبول
            is_active=True
        ).distinct()

class CreateRequestView(APIView):


    permission_classes = [IsAuthenticatedAndActive, IsParent] # (4.1) تفعيل الصلاحيات

    """إنشاء طلب استلام جديد بعد التحقق من الموقع"""
    def post(self, request):
        serializer = PickupRequest.CreatePickupRequestSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                # (5.1) الـ View ينادي الخدمة فقط والخدمة هي من تطلق الـ WebSocket
                AttendanceService.process_pickup_request(
                    user=request.user,
                    student_id=serializer.validated_data['student'].id,
                    lat=serializer.validated_data.get('lat'),
                    lng=serializer.validated_data.get('lng')
                )
                return Response({"message": "تم إرسال طلب الاستلام بنجاح"}, status=status.HTTP_201_CREATED)
            
            except ValidationError as e:
                # (5.2) توحيد سلوك الخطأ لرسائل منطق الأعمال
                return Response({"detail": str(e.detail[0] if isinstance(e.detail, list) else e.detail)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"detail": "حدث خطأ غير متوقع"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#   واجهات الأستاذ

class ClassDashboardView(APIView):

    permission_classes = [IsAuthenticatedAndActive, IsTeacher]

    """إحصائيات سريعة لفصل الأستاذ"""
    def get(self, request):
        # (16) التحقق من وجود وصحة ملف المعلم قبل جلب البيانات
        teacher_profile = getattr(request.user, 'teacher', None)
        if not teacher_profile or not teacher_profile.is_active:
            return Response({"error": "حساب المعلم غير نشط أو غير موجود"}, status=403)
            
        # نضمن أن الإحصائيات فقط للفصل الموكل لهذا المعلم في مدرسته
        students = Student.objects.filter(
            school_class=teacher_profile.school_class,
            school=teacher_profile.school,
            is_active=True
        )
        
        return Response({
            "total": students.count(),
            "present": students.filter(status='PRESENT').count(),
            "requested": students.filter(status='REQUESTED').count(),
            "at_gate": students.filter(status='AT_GATE').count(),
            "delivered": students.filter(status='DELIVERED').count(),
        })
   



class ActiveRequestsView(generics.ListAPIView):
    """عرض الطلبات النشطة (التي لم تكتمل بعد) للفصل"""
    permission_classes = [IsAuthenticatedAndActive, IsTeacher]
    serializer_class = teacher.TeacherPickupRequestSerializer

    def get_queryset(self):
        user = self.request.user
        # (16) الوصول للملف عبر getattr بأمان كما اتفقنا
        teacher_profile = getattr(user, 'teacher', None)
        
        if not teacher_profile or not teacher_profile.school_class:
            return PickupRequest.objects.none()

        # (4.2) عزل البيانات: الطلبات فقط لطلاب فصل المعلم وفي مدرسته حصراً
        return PickupRequest.objects.filter(
            student__school_class=teacher_profile.school_class,
            student__school=teacher_profile.school,
            status__in=['CREATED', 'ACCEPTED'],
            student__is_active=True
        ).order_by('requested_at')
    
#واجهات الإدارة


class ApprovalActionView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsSchoolManager]

    """تفعيل ولي الأمر للمدرسة وتوليد التوكن الخاص به"""
    def post(self, request, parent_id):
        school_id = request.data.get('school_id')
        
        # استخدام الدالة الموحدة للتحقق من صلاحية المدير على هذه المدرسة
        school = authorize_request(request, school_id)
            
        try:
            ps_relation = ParentSchool.objects.get(parent_id=parent_id, school_id=school.id)
            ps_relation.is_approved = True
            ps_relation.approved_by = request.user
            ps_relation.save()
            return Response({"message": "تم تفعيل حساب ولي الأمر بنجاح"})
        except ParentSchool.DoesNotExist:
            return Response({"error": "علاقة ولي الأمر بالمدرسة غير موجودة"}, status=404)


