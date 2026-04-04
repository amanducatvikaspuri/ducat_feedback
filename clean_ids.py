import os
import django
import re

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from form.models import Attendance, Student
from feedback.models import Feedback

def clean_id(sid):
    # Extract only digits from the string
    cleaned = re.sub(r'\D', '', str(sid))
    return cleaned if cleaned else sid # Fallback to original if no digits found

def migrate_ids():
    print("Starting ID cleanup...")
    
    # 1. Clean Attendance IDs
    for record in Attendance.objects.all():
        old_id = record.student_id
        new_id = clean_id(old_id)
        if old_id != new_id:
            record.student_id = new_id
            record.save()
            print(f"Attendance: {old_id} -> {new_id}")

    # 2. Clean Feedback IDs
    for record in Feedback.objects.all():
        old_id = record.student_id
        new_id = clean_id(old_id)
        if old_id != new_id:
            record.student_id = new_id
            record.save()
            print(f"Feedback: {old_id} -> {new_id}")

    # 3. Clean Student IDs (Primary Key - tricky)
    # Since sid is a Primary Key in Student model, we must be careful.
    # We will create new records and delete the old ones.
    all_students = list(Student.objects.all())
    for student in all_students:
        old_id = student.sid
        new_id = clean_id(old_id)
        if old_id != new_id:
            # Check if the new_id already exists (to avoid PK conflict)
            if not Student.objects.filter(sid=new_id).exists():
                Student.objects.create(
                    sid=new_id,
                    name=student.name,
                    course=student.course,
                    semester=student.semester,
                    section=student.section
                )
                student.delete()
                print(f"Student PK: {old_id} -> {new_id}")
            else:
                # If new_id exists, just delete the old one or merge?
                # Usually deleting the redundant non-numeric one is safer.
                student.delete()
                print(f"Student PK: {old_id} (Merged into existing {new_id})")

    print("ID cleanup completed successfully.")

if __name__ == "__main__":
    migrate_ids()
