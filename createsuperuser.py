
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

User = get_user_model()

if not User.objects.filter(username="shubham").exists():
    User.objects.create_superuser("shubham", "admin@example.com", "admin@123")
    print("Superuser created!")
else:
    print("Superuser already exists.")
