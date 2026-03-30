from django.test import TestCase
from django.utils import timezone
from datetime import datetime

# Create your tests here.
class MonthlyResetTestCase(TestCase):
    def test_monthly_reset(self):
        # This test would ideally create some materials, run the reset command, and check the results.
        # For now, we will just print the current date to verify our timezone override.
        now = timezone.datetime(2026, 3, 30)
        print(f"Current date for testing: {now}")