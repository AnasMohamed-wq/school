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
            {"name": "ارين محمد طارق الخوتاني", "phones": ["0555630551", "0555630550"]},
            {"name": "ليان زياد بن محمد المارديني", "phones": ["0537260066", "0505439683"]},
            {"name": "أوس عزمي سراج رحيله", "phones": ["0568109783", "0569992278"]},
            {"name": "ليلى سلطان بهجت الزغيبي", "phones": ["0530162333", "0560026810"]},
            {"name": "اياد محمد سعود سندي", "phones": ["0550640336", "0531459125"]},
            {"name": "ليلى هشام خالد الحربي", "phones": ["0560948010", "0500036390"]},
            {"name": "ايميليا رائد بدر كلجي", "phones": ["0550789885", "0555050212"]},
            {"name": "محمد مصطفى بدر الحربي", "phones": ["0532980891", "0566122355"]},
            {"name": "تالا احمد بن جباره الأحمدي", "phones": ["0531421900", "0536763464"]},
            {"name": "مريم محمد بن عودة الردادي", "phones": ["0553163456", "0533310416"]},
            {"name": "تالين عبدالله بن حمد المحيميد", "phones": ["0544541525", "0505304323"]},
            {"name": "معاذ فهد بن محمد الصبحي", "phones": ["0569300057", "0500204683"]},
            {"name": "تميم أحمد بن علي الغامدي", "phones": ["0504144365", "0555589133"]},
            {"name": "مودة ماجد بن محمد الحجيلي", "phones": ["0569446416", "0565553133"]},
            {"name": "جوري ابراهيم بن عبدالله الردادي", "phones": ["0540445663", "0546648834"]},
            {"name": "ميار فهد بن حامد الصبحي", "phones": ["0548174411", "0540090881"]},
            {"name": "جوى أحمد بن عواده الاحمدي", "phones": ["0503328211", "0506307338"]},
            {"name": "نايف ممدوح بن مفلح الرشيدي", "phones": ["0541170068", "0551170068"]},
            {"name": "حور خالد بن مرزوق العوفي", "phones": ["0561561026", "0561561026"]},
            {"name": "نبراس عمار بن محمد الجهني", "phones": ["0563450007", "0540055745"]},
            {"name": "رنا محمد بن مصلح الصاعدي", "phones": ["0534567228", "0553317781"]},
            {"name": "هيفاء خالد بن دخيل الله المحمدي", "phones": ["0544320448", "0544133446"]},
            {"name": "ريتاج راضي بن سليم العروي", "phones": ["0564885856", "0562505030"]},
            {"name": "وسن حميد بن حامد الصاعدي", "phones": ["0553413554", "0540026601"]},
            {"name": "ريف محمد بن راشد الفريدي", "phones": ["0558113400", "0503327242"]},
            {"name": "يارا وليد بن غازي الرحيلي", "phones": ["0544577822", "0566412128"]},
            {"name": "سديم فواز بن لافي الحربي", "phones": ["0546252203", "0555317783"]},
            {"name": "ياسمين وليد بن سالم الصاعدي", "phones": ["0558172102", "0555301886"]},
            {"name": "شادن منير بن حميد المحمدي", "phones": ["0545466882", "0544315518"]},
            {"name": "يزن مشاري بن غازي العوفي", "phones": ["0566363539", "0500122261"]},
            {"name": "شموخ عيسى بن عوده المحمدي", "phones": ["0544186675", "0544317130"]},
            {"name": "يوسف مروان بن جميل حكيم", "phones": ["0540026511", "0540026511"]},
            {"name": "عادل ابراهيم بن عادل سمان", "phones": ["0555325411", "0544422340"]},
            {"name": "عبدالملك خالد بن حامد الجابري", "phones": ["0508112117", "0553313010"]},
            {"name": "غلا مشعل بن فريح الحازمي", "phones": ["0544301550", "0503323060"]},
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
