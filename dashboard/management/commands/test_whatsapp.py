from django.core.management.base import BaseCommand
import requests
from django.conf import settings
from datetime import datetime

class Command(BaseCommand):
    help = 'Test WATI WhatsApp Integration with a single number'

    def add_arguments(self, parser):
        parser.add_argument('--phone', type=str, help='10 or 12 digit phone number with country code (e.g. 919999999999)')

    def handle(self, *args, **options):
        phone = options['phone']
        if not phone:
            self.stdout.write(self.style.ERROR('Please provide a phone number using --phone 91XXXXXXXXXX'))
            return

        base_url = getattr(settings, 'WATI_BASE_URL', '').rstrip('/')
        api_token = getattr(settings, 'WATI_API_TOKEN', '')

        if not base_url or not api_token:
            self.stdout.write(self.style.ERROR('WATI credentials missing in settings.py'))
            return

        # Ensure country code for India
        if len(phone) == 10:
            phone = "91" + phone

        self.stdout.write(f"Attempting to send test message to {phone}...")
        
        api_endpoint = f"{base_url}/api/v1/sendSessionMessage/{phone}"
        headers = {
            "Authorization": api_token,
            "Content-Type": "application/json"
        }
        
        msg = f"Hello from Ducat Vikaspuri! This is a test message sent at {datetime.now().strftime('%H:%M:%S')}."
        payload = {"messageText": msg}

        try:
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200 and data.get('result') == 'success':
                self.stdout.write(self.style.SUCCESS(f"HUZZAH! Message sent successfully. WATI Response: {data}"))
            else:
                self.stdout.write(self.style.ERROR(f"FAILED! Status: {response.status_code}, Response: {data}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"NETWORK ERROR: {str(e)}"))
