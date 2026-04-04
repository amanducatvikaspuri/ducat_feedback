from django.urls import path
from . import views

urlpatterns = [
    path('', views.attendance_form, name='attendance_form'),
    path('register/', views.student_registration, name='student_registration'),
]
