from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from attendance.models import (
    User, Parent, School, SchoolClass, 
    Student, StudentParent, ParentSchool
)

class Command(BaseCommand):
    help = 'الربط الذكي للطلاب وأولياء الأمور ومنع تكرار البيانات'

    def handle(self, *args, **options):
        school_id = 1
        class_name = "فصل الانجاز"

        students_data = [
            {"name": "ابراهيم معتز ابراهيم التويم", "phones": ["0543282003", "0564948838"]},
            {"name": "فرح علاء بن منسي الحربي", "phones": ["0582610031", "059596910"]},
            # ... بقية البيانات كما هي في القائمة السابقة
        ]

        try:
            school = School.objects.get(id=school_id)
            
            with transaction.atomic():
                # 1. التأكد من وجود الفصل
                school_class, _ = SchoolClass.objects.get_or_create(
                    school=school,
                    name=class_name,
                    defaults={'number': '1'}
                )

                for data in students_data:
                    # 2. البحث عن الطالب أو تحديثه (منع التكرار بالاسم والمدرسة)
                    student, created = Student.objects.update_or_create(
                        school=school,
                        full_name=data["name"],
                        defaults={
                            'school_class': school_class,
                            'is_active': True
                        }
                    )
                    
                    status_msg = "إنشاء جديد" if created else "تحديث بيانات"
                    self.stdout.write(f"معالجة الطالب: {student.full_name} ({status_msg})")

                    for ph in data["phones"]:
                        clean_phone = ph.strip()
                        if not clean_phone or len(clean_phone) < 9:
                            continue

                        # 3. التعامل مع المستخدم (البحث برقم الهاتف الفريد)
                        user, u_created = User.objects.get_or_create(
                            phone=clean_phone,
                            defaults={
                                'full_name': f"ولي أمر {data['name']}",
                                'role': 'PARENT',
                                'is_active': True
                            }
                        )

                        # 4. التأكد من وجود بروفايل ولي الأمر وتفعيله
                        parent_profile, _ = Parent.objects.get_or_create(
                            user=user,
                            defaults={'is_active': True}
                        )

                        # 5. ربط ولي الأمر بالمدرسة (تحديث الربط لو وجد مسبقاً)
                        ParentSchool.objects.update_or_create(
                            parent=parent_profile,
                            school=school,
                            defaults={
                                'is_approved': True,
                                'approved_at': timezone.now()
                            }
                        )

                        # 6. ربط ولي الأمر بالابن (منع تكرار العلاقة)
                        StudentParent.objects.get_or_create(
                            student=student, 
                            parent=parent_profile
                        )

            self.stdout.write(self.style.SUCCESS('تمت عملية الربط والتحديث بنجاح دون تكرار سجلات.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'فشل السكربت: {str(e)}'))
