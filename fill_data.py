import os
import django
import random
import uuid
from django.utils import timezone
from faker import Faker

# 1. إعداد بيئة Django (تأكد من تغيير 'myproject' لاسم مجلد مشروعك)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

# 2. استيراد الموديلات بعد عمل django.setup()
from attendance.models import (
    User, School, SchoolClass, Teacher, Parent, 
    Student, StudentParent, SchoolManager, ParentSchool, StudentStatus
)

fake = Faker('ar_SA')
PASSWORD = "poiu0987"
current_phone_int = 0

def get_next_phone():
    global current_phone_int
    phone = str(current_phone_int).zfill(5)
    current_phone_int += 1
    return phone

def run_seeder():
    print("🚀 جاري تنظيف قاعدة البيانات وبدء الإنشاء...")
    
    # اختيار اختياري: مسح البيانات القديمة لتجنب التكرار
    # User.objects.all().delete()
    # School.objects.all().delete()

    for s_idx in range(1, 11):
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
        classes = []
        for c_idx in range(1, 11):
            s_class = SchoolClass.objects.create(
                school=school,
                name=f"فصل {c_idx}",
                number=f"{c_idx}"
            )
            classes.append(s_class)

        # إنشاء 15 مدرس
        for _ in range(15):
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
                    full_name=f"ولي أمر {student.full_name}",
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

if __name__ == "__main__":
    run_seeder()