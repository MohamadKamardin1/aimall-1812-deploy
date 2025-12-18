# test_delivery_system.py
import os
import django
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

from location.models import DeliveryTimeSlot

def test_delivery_times():
    """Test that delivery time slots are set up correctly"""
    print("🔍 Testing Delivery Time Slots...")
    
    slots = DeliveryTimeSlot.objects.all()
    print(f"Found {slots.count()} delivery time slots:")
    
    for slot in slots:
        print(f"  - {slot.name}:")
        print(f"    Cut-off: {slot.cut_off_time}")
        print(f"    Delivery: {slot.delivery_start_time} - {slot.delivery_end_time}")
        print(f"    Active: {slot.is_active}")
    
    # Test delivery time calculation
    from django.utils import timezone
    from datetime import datetime
    
    now = timezone.now()
    print(f"\n🕒 Current time: {now}")
    
    for slot in slots:
        if now.time() < slot.cut_off_time:
            delivery_date = now.date()
            status = "TODAY"
        else:
            delivery_date = now.date() + timezone.timedelta(days=1)
            status = "TOMORROW"
        
        print(f"  - {slot.name}: Delivery {status} at {delivery_date}")

if __name__ == "__main__":
    test_delivery_times()