import os
import django
import uuid
import sys
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()

from attendance.models import (
    User, School, SchoolClass, Teacher, Parent,
    Student, StudentParent, SchoolManager, ParentSchool, StudentStatus, PickupRequest
)
from django.db import transaction

def clean_database_except_super_admin():
    print("🧹 تنظيف قاعدة البيانات (مع الإبقاء على Super Admin)...")

    with transaction.atomic():
        # حذف الطلبات
        PickupRequest.objects.all().delete()

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



PASSWORD = "poiu0987"

# =============================
# 📞 إدارة أرقام الهواتف
# =============================
PHONE_COUNTER = 0

def next_phone():
    global PHONE_COUNTER
    phone = str(PHONE_COUNTER).zfill(5)
    PHONE_COUNTER += 1
    return phone


# =============================
# 👑 Super Admin
# =============================
def create_super_admin():
    if not User.objects.filter(role="SUPER_ADMIN").exists():
        User.objects.create_superuser(
            phone=next_phone(),  # 00000
            full_name="Super Admin",
            password=PASSWORD
        )


# =============================
# 🏫 المدارس
# =============================
def create_school(index):
    return School.objects.create(
        name=f"مدرسة المستقبل النموذجية {index}",
        public_code=f"SCH-{index:03}",
        location_method="GPS",
        location_lat=24.7,
        location_lng=46.6
    )


def create_school_manager(school, index):
    user = User.objects.create_user(
        phone=next_phone(),  # بعد الأدمن مباشرة
        full_name=f"مدير المدرسة {index}",
        password=PASSWORD,
        role="MANAGER"
    )
    SchoolManager.objects.create(user=user, school=school)


# =============================
# 🧑‍🏫 الفصول والأساتذة
# =============================
def create_classes_and_teachers(school):
    classes = []
    sections = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

    for i in range(10):
        class_name = f"الصف {i + 1} - {sections[i]}"
        school_class = SchoolClass.objects.create(
            school=school,
            name=class_name,
            number=str(i + 1)
        )
        classes.append(school_class)

        teacher_user = User.objects.create_user(
            phone=next_phone(),
            full_name=f"الأستاذ {class_name}",
            password=PASSWORD,
            role="TEACHER"
        )
        Teacher.objects.create(
            user=teacher_user,
            school=school,
            school_class=school_class
        )

    return classes


# =============================
# 👨‍👩‍👦 الطلاب وأولياء الأمور
# =============================
def create_students_and_parents(school, classes):
    student_index = 1

    for school_class in classes:
        for i in range(10):  # 10 طلاب لكل فصل
            student_name = f"طالب {student_index} محمد احمد"
            father_name = f"محمد احمد"

            student = Student.objects.create(
                school=school,
                school_class=school_class,
                full_name=student_name,
                student_code=f"STD-{school.id}-{student_index}",
                status=StudentStatus.PRESENT
            )

            # ولي الأمر
            parent_user = User.objects.create_user(
                phone=next_phone(),
                full_name=father_name,
                password=PASSWORD,
                role="PARENT"
            )
            parent = Parent.objects.create(user=parent_user)

            ParentSchool.objects.create(
                parent=parent,
                school=school,
                parent_school_token=str(uuid.uuid4()),
                is_approved=True
            )

            StudentParent.objects.create(
                student=student,
                parent=parent
            )

            student_index += 1


# =============================
# 🚀 التشغيل
# =============================
def run():
    print("🚀 بدء إنشاء البيانات ...")

    create_super_admin()
    clean_database_except_super_admin()  # ← 🔥 الجديد

    for i in range(1, 11):  # 10 مدارس
        school = create_school(i)
        print(f"🏫 تم إنشاء {school.name}")

        create_school_manager(school, i)
        classes = create_classes_and_teachers(school)
        create_students_and_parents(school, classes)

    print("✅ اكتمل إنشاء البيانات بنجاح")
    print(f"📞 آخر رقم هاتف مستخدم: {PHONE_COUNTER - 1}")


if __name__ == "__main__":
    run()
