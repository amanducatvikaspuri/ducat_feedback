from django.db import models

class Trainer(models.Model):
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Batch(models.Model):
    BATCH_TYPES = [
        ('Weekdays', 'Weekdays'),
        ('Weekend', 'Weekend'),
    ]
    BATCH_NAMES = [
        ('PYTHON', 'PYTHON'),
        ('POWER BI', 'POWER BI'),
        ('EXCEL', 'EXCEL'),
        ('SQL', 'SQL'),
        ('TABLEAU', 'TABLEAU'),
        ('MACHINE LEARNING', 'MACHINE LEARNING'),
        ('NLP', 'NLP'),
        ('GEN AI', 'GEN AI'),
        ('CORE JAVA', 'CORE JAVA'),
        ('ADVANCED JAVA', 'ADVANCED JAVA'),
        ('REACT JS', 'REACT JS'),
        ('NODE JS', 'NODE JS'),
        ('MONGODB', 'MONGODB'),
        ('DATA SCIENCE', 'DATA SCIENCE'),
        ('MERN/MEAN STACK', 'MERN/MEAN STACK'),
        ('CLOUD COMPUTING', 'CLOUD COMPUTING'),
        ('DATA ANALYTICS', 'DATA ANALYTICS'),
        ('OTHERS', 'OTHERS'),
    ]
    trainer = models.ForeignKey(Trainer, related_name='batches', on_delete=models.CASCADE)
    batch_name = models.CharField(max_length=100, choices=BATCH_NAMES, default='OTHERS')
    batch_type = models.CharField(max_length=20, choices=BATCH_TYPES)
    students_count = models.IntegerField(default=0)
    timing = models.CharField(max_length=100)
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=4)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.trainer.name} - {self.batch_name} ({self.batch_type})"
