from django.shortcuts import render, redirect
from .models import Attendance, Student
from dashboard.models import Batch, Trainer
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

@csrf_exempt
def attendance_form(request):
    branch_filter = request.GET.get('branch', 'Vikaspuri')
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
                batch_mode=mode,
                branch=request.POST.get('branch', branch_filter)
            )
            messages.success(request, f'Thank you {name}, your attendance is marked!')
            return redirect('attendance_form')
        except Exception as e:
            messages.error(request, f'Submission Error: {str(e)}')
            return redirect('attendance_form')

    # Pre-fetch all running batches grouped by trainer
    batches_data = {}
    today = timezone.localdate()
    trainers = Trainer.objects.filter(branch=branch_filter).prefetch_related('batches').all()
    for t in trainers:
        active_batches = [b for b in t.batches.all() if b.status == 'Active' and (not b.end_date or b.end_date >= today)]
        if active_batches:
            batches_data[t.name] = [{
                'id': b.id,
                'batch_name': b.batch_name,
                'batch_type': b.batch_type,
                'timing': b.timing
            } for b in active_batches]

    # Technology choices are now static globally to show all available courses
    dynamic_tech_choices = Attendance.TECHNOLOGY_CHOICES

    # Use dynamic trainer choices based on filtered trainers list
    if branch_filter == 'Vikaspuri':
        dynamic_trainer_choices = Attendance.TRAINER_CHOICES
    else:
        dynamic_trainer_choices = []
        for t in trainers:
            label = f"{t.name} ({t.course})" if t.course and t.course.upper() not in t.name.upper() else t.name
            dynamic_trainer_choices.append((label, label))

    context = {
        'technology_choices': dynamic_tech_choices,
        'trainer_choices': dynamic_trainer_choices,
        'trainer_batches_json': json.dumps(batches_data),
        'active_branch': branch_filter
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
            branch = request.POST.get('branch')

            if not all([name, sid, phone, email, course, branch]):
                messages.error(request, "All fields are required!")
                return redirect('student_registration')

            Student.objects.update_or_create(
                sid=sid,
                defaults={
                    'name': name,
                    'phone_number': phone,
                    'email': email,
                    'course': course,
                    'branch': branch
                }
            )
            messages.success(request, f"Welcome {name}! Registration Successful.")
            return redirect('student_registration')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('student_registration')

    branch_query = request.GET.get('branch', 'Vikaspuri')

    # Use static technology choices globally
    dynamic_tech_choices = Attendance.TECHNOLOGY_CHOICES

    context = {
        'technology_choices': dynamic_tech_choices,
        'active_branch': branch_query
    }
    return render(request, 'form/register.html', context)
