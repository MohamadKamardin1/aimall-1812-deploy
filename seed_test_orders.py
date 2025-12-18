#!/usr/bin/env python
"""
Create test orders for driver delivery app testing
"""
import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

from django.utils import timezone
from accounts.models import User, Customer
from location.models import CustomerAddress, DeliveryZone
from order.models import Order, OrderItem
from products.models import ProductVariant, MeasurementUnit
from markets.models import Market

def create_test_orders():
    """Create test orders in 'ready' status for driver to pick up"""
    
    # Get or create a customer
    customer_phone = '+255723456789'
    customer_user, _ = User.objects.get_or_create(
        phone_number=customer_phone,
        defaults={
            'user_type': 'customer',
            'is_active': True,
        }
    )
    
    customer, _ = Customer.objects.get_or_create(
        user=customer_user,
        defaults={
            'names': 'Test Customer',
            'address': '123 Test Street',
        }
    )
    
    # Get a market first
    market = Market.objects.first()
    if not market:
        print("No market found. Please seed markets first.")
        return
    
    # Get or create a delivery address
    address, _ = CustomerAddress.objects.get_or_create(
        customer=customer_user,
        market=market,
        label='Test Address',
        defaults={
            'street_address': '123 Test Street, Test City',
            'latitude': Decimal('-6.7924'),  # Dar es Salaam
            'longitude': Decimal('39.2083'),
        }
    )
    
    # Get a product variant (any one will do)
    product_variant = ProductVariant.objects.first()
    if not product_variant:
        print("No product variant found. Please seed products first.")
        return
    
    # Get a measurement unit
    measurement_unit = MeasurementUnit.objects.first()
    if not measurement_unit:
        print("No measurement unit found. Please seed measurement units first.")
        return
    
    # Create 3 test orders in 'ready' status
    for i in range(3):
        order_data = {
            'customer': customer_user,
            'delivery_address': address,
            'delivery_location_name': f'Test Location {i+1}',
            'delivery_latitude': Decimal('-6.7924') + Decimal(str(i * 0.001)),
            'delivery_longitude': Decimal('39.2083') + Decimal(str(i * 0.001)),
            'delivery_street_address': f'{123 + i*10} Test Street',
            'scheduled_delivery_date': (timezone.now() + timedelta(days=1)).date(),
            'scheduled_delivery_time': '09:00 - 12:00',
            'items_total': Decimal('50000.00'),
            'delivery_fee': Decimal('5000.00'),
            'total_amount': Decimal('55000.00'),
            'payment_method': 'cash_on_delivery',
            'is_paid': False,
            'status': 'ready',  # Ready for driver to pick up
        }
        
        order = Order.objects.create(**order_data)
        
        # Add an order item
        OrderItem.objects.create(
            order=order,
            product_variant=product_variant,
            measurement_unit=measurement_unit,
            quantity=Decimal('2'),
            unit_price=Decimal('25000.00'),
            total_price=Decimal('50000.00'),
        )
        
        print(f'✓ Created order {order.order_number} with status "ready"')
    
    print(f'\n✓ Successfully created 3 test orders!')
    print('Orders are in "ready" status and available for drivers to pick up.')

if __name__ == '__main__':
    create_test_orders()
