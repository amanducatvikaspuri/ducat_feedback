from django.db import models
from django.utils import timezone

class Trainer(models.Model):
    BRANCH_CHOICES = [
        ('Vikaspuri', 'Vikaspuri'),
        ('Pitampura', 'Pitampura'),
        ('South Ex', 'South Ex'),
        ('Noida', 'Noida'),
        ('Gurgaon', 'Gurgaon'),
        ('Ghaziabad', 'Ghaziabad'),
    ]
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    branch = models.CharField(max_length=50, choices=BRANCH_CHOICES, default='Vikaspuri')

    def __str__(self):
        return self.name

class Batch(models.Model):
    BATCH_TYPES = [
        ('Weekdays', 'Weekdays'),
        ('Weekend', 'Weekend'),
    ]
    BATCH_NAMES = [
        ('3DS MAX', '3DS MAX'),
        ('ADVANCE JAVA', 'ADVANCE JAVA'),
        ('ANDROID', 'ANDROID'),
        ('ANGULAR', 'ANGULAR'),
        ('ANIMATION', 'ANIMATION'),
        ('AUTOCAD', 'AUTOCAD'),
        ('AWS', 'AWS'),
        ('AZURE', 'AZURE'),
        ('C & C++', 'C & C++'),
        ('CCNA', 'CCNA'),
        ('CCNP', 'CCNP'),
        ('CLOUD COMPUTING', 'CLOUD COMPUTING'),
        ('CORE JAVA', 'CORE JAVA'),
        ('COREL DRAW', 'COREL DRAW'),
        ('CYBER ETHICAL', 'CYBER ETHICAL'),
        ('CYBER SECURITY', 'CYBER SECURITY'),
        ('DATA ANALYTICS', 'DATA ANALYTICS'),
        ('DATA SCIENCE', 'DATA SCIENCE'),
        ('DEEP LEARNING', 'DEEP LEARNING'),
        ('DEVOPS', 'DEVOPS'),
        ('DIGITAL MARKETING', 'DIGITAL MARKETING'),
        ('EXCEL', 'EXCEL'),
        ('EXPRESS', 'EXPRESS'),
        ('FIGMA', 'FIGMA'),
        ('FLUTTER', 'FLUTTER'),
        ('GEN AI', 'GEN AI'),
        ('ILLUSTRATOR', 'ILLUSTRATOR'),
        ('JAVA', 'JAVA'),
        ('LINUX', 'LINUX'),
        ('MACHINE LEARNING', 'MACHINE LEARNING'),
        ('MANUAL TESTING', 'MANUAL TESTING'),
        ('MCSA', 'MCSA'),
        ('MERN/MEAN STACK', 'MERN/MEAN STACK'),
        ('MONGODB', 'MONGODB'),
        ('NLP', 'NLP'),
        ('NODE JS', 'NODE JS'),
        ('PHOTOSHOP', 'PHOTOSHOP'),
        ('POWER BI', 'POWER BI'),
        ('PYTHON', 'PYTHON'),
        ('QA FULL STACK', 'QA FULL STACK'),
        ('REACT JS', 'REACT JS'),
        ('REACT NATIVE', 'REACT NATIVE'),
        ('REVIT', 'REVIT'),
        ('SALES FORCE', 'SALES FORCE'),
        ('SELENIUM AUTOMATION', 'SELENIUM AUTOMATION'),
        ('SEO', 'SEO'),
        ('SOLID WORKS', 'SOLID WORKS'),
        ('SQL', 'SQL'),
        ('STATIC', 'STATIC'),
        ('TABLEAU', 'TABLEAU'),
        ('VIDEO EDITING', 'VIDEO EDITING'),
        ('WEB DESIGN', 'WEB DESIGN'),
        ('OTHERS', 'OTHERS'),
    ]
    trainer = models.ForeignKey(Trainer, related_name='batches', on_delete=models.PROTECT)
    batch_name = models.CharField(max_length=100)
    batch_type = models.CharField(max_length=20, choices=BATCH_TYPES)
    students_count = models.IntegerField(default=0)
    timing = models.CharField(max_length=100)
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=4)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Closed', 'Closed')], default='Active')
    email_sent = models.BooleanField(default=False)
    class Meta:
        verbose_name_plural = "Batches"

    def __str__(self):
        return f"{self.trainer.name} - {self.batch_name} ({self.batch_type})"

class DailyAttendance(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='daily_attendances')
    student_sid = models.CharField(max_length=50) # Storing SID for easier lookup
    student_name = models.CharField(max_length=100)
    date = models.DateField(default=timezone.now)
    is_present = models.BooleanField(default=True)

    class Meta:
        unique_together = ('batch', 'student_sid', 'date')

    def __str__(self):
        return f"{self.student_name} - {self.date} ({'P' if self.is_present else 'A'})"
