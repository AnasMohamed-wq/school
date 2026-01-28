from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
import uuid
import secrets , random , string 

# تعريف الحالات في كلاس منفصل ليكون المرجع الوحيد
class StudentStatus:
    PRESENT = 'PRESENT'
    REQUESTED = 'REQUESTED'
    AT_GATE = 'AT_GATE'
    DELIVERED = 'DELIVERED'

    CHOICES = (
        (PRESENT, 'Present'),
        (REQUESTED, 'Requested'),
        (AT_GATE, 'At Gate'),
        (DELIVERED, 'Delivered'),
    )

    # مصفوفة الانتقالات المسموحة
    TRANSITIONS = {
        PRESENT: [REQUESTED],
        REQUESTED: [AT_GATE, PRESENT], # سمحنا بالعودة لـ Present في حال الإلغاء
        AT_GATE: [DELIVERED],
        DELIVERED: [], 
    }

class UserManager(BaseUserManager):
    def create_user(self, phone, full_name, password=None, **extra_fields):
        if not phone:
            raise ValueError('يجب وضع رقم هاتف')
        user = self.model(phone=phone, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'SUPER_ADMIN')
        return self.create_user(phone, full_name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ('PARENT', 'Parent'),
        ('TEACHER', 'Teacher'),
        ('MANAGER', 'schoolmanager'),
        ('SUPER_ADMIN', 'Super Admin'),
    ]

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLES)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager() # ربط المدير بالكلاس
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['full_name']


    # (1.3) التحقق من وجود Profile مطابق للدور
    def clean(self):
        super().clean()

        if not self.pk:
            return  # لا نتحقق عند الإنشاء

        role_profile_map = {
            'PARENT': 'parent',
            'TEACHER': 'teacher',
            'MANAGER': 'schoolmanager',
        }

        expected_profile = role_profile_map.get(self.role)

        if expected_profile and not hasattr(self, expected_profile):
            raise ValidationError(
                f"Profile {expected_profile} مفقود لهذا المستخدم"
            )
        


    def __str__(self):
        return f"{self.full_name} ({self.role})"


class School(models.Model):
    LOCATION_METHODS = (
    ('GPS', 'GPS'),
    ('WIFI', 'WiFi'),
    ('BARCODE', 'Barcode'),
    )


    name = models.CharField(max_length=255)
    public_code = models.CharField(max_length=50, unique=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_radius = models.IntegerField(default=100)
    location_method = models.CharField(max_length=10, choices=LOCATION_METHODS)
    is_active = models.BooleanField(default=True)

    def generate_public_code(self):
        """
        يولد كودًا عامًا للمدرسة
        مثال: SCH-48392
        """
        return f"SCH-{random.randint(10000, 99999)}"

    def save(self, *args, **kwargs):
        if not self.public_code:
            self.public_code = self.generate_public_code()
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name


class SchoolManager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.full_name}"


class SchoolClass(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.school.name} - {self.name}"
    

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)


class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.full_name} "


class ParentSchool(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    parent_school_token = models.CharField(max_length=255, unique=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
  


    class Meta:
        unique_together = ('parent', 'school')

    def generate_parent_school_token(self):
        """
        توكن قوي وآمن
        """
        return f"ps_{secrets.token_urlsafe(32)}"

    def save(self, *args, **kwargs):
        if not self.parent_school_token:
            self.parent_school_token = self.generate_parent_school_token()
        super().save(*args, **kwargs)
    
    
    
 
class Student(models.Model):

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    student_code = models.CharField(max_length=100 , unique=True)
    status = models.CharField(max_length=20, choices=StudentStatus.CHOICES, default=StudentStatus.PRESENT)
    is_active = models.BooleanField(default=True)


    def generate_student_code(self):
        """
        مثال:
        SCH1-CLS3-0007
        """
        school_part = f"SCH{self.school.id}"
        class_part = f"CLS{self.school_class.id}"

        last_student = (
            Student.objects
            .filter(school=self.school, school_class=self.school_class)
            .exclude(student_code='')
            .count()
            + 1
        )

        return f"{school_part}-{class_part}-{str(last_student).zfill(4)}"


    # (1.1) حماية حالة الطالب داخل الموديل
    def change_status(self, new_status):
        """
        تغيير الحالة بدون حفظ.
        الحفظ يتم حصريًا داخل Service.
        """
        if new_status not in StudentStatus.TRANSITIONS.get(self.status, []):
            raise ValidationError(
                f"Invalid transition from {self.status} to {new_status}"
            )
        self.status = new_status

    def save(self, *args, **kwargs):
        if not self.student_code:
            self.student_code = self.generate_student_code()
        super().save(*args, **kwargs)


    def __str__(self):
        return self.full_name
    

class StudentParent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)


    class Meta:
        unique_together = ('student', 'parent')



    



class PickupRequest(models.Model):
    STATUS_CHOICES = (
        ('CREATED', 'Created'),
        ('ACCEPTED', 'Accepted'),
        ('COMPLETED', 'Completed'),
    )


    school = models.ForeignKey(School, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # (1.2) منع وجود أكثر من طلب نشط لنفس الطالب بقيد على مستوى DB
        constraints = [
            models.UniqueConstraint(
                fields=['student'], 
                condition=models.Q(status__in=['CREATED', 'ACCEPTED']),
                name='unique_active_pickup_request'
            )
        ]

    def clean(self):
        # ضمان أن الطالب والمدرسة والطلب في نطاق واحد
        if self.student.school != self.school:
            raise ValidationError("Student must belong to the same school as the request.")


class SmartScreen(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    screen_name = models.CharField(max_length=100)
    screen_token = models.CharField(max_length=255, unique=True, editable=False)
    is_active = models.BooleanField(default=True)


    def generate_screen_token(self):
        return str(uuid.uuid4())

    def save(self, *args, **kwargs):
        if not self.screen_token:
            self.screen_token = self.generate_screen_token()
        super().save(*args, **kwargs)





