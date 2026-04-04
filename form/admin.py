from django.contrib import admin
from .models import Attendance, Student, WhatsAppMessageLog

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'student_id', 'technology', 'trainer_name', 'submitted_at')
    list_filter = ('technology', 'trainer_name', 'week_type', 'submitted_at')
    search_fields = ('name', 'student_id', 'today_topic')
    readonly_fields = ('submitted_at',)
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('sid', 'name', 'phone_number', 'email', 'current_batch')
    search_fields = ('sid', 'name', 'phone_number')
    list_filter = ('current_batch',)
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)

@admin.register(WhatsAppMessageLog)
class WhatsAppMessageLogAdmin(admin.ModelAdmin):
    list_display = ('sent_at', 'student', 'batch', 'status')
    list_filter = ('status', 'batch', 'sent_at')
    search_fields = ('student__name', 'message_body')
    readonly_fields = ('sent_at',)
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)
