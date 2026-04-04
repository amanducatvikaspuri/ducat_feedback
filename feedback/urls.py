from django.urls import path
from . import views

urlpatterns = [
    path('', views.feedback_form, name='feedback_form'),
    path('get-student/', views.get_student_details, name='get_student_details'),
    path('<str:phase>/', views.feedback_form, name='feedback_phase'),
]
