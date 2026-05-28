from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('export/csv/', views.export_attendance_csv, name='export_csv'),
    path('export/excel/', views.export_attendance_excel, name='export_excel'),
    path('export/feedback/csv/', views.export_feedback_csv, name='export_feedback_csv'),
    path('export/feedback/excel/', views.export_feedback_excel, name='export_feedback_excel'),
    path('export/feedback/pdf/', views.export_feedback_pdf, name='export_feedback_pdf'),
    path('export/feedback/sheets/', views.export_feedback_sheets, name='export_feedback_sheets'),
    # path('google-sync/', views.sync_to_google_sheets, name='google_sync'),
    # path('api/send-bulk-whatsapp/', views.send_bulk_whatsapp, name='send_bulk_whatsapp'),
    # path('api/announcement-logs/', views.get_announcement_logs, name='get_announcement_logs'),
    # path('api/send-single-whatsapp/', views.send_single_whatsapp, name='send_single_whatsapp'),
    # path('api/send-batch-individual-whatsapp/', views.send_batch_individual_whatsapp, name='send_batch_individual_whatsapp'),
    path('api/import-students/', views.import_students, name='import_students'),
    path('api/daily-attendance/mark/', views.mark_daily_attendance, name='mark_daily_attendance'),
    path('api/daily-attendance/history/', views.get_daily_attendance_history, name='get_daily_attendance_history'),
    path('api/student-attendance-calendar/', views.get_student_attendance_calendar, name='get_student_attendance_calendar'),
    path('api/send-batch-notification/', views.send_batch_notification, name='send_batch_notification'),
    path('api/batch/delete/<int:batch_id>/', views.delete_batch, name='delete_batch'),
    path('api/trend-details/', views.get_trend_details, name='get_trend_details'),
    path('api/student-profile/', views.get_student_profile, name='get_student_profile'),
    path('export/timetable/csv/', views.export_timetable_csv, name='export_timetable_csv'),
    path('export/timetable/excel/', views.export_timetable_excel, name='export_timetable_excel'),
    path('export/roster/csv/', views.export_student_roster_csv, name='export_roster_csv'),
    path('export/roster/excel/', views.export_student_roster_excel, name='export_roster_excel'),
]
