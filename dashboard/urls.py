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
    path('api/announcement-logs/', views.get_announcement_logs, name='get_announcement_logs'),
    # path('api/send-single-whatsapp/', views.send_single_whatsapp, name='send_single_whatsapp'),
    # path('api/send-batch-individual-whatsapp/', views.send_batch_individual_whatsapp, name='send_batch_individual_whatsapp'),
    # path('api/import-students/', views.import_students, name='import_students'),
]
