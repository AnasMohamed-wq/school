# attendance/management/commands/reset_school_day.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from attendance.models import Student, PickupRequest
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'تصفير حالات الطلاب وإغلاق الطلبات المعلقة يومياً'

    def handle(self, *args, **options):
        self.stdout.write("جاري بدء عملية التصفير اليومي...")
        
        try:
            with transaction.atomic():
                # 1. إعادة كافة الطلاب إلى حالة حاضر
                students_updated = Student.objects.exclude(status='PRESENT').update(status='PRESENT')
                
                # 2. إغلاق كافة طلبات الاستلام التي لم تكتمل
                requests_closed = PickupRequest.objects.filter(
                    status__in=['CREATED', 'ACCEPTED']
                ).update(
                    status='COMPLETED', 
                    completed_at=timezone.now()
                )

                self.stdout.write(self.style.SUCCESS(
                    f"تم التصفير بنجاح: {students_updated} طالب، {requests_closed} طلب."
                ))
                logger.info("Daily reset completed successfully via management command.")
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"حدث خطأ: {str(e)}"))
            logger.error(f"Daily reset failed: {str(e)}")