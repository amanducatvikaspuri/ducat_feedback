import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from feedback.models import Feedback
from dashboard.models import Batch

def fix_feedbacks():
    print("Starting Feedback Data Fix...")
    # Find all feedbacks with default/missing timing
    broken_feedbacks = Feedback.objects.filter(batch_timing__in=['00:00 AM', '00:00AM', '', None])
    print(f"Found {broken_feedbacks.count()} broken feedback records.")
    
    fixed_count = 0
    for fb in broken_feedbacks:
        # Try to find a valid batch for this trainer
        first_batch = Batch.objects.filter(trainer__name__iexact=fb.trainer_name).first()
        if first_batch:
            fb.batch_timing = first_batch.timing.upper()
            fb.batch_type = first_batch.batch_type.upper()
            fb.save()
            fixed_count += 1
            print(f"Fixed: Student {fb.student_name} reassigned to {fb.batch_timing} ({fb.batch_type})")
        else:
            print(f"Skipped: No active batch found for trainer {fb.trainer_name}")

    print(f"Update Complete. {fixed_count} records fixed.")

if __name__ == "__main__":
    fix_feedbacks()
