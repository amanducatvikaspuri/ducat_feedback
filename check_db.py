import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from form.models import Student

def check_db():
    print("Checking 'Student' model fields...")
    fields = [f.name for f in Student._meta.fields]
    print(f"Fields in Model: {fields}")
    
    with connection.cursor() as cursor:
        print("\nChecking migrations table for 'form'...")
        cursor.execute("SELECT name FROM django_migrations WHERE app='form'")
        applied = [row[0] for row in cursor.fetchall()]
        print(f"Applied Migrations: {applied}")
        
        print("\nChecking actual DB columns for 'form_student'...")
        cursor.execute("PRAGMA table_info(form_student)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Columns in DB: {columns}")

if __name__ == "__main__":
    check_db()
