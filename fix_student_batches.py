import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from form.models import Student, Attendance
from dashboard.models import Batch, Trainer

def link_students():
    count = 0
    students = Student.objects.all()
    print(f"Checking {len(students)} students...")
    for s in students:
        # Find latest attendance for this student
        latest = Attendance.objects.filter(student_id=s.sid).order_by('-submitted_at').first()
        if latest:
            # Extract main name from attendance trainer choice (e.g. "MR. AMAN")
            trainer_name_raw = latest.trainer_name.split('(')[0].strip()
            
            # Find a batch that matches trainer name and timing
            # Search by trainer name partially
            b = Batch.objects.filter(trainer__name__icontains=trainer_name_raw, timing=latest.batch_time).first()
            
            if b:
                s.current_batch = b
                s.save()
                count += 1
                print(f"SUCCESS: Student {s.name} ({s.sid}) linked to batch: {b.trainer.name} - {b.batch_name} ({b.timing})")
            else:
                # If exact match fails, try just Timing if trainer choice doesn't match perfectly
                print(f"SKIP: No batch found for {trainer_name_raw} at {latest.batch_time}")
        else:
            print(f"SKIP: No attendance found for student {s.sid}")
    
    print(f"\nFinal: Linked {count} students out of {len(students)} total.")

if __name__ == "__main__":
    link_students()
