from django.db import models

class Feedback(models.Model):
    PHASE_CHOICES = [
        ('P-1', 'Phase 1: Orientation & Basics'),
        ('P-2', 'Phase 2: Core Implementation'),
        ('P-3', 'Phase 3: Mid-Project Assessment'),
        ('P-4', 'Phase 4: Advanced Concepts'),
        ('P-5', 'Phase 5: Final Submission/Project'),
    ]

    # Student Info
    student_id = models.CharField(max_length=50)
    student_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    branch = models.CharField(max_length=100, default="Vikaspuri")
    
    # Course Info
    trainer_name = models.CharField(max_length=255)
    technology = models.CharField(max_length=255)
    batch_timing = models.CharField(max_length=100) # Combined Hr:Min AM/PM
    batch_mode = models.CharField(max_length=20, default="Offline")
    batch_type = models.CharField(max_length=20, default="Weekdays") # Weekdays/Weekend
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default="P-1")
    
    # Ratings (1-5 stars)
    ques1_rating = models.IntegerField(default=5) # Understand topics
    ques2_rating = models.IntegerField(default=5) # Regularity/Punctuality
    ques3_rating = models.IntegerField(default=5) # Practical work
    ques4_rating = models.IntegerField(default=5) # Doubt clearing
    
    # Review
    review_description = models.TextField(blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review from {self.student_name} for {self.trainer_name} ({self.get_phase_display()})"
