import os
import django
import random
from datetime import datetime, timedelta, time
from django.utils import timezone

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import Trainer, Batch
from form.models import Attendance
from feedback.models import Feedback

def seed_data():
    print("--- Starting Advanced Data Seeding ---")

    trainers_config = [
        {"name": "MR. AMAN (DATA SCIENCE)", "course": "DATA SCIENCE", "batches": [
            {"type": "Weekdays", "timing": "10:00:00", "students": 15},
            {"type": "Weekend", "timing": "14:00:00", "students": 10}
        ]},
        {"name": "MR. ABDUL (DATA ANALYTICS)", "course": "DATA ANALYTICS & AI", "batches": [
            {"type": "Weekdays", "timing": "16:00:00", "students": 20}
        ]},
        {"name": "MR. PRASHANT (GRAPHIC)", "course": "GRAPHIC/MOTION", "batches": [
            {"type": "Weekdays", "timing": "12:00:00", "students": 12}
        ]},
        {"name": "MR. SAGAR (CLOUD)", "course": "DIPLOMA CLOUD COMPUTING", "batches": [
            {"type": "Weekdays", "timing": "08:00:00", "students": 18}
        ]}
    ]

    # Spread over 2024, 2025, and 2026
    years = [2024, 2025, 2026]
    months = list(range(1, 13))

    topics = ["Python Basics", "Deep Learning", "SQL Mastery", "Deployment", "React Hooks"]
    names = ["Amit Sharma", "Vikram Singh", "Priya Malhotra", "Rahul Jain", "Riya Singh", "Sameer Sharma", "Amit Mehta"]

    for t_conf in trainers_config:
        trainer_obj, _ = Trainer.objects.get_or_create(name=t_conf["name"], defaults={"course": t_conf["course"]})
        
        for b_conf in t_conf["batches"]:
            Batch.objects.get_or_create(
                trainer=trainer_obj, 
                batch_type=b_conf["type"],
                defaults={"timing": b_conf["timing"], "students_count": b_conf["students"]}
            )

            for i in range(b_conf["students"]):
                student_id = str(random.randint(1000, 9999))
                student_name = f"{random.choice(names)} {random.randint(1, 100)}"
                
                # Random year/month/day
                y = random.choice(years)
                m = random.choice(months)
                d = random.randint(1, 28)
                
                final_date = timezone.make_aware(datetime(y, m, d, random.randint(9, 18), random.randint(0, 59)))
                mode = random.choice(["Online", "Offline"])
                b_time = datetime.strptime(b_conf["timing"], "%H:%M:%S").time()

                # Create Attendance with Manual Date
                att = Attendance.objects.create(
                    name=student_name,
                    student_id=student_id,
                    technology=t_conf["course"],
                    today_topic=random.choice(topics),
                    batch_time=b_time,
                    trainer_name=t_conf["name"],
                    week_type=b_conf["type"],
                    batch_mode=mode
                )
                att.submitted_at = final_date
                att.save()

                # Feedback Sessions (P-1, P-2, etc)
                for phase in ["P-1", "P-2", "P-3"]:
                    if random.random() > 0.4:
                        q1 = random.randint(3, 5)
                        q2 = random.randint(3, 5)
                        q3 = random.randint(2, 5)
                        q4 = random.randint(4, 5)
                        
                        feed_date = final_date + timedelta(days=random.randint(2, 30))
                        # Limit feed_date to not exceed future too much
                        if feed_date > timezone.now() + timedelta(days=365):
                             feed_date = timezone.now()

                        feed = Feedback.objects.create(
                            student_id=student_id,
                            student_name=student_name,
                            email=f"student{student_id}@example.com",
                            phone="9876543210",
                            trainer_name=t_conf["name"],
                            technology=t_conf["course"],
                            batch_timing=b_conf["timing"],
                            batch_mode=mode,
                            batch_type=b_conf["type"],
                            phase=phase,
                            ques1_rating=q1,
                            ques2_rating=q2,
                            ques3_rating=q3,
                            ques4_rating=q4,
                            review_description="Excellent session." if q1 > 3 else "Normal session."
                        )
                        feed.submitted_at = feed_date
                        feed.save()

    print("--- FULL SEEDING COMPLETE: 2024, 2025, and 2026 data populated ---")

if __name__ == "__main__":
    seed_data()
