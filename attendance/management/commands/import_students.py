import os
import pdfplumber
from django.core.management.base import BaseCommand
from django.db import transaction
# استبدل 'core' باسم تطبيقك
from attendance.models import User, Parent, School, SchoolClass, Student, StudentParent 

class Command(BaseCommand):
    help = 'استيراد بيانات الطلاب من ملف PDF'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='مسار ملف الـ PDF')
        parser.add_argument('school_id', type=int, help='ID المدرسة')

    def handle(self, *args, **options):
        file_path = options['file_path']
        school_id = options['school_id']

        try:
            school = School.objects.get(id=school_id)
            # استخراج اسم الفصل من اسم الملف (مثلاً: فصل الانجاز)
            file_name = os.path.basename(file_path)
            class_name = file_name.replace('معلومات ', '').replace('.pdf', '').strip()

            with pdfplumber.open(file_path) as pdf:
                all_rows = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        # نتجاوز الهيدر (الاسم، رقم الام، رقم الاب)
                        all_rows.extend(table[1:]) 

            with transaction.atomic():
                # 1. تجهيز الفصل
                school_class, _ = SchoolClass.objects.get_or_create(
                    school=school,
                    name=class_name,
                    defaults={'number': '1'}
                )

                count = 0
                for row in all_rows:
                    # بناءً على ملفك، الجدول مقسم لـ 6 أعمدة (طالبين في كل سطر)
                    # سنعالج كل 3 أعمدة كمجموعة (اسم، هاتف_أم، هاتف_أب)
                    for i in range(0, len(row), 3):
                        if i+2 >= len(row): break
                        
                        s_name = str(row[i]).strip() if row[i] else None
                        m_phone = str(row[i+1]).strip() if row[i+1] else None
                        f_phone = str(row[i+2]).strip() if row[i+2] else None

                        if not s_name or s_name == "الاسم": continue

                        # 2. إنشاء الطالب
                        student = Student.objects.create(
                            school=school,
                            school_class=school_class,
                            full_name=s_name
                        )

                        # 3. معالجة الهواتف (الأم والأب)
                        for phone in [m_phone, f_phone]:
                            if phone and len(phone) > 5: # التحقق من صحة الرقم
                                clean_phone = phone.replace('\n', '').strip()
                                
                                # إنشاء مستخدم (رقم الهاتف هو الاسم)
                                user, created = User.objects.get_or_create(
                                    phone=clean_phone,
                                    defaults={
                                        'full_name': f"ولي أمر {clean_phone}",
                                        'role': 'PARENT',
                                    }
                                )
                                if created:
                                    user.set_password('123456') # كلمة مرور افتراضية
                                    user.save()

                                parent_profile, _ = Parent.objects.get_or_create(user=user)
                                StudentParent.objects.get_or_create(student=student, parent=parent_profile)
                        
                        count += 1

            self.stdout.write(self.style.SUCCESS(f'تم بنجاح استيراد {count} طالب لفصل {class_name}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'حدث خطأ: {str(e)}'))
