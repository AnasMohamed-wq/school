import os
import django
import random
import uuid
from django.utils import timezone
from faker import Faker
from django.db import transaction



# 1. إعداد بيئة Django (تأكد من تغيير 'myproject' لاسم مجلد مشروعك)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()
from django.conf import settings
settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# 2. استيراد الموديلات بعد عمل django.setup()
from attendance.models import (
    User, School, SchoolClass, Teacher, Parent, 
    Student, StudentParent, SchoolManager, ParentSchool, StudentStatus ,PickupRequest ,
    SmartScreen
)

fake = Faker('ar_SA')
PASSWORD = "poiu0987"
current_phone_int = 0

def get_next_phone():
    global current_phone_int
    phone = str(current_phone_int).zfill(5)
    current_phone_int += 1
    return phone


def clean_database_except_super_admin():
    print("🧹 تنظيف قاعدة البيانات (مع الإبقاء على Super Admin)...")

    with transaction.atomic():
        # حذف الطلبات
        PickupRequest.objects.all().delete()
        SmartScreen.objects.all().delete()
        # علاقات
        StudentParent.objects.all().delete()
        ParentSchool.objects.all().delete()

        # كيانات
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        Parent.objects.all().delete()
        SchoolClass.objects.all().delete()
        SchoolManager.objects.all().delete()
        School.objects.all().delete()

        # حذف المستخدمين ما عدا Super Admin
        User.objects.exclude(role="SUPER_ADMIN").delete()

    print("✅ تم تنظيف قاعدة البيانات بنجاح")



def run_seeder():
    print("🚀 جاري تنظيف قاعدة البيانات وبدء الإنشاء...")
    clean_database_except_super_admin()

    
    
    for s_idx in range(1, 2):
        # إنشاء المدرسة
        school = School.objects.create(
            name=f"مدرسة {fake.company()}",
            public_code=f"SCH-{uuid.uuid4().hex[:6].upper()}",
            location_lat=24.7,
            location_lng=46.6,
            location_method='GPS'
        )
        print(f"✅ تم إنشاء: {school.name}")

        # إنشاء مدير المدرسة
        manager_user = User.objects.create_user(
            phone=get_next_phone(),
            full_name=fake.name(),
            password=PASSWORD,
            role='MANAGER'
        )
        SchoolManager.objects.create(user=manager_user, school=school)

        # إنشاء 10 فصول
        # إنشاء 10 فصول
        classes = []
        for c_idx in range(1, 3):
            s_class = SchoolClass.objects.create(
                school=school,
                name=f"فصل {fake.name()} {c_idx}",
                number=f"{c_idx}"
            )
            classes.append(s_class)

            # --- إضافة: إنشاء الشاشات الذكية لكل فصل ---
            # نقوم بإنشاء شاشة واحدة لكل فصل يتم إنشاؤه
            smart_screen = SmartScreen.objects.create(
                school=school,          # ربطها بالمدرسة الحالية
                school_class=s_class,   # ربطها بالفصل الحالي
                screen_name=f"شاشة {s_class.name}",
                is_active=True
                # الـ screen_token سيتم إنشاؤه تلقائياً بواسطة uuid4 كما هو محدد في الموديل
            )
            # السطر الصحيح
            print(f"   🖥️ تم إنشاء شاشة للفصل: {s_class.name} (Token: {str(smart_screen.screen_token)[:8]}...)")

        # إنشاء 10 مدرس
        for _ in range(3):
            t_user = User.objects.create_user(
                phone=get_next_phone(),
                full_name=fake.name(),
                password=PASSWORD,
                role='TEACHER'
            )
            Teacher.objects.create(
                user=t_user,
                school=school,
                school_class=random.choice(classes)
            )

        # إنشاء 100 طالب
        for st_idx in range(100):
            student = Student.objects.create(
                school=school,
                school_class=random.choice(classes),
                full_name=fake.name(),
                student_code=f"ID-{school.id}-{st_idx}-{random.randint(100,999)}",
                status=StudentStatus.PRESENT
            )

            # ولي أمر واحد أو اثنين
            num_parents = random.randint(1, 2)
            for p_idx in range(num_parents):
                p_user = User.objects.create_user(
                    phone=get_next_phone(),
                    full_name=f"ولي أمر {fake.name()}",
                    password=PASSWORD,
                    role='PARENT',
                    is_active=(p_idx == 0) # الأول نشط، الثاني لا
                )
                parent_profile, _ = Parent.objects.get_or_create(user=p_user)
                
                ParentSchool.objects.get_or_create(
                    parent=parent_profile,
                    school=school,
                    defaults={'parent_school_token': str(uuid.uuid4()), 'is_approved': True}
                )
                StudentParent.objects.create(student=student, parent=parent_profile)

    print(f"✨ اكتملت العملية! إجمالي الهواتف المستخدمة: {current_phone_int}")

def print_websocket_links():
    print("\n" + "="*50)
    print("🔗 روابط اختبار الشاشات الذكية (WebSockets)")
    print("="*50)
    
    screens = SmartScreen.objects.all().select_related('school', 'school_class')
    
    if not screens.exists():
        print("❌ لا توجد شاشات في قاعدة البيانات.")
        return

    for screen in screens:
        # بناء الرابط بناءً على المسار الذي وضعناه في routing.py
        # ws://127.0.0.1:8000/ws/pickup/screen/ID_المدرسة/ID_الفصل/?token=TOKEN
        link = (
            f"wss://used-alex-techcodesdn-bdb25f1f.koyeb.app/ws/pickup/screen/"
            f"{screen.school.id}/{screen.school_class.id}/"
            f"?token={screen.screen_token}"
        )
        
        print(f"🏫 مدرسة: {screen.school.name}")
        print(f"🏢 فصل: {screen.school_class.name}")
        print(f"🌐 الرابط: {link}")
        print("-" * 30)


if __name__ == "__main__":
    run_seeder()
    print_websocket_links()