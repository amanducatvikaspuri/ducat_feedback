from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'student_id', 'trainer_name', 'phase', 'technology', 'batch_mode', 'ques1_rating', 'ques2_rating', 'ques3_rating', 'ques4_rating', 'submitted_at')
    list_filter = ('phase', 'trainer_name', 'technology', 'batch_mode', 'submitted_at')
    search_fields = ('student_name', 'student_id', 'trainer_name')
    readonly_fields = ('submitted_at',)
