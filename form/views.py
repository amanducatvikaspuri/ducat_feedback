from django.shortcuts import render, redirect
from .models import Attendance, Student
from dashboard.models import Batch, Trainer
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

@csrf_exempt
def attendance_form(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            sid = request.POST.get('student_id')
            tech = request.POST.get('technology')
            topic = request.POST.get('today_topic')
            time = request.POST.get('batch_time')
            trainer = request.POST.get('trainer_name')
            week = request.POST.get('week_type')
            mode = request.POST.get('batch_mode')
            
            if not all([name, sid, tech, topic, trainer, week, mode]):
                 messages.error(request, "Please fill all required fields.")
                 return redirect('attendance_form')

            # Create or Update Student record for later auto-fill
            Student.objects.update_or_create(
                sid=sid,
                defaults={
                    'name': name,
                    'course': tech
                }
            )


            time_val = time if time else "00:00"
            today = timezone.localdate()

            # Check if attendance already exists for today in this very batch
            if Attendance.objects.filter(
                student_id=sid,
                trainer_name=trainer,
                batch_time=time_val,
                week_type=week,
                submitted_at__date=today
            ).exists():
                messages.error(request, f"Hi {name}, you have already submitted attendance for this batch today!")
                return redirect('attendance_form')

            Attendance.objects.create(
                name=name,
                student_id=sid,
                technology=tech,
                today_topic=topic,
                batch_time=time_val,
                trainer_name=trainer,
                week_type=week,
                batch_mode=mode
            )
            messages.success(request, f'Thank you {name}, your attendance is marked!')
            return redirect('attendance_form')
        except Exception as e:
            messages.error(request, f'Submission Error: {str(e)}')
            return redirect('attendance_form')
            
    # Pre-fetch all running batches grouped by trainer
    batches_data = {}
    trainers = Trainer.objects.prefetch_related('batches').all()
    for t in trainers:
        batches_data[t.name] = [{
            'id': b.id,
            'batch_name': b.batch_name,
            'batch_type': b.batch_type,
            'timing': b.timing
        } for b in t.batches.all()]

    # Fetch unique technologies from active batches + static choices
    # Normalizing to uppercase for consistency
    batch_techs = set(b.batch_name.upper() for b in Batch.objects.all() if b.batch_name)
    static_techs = set(tech.upper() for tech in dict(Attendance.TECHNOLOGY_CHOICES).keys())
    all_techs = sorted(list(batch_techs | static_techs))
    dynamic_tech_choices = [(tech, tech) for tech in all_techs if tech]

    context = {
        'technology_choices': dynamic_tech_choices, # Dynamic + Static merged
        'trainer_choices': Attendance.TRAINER_CHOICES,
        'trainer_batches_json': json.dumps(batches_data)
    }
    return render(request, 'form/form.html', context)
@csrf_exempt
def student_registration(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            sid = request.POST.get('student_id')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            course = request.POST.get('course')
            
            if not all([name, sid, phone, email, course]):
                messages.error(request, "All fields are required!")
                return redirect('student_registration')
                
            Student.objects.update_or_create(
                sid=sid,
                defaults={
                    'name': name,
                    'phone_number': phone,
                    'email': email,
                    'course': course
                }
            )
            messages.success(request, f"Welcome {name}! Registration Successful.")
            return redirect('student_registration')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('student_registration')
            
    # Fetch unique technologies from active batches + static choices
    # Normalizing to uppercase for consistency
    batch_techs = set(b.batch_name.upper() for b in Batch.objects.all() if b.batch_name)
    static_techs = set(tech.upper() for tech in dict(Attendance.TECHNOLOGY_CHOICES).keys())
    all_techs = sorted(list(batch_techs | static_techs))
    dynamic_tech_choices = [(tech, tech) for tech in all_techs if tech]

    context = {
        'technology_choices': dynamic_tech_choices
    }
    return render(request, 'form/register.html', context)
