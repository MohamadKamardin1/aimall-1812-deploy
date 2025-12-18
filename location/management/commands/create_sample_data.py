# location/management/commands/create_sample_data.py
from django.core.management.base import BaseCommand
from location.models import DeliveryZone, CustomerAddress
from markets.models import Market, MarketZone
from accounts.models import User, Customer
from products.models import Category, ProductTemplate, ProductVariant, MeasurementUnit
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Create sample data for testing'
    
    def handle(self, *args, **options):
        self.stdout.write("Creating sample data...")
        
        # Create a test market
        market, created = Market.objects.get_or_create(
            name="Darajani Market",
            defaults={
                'description': 'Main market in Zanzibar for fresh produce',
                'location': 'Stone Town, Zanzibar',
                'latitude': -6.1659,
                'longitude': 39.2026,
                'address': 'Darajani, Stone Town, Zanzibar',
                'contact_phone': '+255777123456',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created market: {market.name}'))
        
        # Create market zones
        zones_data = [
            {'name': 'Fruits Zone', 'zone_type': 'Fruits'},
            {'name': 'Vegetables Zone', 'zone_type': 'Vegetables'},
            {'name': 'Fish Zone', 'zone_type': 'Fish'},
        ]
        
        for zone_data in zones_data:
            zone, created = MarketZone.objects.get_or_create(
                market=market,
                name=zone_data['name'],
                defaults={'zone_type': zone_data['zone_type'], 'is_active': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created market zone: {zone.name}'))
        
        # Create delivery zones if they don't exist
        delivery_zones_data = [
            {
                'name': 'Stone Town Central',
                'base_delivery_fee': Decimal('2000.00'),
                'min_latitude': -6.1700, 'max_latitude': -6.1600,
                'min_longitude': 39.1800, 'max_longitude': 39.2200,
            },
            {
                'name': 'Stone Town Outer', 
                'base_delivery_fee': Decimal('3000.00'),
                'min_latitude': -6.1800, 'max_latitude': -6.1500,
                'min_longitude': 39.1600, 'max_longitude': 39.2400,
            },
        ]
        
        for zone_data in delivery_zones_data:
            zone, created = DeliveryZone.objects.get_or_create(
                market=market,
                name=zone_data['name'],
                defaults=zone_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created delivery zone: {zone.name}'))
        
        # Create a test customer
        try:
            user, created = User.objects.get_or_create(
                phone_number='+255123456789',
                defaults={
                    'user_type': 'customer',
                    'is_verified': True,
                    'is_active': True
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                
                customer, cust_created = Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        'names': 'John Test Customer',
                        'address': 'Test Address, Stone Town'
                    }
                )
                
                if cust_created:
                    self.stdout.write(self.style.SUCCESS('Created test customer'))
        
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not create test customer: {e}'))
        
        self.stdout.write(self.style.SUCCESS('Sample data creation completed!'))