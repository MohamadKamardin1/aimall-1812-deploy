# test_complete_system.py
import os
import django
import requests
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_all_endpoints():
    """Test all location and orders endpoints"""
    print("🚀 Testing Complete Delivery & Order System...")
    
    # Test 1: Delivery Time Slots
    print("\n1. 📅 Testing Delivery Time Slots...")
    try:
        response = requests.get(f"{BASE_URL}/location/time-slots/")
        if response.status_code == 200:
            slots = response.json()
            print(f"✅ Found {len(slots)} delivery time slots")
            for slot in slots:
                print(f"   - {slot['name']}: Cut-off {slot['cut_off_time']}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Delivery Time Calculation
    print("\n2. 🕒 Testing Delivery Time Calculation...")
    try:
        response = requests.get(f"{BASE_URL}/location/calculate-delivery-time/")
        if response.status_code == 200:
            data = response.json()
            current_time = data['current_time']
            print(f"✅ Current server time: {current_time}")
            print("Available delivery slots:")
            for slot in data['available_slots']:
                slot_info = slot['slot']
                print(f"   - {slot_info['name']}: {slot['delivery_date']} ({slot['delivery_time_range']})")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Markets with Delivery Info
    print("\n3. 🏪 Testing Markets with Delivery Info...")
    try:
        response = requests.get(f"{BASE_URL}/location/markets/")
        if response.status_code == 200:
            markets = response.json()
            print(f"✅ Found {len(markets)} markets")
            for market in markets:
                print(f"   - {market['name']}: {market['location']}")
                if 'delivery_zones' in market and market['delivery_zones']:
                    print(f"     Delivery zones: {len(market['delivery_zones'])}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Delivery Fee Calculation
    print("\n4. 💰 Testing Delivery Fee Calculation...")
    try:
        # Using Darajani Market coordinates and a nearby location
        test_data = {
            'market_id': 'your_market_id_here',  # You'll need to get this from the markets endpoint
            'latitude': -6.1600,
            'longitude': 39.1900
        }
        response = requests.post(f"{BASE_URL}/location/calculate-fee/", json=test_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Delivery fee: {data['delivery_fee']} {data['currency']}")
            print(f"   Market: {data['market']}")
        else:
            print(f"❌ Failed: {response.status_code} - This is normal if no markets exist yet")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n🎉 System test completed!")

def test_delivery_logic():
    """Test the delivery time logic"""
    print("\n🧠 Testing Delivery Logic...")
    
    from django.utils import timezone
    from datetime import time
    from location.models import DeliveryTimeSlot
    
    # Test different times
    test_times = [
        time(9, 0),   # 9:00 AM - Before morning cut-off
        time(10, 30), # 10:30 AM - After morning cut-off, before afternoon
        time(15, 0),  # 3:00 PM - After afternoon cut-off
    ]
    
    for test_time in test_times:
        print(f"\nTesting at {test_time}:")
        
        # Mock current time
        now = timezone.now()
        test_datetime = datetime.combine(now.date(), test_time)
        test_datetime = timezone.make_aware(test_datetime)
        
        slots = DeliveryTimeSlot.objects.filter(is_active=True).order_by('cut_off_time')
        
        for slot in slots:
            if test_time < slot.cut_off_time:
                delivery_date = now.date()
                status = "TODAY"
            else:
                delivery_date = now.date() + timezone.timedelta(days=1)
                status = "TOMORROW"
            
            print(f"  - {slot.name}: Delivery {status} on {delivery_date}")

if __name__ == "__main__":
    test_all_endpoints()
    test_delivery_logic()