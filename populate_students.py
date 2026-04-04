import os
import django
import random
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from form.models import Student, Attendance
from dashboard.models import Batch, Trainer

def populate_students_distribute():
    print("Redistributing 150 students into current batches...")
    
    # Get all existing batches
    db_batches = list(Batch.objects.all())
    if not db_batches:
        print("Error: No batches found in database! Please create batches first.")
        return

    students = list(Student.objects.all())
    if not students:
        print("No students found to redistribute.")
        return

    print(f"Distributing {len(students)} students across {len(db_batches)} batches...")
    
    for s in students:
        # Try to find a batch that matches the student's course category if possible
        # Simple mapping logic
        matching_batches = [b for b in db_batches if b.batch_name.split('-')[0].strip().upper() in s.course.upper() or s.course.upper() in b.batch_name.upper()]
        
        if matching_batches:
            s.current_batch = random.choice(matching_batches)
        else:
            # Fallback to any random batch if no direct course match
            s.current_batch = random.choice(db_batches)
            
        s.save()

    print("Success! All students have been assigned to appropriate current batches.")

if __name__ == '__main__':
    populate_students_distribute()
