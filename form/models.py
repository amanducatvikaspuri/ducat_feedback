from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_delete
from django.dispatch import receiver

class Student(models.Model):
    sid = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    course = models.CharField(max_length=100)
    current_batch = models.ForeignKey('dashboard.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='enrolled_students')
    joining_date = models.DateField(default=timezone.now)
    BRANCH_CHOICES = [
        ('Vikaspuri', 'Vikaspuri'),
        ('Pitampura', 'Pitampura'),
        ('South Ex', 'South Ex'),
        ('Noida', 'Noida'),
        ('Gurgaon', 'Gurgaon'),
        ('Ghaziabad', 'Ghaziabad'),
    ]
    semester = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=20, blank=True, null=True)
    branch = models.CharField(max_length=50, choices=BRANCH_CHOICES, default='Vikaspuri')

    def __str__(self):
        return f"{self.sid} - {self.name}"

class WhatsAppMessageLog(models.Model):
    STATUS_CHOICES = [('Sent', 'Sent'), ('Failed', 'Failed')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    batch = models.ForeignKey('dashboard.Batch', on_delete=models.SET_NULL, null=True)
    message_body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error_response = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.status} to {self.student.name} at {self.sent_at}"

class Attendance(models.Model):
    WEEK_CHOICES = [
        ('Weekdays', 'Weekdays'),
        ('Weekend', 'Weekend'),
    ]
    MODE_CHOICES = [
        ('Online', 'Online'),
        ('Offline', 'Offline'),
    ]
    TECHNOLOGY_CHOICES = [
        ('DATA ANALYTICS & AI', 'DATA ANALYTICS & AI'),
        ('DATA ANALYTICS & GEN AI', 'DATA ANALYTICS & GEN AI'),
        ('PYTHON FULLSTACK', 'PYTHON FULLSTACK'),
        ('JAVA FULLSTACK', 'JAVA FULLSTACK'),
        ('DATA SCIENCE', 'DATA SCIENCE'),
        ('FLUTTER', 'FLUTTER'),
        ('SAP', 'SAP'),
        ('DEVOPS MASTER', 'DEVOPS MASTER'),
        ('DIPLOMA CLOUD COMPUTING', 'DIPLOMA CLOUD COMPUTING'),
        ('DIPLOMA CYBER ETHICAL', 'DIPLOMA CYBER ETHICAL'),
        ('DIPLOMA DIGITAL MARKETING', 'DIPLOMA DIGITAL MARKETING'),
        ('DIGITAL MARKETING', 'DIGITAL MARKETING'),
        ('GRAPHIC/MOTION', 'GRAPHIC/MOTION'),
        ('DIPLOMA GRAPHIC DESIGN', 'DIPLOMA GRAPHIC DESIGN'),
        ('C & C++', 'C & C++'),
        ('SELENIUM JAVA', 'SELENIUM JAVA'),
        ('PYTHON WITH AI', 'PYTHON WITH AI'),
        ('REVIT', 'REVIT'),
        ('PD CLASS', 'PD CLASS'),
        ('MERN/MEAN STACK', 'MERN/MEAN STACK'),
        ('MIS', 'MIS'),
        ('AUTOCAD/SOLIDWORKS/3DS MAX', 'AUTOCAD/SOLIDWORKS/3DS MAX'),
        ('BUSINESS ANALYTICS', 'BUSINESS ANALYTICS'),
        ('UI/UX', 'UI/UX'),
        ('WEBDESIGN', 'WEBDESIGN'),
        ('JAVA EXPERT', 'JAVA EXPERT'),
        ('ANDROID/KOTLIN', 'ANDROID/KOTLIN'),
        ('GEN AI', 'GEN AI'),
        ('CCNA', 'CCNA'),
        ('SQT & CORE JAVA', 'SQT & CORE JAVA'),
    ]
    TRAINER_CHOICES = [
        ('MR. AMAN (DATA SCIENCE)', 'MR. AMAN (DATA SCIENCE)'),
        ('MR. ABDUL (DATA ANALYTICS)', 'MR. ABDUL (DATA ANALYTICS)'),
        ('MR. PRASHANT (GRAPHIC)', 'MR. PRASHANT (GRAPHIC)'),
        ('MR. SAGAR (CLOUD)', 'MR. SAGAR (CLOUD)'),
        ('MR. RAJESH (JAVA)', 'MR. RAJESH (JAVA)'),
        ('MR. HEMANT (ETHICAL)', 'MR. HEMANT (ETHICAL)'),
        ('MRS. MAMTA (MERN)', 'MRS. MAMTA (MERN)'),
        ('MR. SOUVIK (CYBER)', 'MR. SOUVIK (CYBER)'),
        ('MRS NITI GUPTA (PD)', 'MRS NITI GUPTA (PD)'),
        ('AMAN KHAN (DIGITAL MARKETING)', 'AMAN KHAN (DIGITAL MARKETING)'),
        ('MR. RUPINDER (AUTOCAD)', 'MR. RUPINDER (AUTOCAD)'),
        ('MR. AMAN SIR (FLUTTER)', 'MR. AMAN SIR (FLUTTER)'),
        ('MR. PRATEEK (WEB-DESIGN)', 'MR. PRATEEK (WEB-DESIGN)'),
        ('MR. TARUN (MERN)', 'MR. TARUN (MERN)'),
        ('ABHISHEK UPADHYAY (DATA SCIENCE)','ABHISHEK UPADHYAY (DATA SCIENCE)'),
        ('SOURABH (JAVA )','SOURABH (JAVA )'),
        ('MR. KUNAL (CYBER SECURITY)','MR. KUNAL (CYBER SECURITY)')
    ]


    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50)
    technology = models.CharField(max_length=100, choices=TECHNOLOGY_CHOICES)
    today_topic = models.CharField(max_length=200)
    batch_time = models.CharField(max_length=20)
    trainer_name = models.CharField(max_length=100, choices=TRAINER_CHOICES)
    week_type = models.CharField(max_length=20, choices=WEEK_CHOICES)
    batch_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='Offline')
    submitted_at = models.DateTimeField(auto_now_add=True)
    semester = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=20, blank=True, null=True)
    branch = models.CharField(max_length=50, default='Vikaspuri')

    def __str__(self):
        return f"{self.name} - {self.student_id}"

@receiver(pre_delete, sender=Student)
def cleanup_student_data(sender, instance, **kwargs):
    """Automatically delete all attendance and feedback records when a student is deleted."""
    # Delete Attendance
    Attendance.objects.filter(student_id=instance.sid).delete()

    # Delete Feedback (using CharField student_id)
    from feedback.models import Feedback
    Feedback.objects.filter(student_id=instance.sid).delete()
