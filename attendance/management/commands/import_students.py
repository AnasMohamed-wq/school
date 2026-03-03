import os
import pdfplumber
from django.core.management.base import BaseCommand
from django.db import transaction
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
            file_name = os.path.basename(file_path)
            class_name = file_name.replace('معلومات ', '').replace('.pdf', '').strip()

            self.stdout.write(self.style.WARNING(f'جاري معالجة الملف: {file_name}'))

            with pdfplumber.open(file_path) as pdf:
                all_rows = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        # نتجاوز الهيدر إذا كان موجوداً
                        for row in table:
                            if row and "الاسم" not in str(row[0]):
                                all_rows.append(row)

            with transaction.atomic():
                school_class, _ = SchoolClass.objects.get_or_create(
                    school=school,
                    name=class_name,
                    defaults={'number': '1'}
                )

                count = 0
                for row in all_rows:
                    # تنظيف الصف من القيم الفارغة
                    row = [str(item).strip() if item else "" for item in row]
                    
                    # ملفك يحتوي على 6 أعمدة (3 للطالب الأول و 3 للطالب الثاني)
                    # سنقوم بتقسيم الصف إلى مجموعتين
                    groups = [row[0:3], row[3:6]]
                    
                    for group in groups:
                        if len(group) < 3: continue
                        
                        student_name = group[0]
                        mother_phone = group[1]
                        father_phone = group[2]

                        # التحقق من وجود اسم طالب فعلي (تجاهل الخلايا الفارغة)
                        if not student_name or student_name in ["None", "", "nan"]:
                            continue

                        # إنشاء الطالب
                        student = Student.objects.create(
                            school=school,
                            school_class=school_class,
                            full_name=student_name
                        )

                        # معالجة الهواتف
                        phones = [mother_phone, father_phone]
                        for ph in phones:
                            if ph and len(ph) >= 9: # التحقق من طول رقم الهاتف
                                clean_phone = ph.replace('\n', '').split('.')[0].strip()
                                
                                # إنشاء مستخدم ولي الأمر
                                user, created = User.objects.get_or_create(
                                    phone=clean_phone,
                                    defaults={
                                        'full_name': f"ولي أمر {clean_phone}",
                                        'role': 'PARENT',
                                    }
                                )
                                if created:
                                    user.set_password('123456')
                                    user.save()

                                parent_profile, _ = Parent.objects.get_or_create(user=user)
                                StudentParent.objects.get_or_create(student=student, parent=parent_profile)
                        
                        count += 1

            self.stdout.write(self.style.SUCCESS(f'تمت العملية! تم استيراد {count} طالب بنجاح.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ: {str(e)}'))
