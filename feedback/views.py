from django.shortcuts import render, redirect
from django.http import JsonResponse
from form.models import Student, Attendance
from django.contrib import messages
from dashboard.models import Trainer
from .models import Feedback

def feedback_form(request, phase=None):
    trainers = Trainer.objects.all().order_by('name')
    
    # Phase normalization
    phase_map = {
        'phase-1': 'P-1', 'phase-2': 'P-2', 'phase-3': 'P-3',
        'phase-4': 'P-4', 'phase-5': 'P-5'
    }
    
    # If no phase is provided (bare link), DEFAULT TO P-1
    if not phase:
        mapped_phase = 'P-1'
    else:
        mapped_phase = phase_map.get(phase, phase)
    
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_id')
            student_name = request.POST.get('student_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            branch = request.POST.get('branch', 'Vikaspuri')
            trainer_name = request.POST.get('trainer_name')
            technology = request.POST.get('technology')
            
            # Legacy handling for old templates if any
            hour = request.POST.get('hour')
            batch_timing = request.POST.get('batch_timing', '00:00 AM')
            batch_mode = request.POST.get('batch_mode', 'Offline')
            batch_type = request.POST.get('batch_type', 'Weekdays')
            
            form_phase = mapped_phase if mapped_phase else request.POST.get('phase', 'P-1')
            
            # Check for duplicate
            if Feedback.objects.filter(student_id=student_id, phase=form_phase, trainer_name=trainer_name).exists():
                 messages.error(request, f'You have already submitted {form_phase} feedback for {trainer_name}!')
                 if phase: return redirect('feedback_phase', phase=phase)
                 return redirect('feedback_form')

            q1 = int(request.POST.get('ques1_rating', 5))
            q2 = int(request.POST.get('ques2_rating', 5))
            q3 = int(request.POST.get('ques3_rating', 5))
            q4 = int(request.POST.get('ques4_rating', 5))
            
            review_desc = request.POST.get('review_description', '')
            
            # Normalize and Clean data for Dashboard Matching
            def clean_str(s): return str(s or '').strip().upper()
            
            f_trainer = clean_str(trainer_name)
            f_tech = clean_str(technology)
            f_timing = clean_str(batch_timing)
            # Remove " Batch" suffix if present in type (e.g. "Weekdays Batch" -> "WEEKDAYS")
            f_type = clean_str(batch_type).replace(' BATCH', '')
            f_phase = clean_str(form_phase)

            Feedback.objects.create(
                student_id=student_id, student_name=student_name, email=email, phone=phone,
                branch=branch, trainer_name=f_trainer, technology=f_tech,
                batch_timing=f_timing, batch_mode=batch_mode, batch_type=f_type,
                phase=f_phase, ques1_rating=q1, ques2_rating=q2, ques3_rating=q3,
                ques4_rating=q4, review_description=review_desc
            )
            messages.success(request, 'Success! Feedback submitted.')
            if phase: return redirect('feedback_phase', phase=phase)
            return redirect('feedback_form')
        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, 'Please fill all fields correctly.')

    # Labels for UI
    phase_labels = {
        'P-1': 'P-1 (Orientation & Basics)',
        'P-2': 'P-2 (Core Implementation)',
        'P-3': 'P-3 (Mid-Project Assessment)',
        'P-4': 'P-4 (Advanced Concepts)',
        'P-5': 'P-5 (Final Submission/Project)'
    }
    phase_label = phase_labels.get(mapped_phase, 'P-1 (Orientation & Basics)')
    
    # Pre-fetch all batches grouped by technology for dynamic frontend selection
    from dashboard.models import Batch
    import json
    
    # 1. Fetch ALL active batches
    batches = Batch.objects.select_related('trainer').all()
    
    # 2. Derive technology choices from BOTH the static list and actual Batch records
    # Normalize to Uppercase for consistent matching
    batch_techs = set(b.batch_name.upper() for b in batches if b.batch_name)
    static_techs = set(tech.upper() for tech in dict(Attendance.TECHNOLOGY_CHOICES).keys())
    
    # Merge and sort
    all_techs = sorted(list(batch_techs | static_techs))
    dynamic_tech_choices = [(tech, tech) for tech in all_techs]
    
    # 3. Group batches by their technology (normalized to uppercase)
    # Mapping by BOTH Batch Name AND Trainer Course to ensure "DATA SCIENCE" finds Python/ML batches
    batch_data = {}
    for b in batches:
        tech_keys = set()
        if b.batch_name: tech_keys.add(b.batch_name.upper())
        if b.trainer and b.trainer.course: tech_keys.add(b.trainer.course.upper())
        
        for tech in tech_keys:
            if tech not in batch_data:
                batch_data[tech] = []
            
            # Avoid duplicate batch entries under same tech
            batch_data[tech].append({
                'id': b.id,
                'trainer': b.trainer.name,
                'timing': b.timing,
                'type': b.batch_type
            })

    context = {
        'trainers': trainers,
        'technology_choices': dynamic_tech_choices,  # Using dynamic list now
        'selected_phase': mapped_phase,
        'phase_label': phase_label,
        'batch_data_json': json.dumps(batch_data),
    }
    
    # Template selection mapping
    template_map = {
        'P-1': 'feedback/form_p1.html',
        'P-2': 'feedback/form_p2.html',
        'P-3': 'feedback/form_p3.html',
        'P-4': 'feedback/form_p4.html',
        'P-5': 'feedback/form.html', # Default for P-5
    }
    template = template_map.get(mapped_phase, 'feedback/form.html')
    return render(request, template, context)

def get_student_details(request):
    sid = request.GET.get('sid', '').strip()
    if sid:
        try:
            student = Student.objects.filter(sid=sid).first()
            if not student: student = Student.objects.filter(sid__icontains=sid).first()
            
            trainer = request.GET.get('trainer', '')
            phase = request.GET.get('phase', '')
            
            existing_fb = None
            if student and trainer and phase:
                existing_fb = Feedback.objects.filter(student_id=student.sid, trainer_name=trainer, phase=phase).first()
            
            if student:
                data = {
                    'status': 'success',
                    'name': student.name,
                    'course': student.course.upper() if student.course else '',
                    'email': getattr(student, 'email', '') or '',
                    'phone': getattr(student, 'phone_number', '') or '',
                    'semester': getattr(student, 'semester', '') or '',
                    'section': getattr(student, 'section', '') or '',
                    'already_submitted': existing_fb is not None
                }
                
                # Add Batch Info if available
                if student.current_batch:
                    data.update({
                        'trainer_name': student.current_batch.trainer.name,
                        'batch_type': student.current_batch.batch_type,
                        'batch_timing': student.current_batch.timing
                    })
                
                if existing_fb:
                    data.update({
                        'q1': existing_fb.ques1_rating,
                        'q2': existing_fb.ques2_rating,
                        'q3': existing_fb.ques3_rating,
                        'q4': existing_fb.ques4_rating,
                        'review': existing_fb.review_description or ''
                    })
                
                return JsonResponse(data)
        except Exception as e:
            print(f"Fetch Error: {e}")
    return JsonResponse({'status': 'not_found'})
