import os
import django
import sys
from django.db import transaction
from django.utils import timezone
from datetime import date
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

from accounts.models import (
    User, Customer, Vendor, Driver, AdminProfile, 
    SecurityQuestion, UserSecurityAnswer
)
from products.models import (
    GlobalSetting, Category, MeasurementUnitType, MeasurementUnit,
    ProductTemplate, ProductVariant, UnitPrice, ProductAddon, 
    ProductAddonMapping, ProductImage
)
from markets.models import Market, MarketZone
from location.models import DeliveryFeeConfig
import uuid

class SeedData:
    def __init__(self):
        self.users = {}
        self.markets = {}
        self.market_zones = {}
        self.categories = {}
        self.unit_types = {}
        self.units = {}
        self.product_templates = {}
        self.addons = {}

    def log(self, message, is_error=False):
        """Enhanced logging"""
        prefix = "❌" if is_error else "✓"
        print(f"{prefix} {message}")
        if is_error:
            import traceback
            traceback.print_exc()

    def create_security_questions(self):
        """Create security questions for password recovery"""
        try:
            questions = [
                "What was the name of your first pet?",
                "What city were you born in?",
                "What is your mother's maiden name?",
                "What was the name of your elementary school?",
                "What is your favorite book?",
            ]
            
            for question_text in questions:
                question, created = SecurityQuestion.objects.get_or_create(
                    question=question_text
                )
                if created:
                    self.log(f"Created security question: {question_text}")
            
            self.log("Security questions created successfully")
            
        except Exception as e:
            self.log(f"Error creating security questions: {e}", True)

    def create_users(self):
        """Create sample users for all types"""
        try:
            # Create admin user
            admin_user, created = User.objects.get_or_create(
                phone_number='+255789123456',
                defaults={
                    'user_type': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_verified': True
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                
                # Create admin profile
                AdminProfile.objects.create(
                    user=admin_user,
                    names="System Administrator",
                    department="IT",
                    position="System Admin",
                    can_manage_users=True,
                    can_manage_vendors=True,
                    can_manage_order=True,
                    can_manage_content=True
                )
                self.log("Created admin user")
            else:
                self.log("Admin user already exists")
                
            self.users['admin'] = admin_user

            # Create vendor users
            vendor_data = [
                {
                    'phone': '+255745111111',
                    'names': 'John Mwita',
                    'business_name': 'Fresh Foods Ltd',
                    'business_license': 'BL001234',
                    'zanzibar_id': 'ZID001234',
                    'business_address': 'Mombasa Street, Dar es Salaam'
                },
                {
                    'phone': '+255745222222',
                    'names': 'Sarah Juma', 
                    'business_name': 'Quality Produce Co',
                    'business_license': 'BL002345',
                    'zanzibar_id': 'ZID002345',
                    'business_address': 'Arusha Road, Dar es Salaam'
                },
                {
                    'phone': '+255745333333',
                    'names': 'David Kimambo',
                    'business_name': 'Daily Groceries',
                    'business_license': 'BL003456',
                    'zanzibar_id': 'ZID003456',
                    'business_address': 'Ubungo Plaza, Dar es Salaam'
                }
            ]

            for i, vendor_info in enumerate(vendor_data):
                user, created = User.objects.get_or_create(
                    phone_number=vendor_info['phone'],
                    defaults={
                        'user_type': 'vendor',
                        'is_verified': True
                    }
                )
                if created:
                    user.set_password('vendor123')
                    user.save()
                    
                    # Create vendor profile
                    Vendor.objects.create(
                        user=user,
                        names=vendor_info['names'],
                        business_name=vendor_info['business_name'],
                        business_license=vendor_info['business_license'],
                        zanzibar_id=vendor_info['zanzibar_id'],
                        business_address=vendor_info['business_address'],
                        business_description=f"Quality {vendor_info['business_name']} providing fresh products",
                        is_verified=True,
                        verified_at=timezone.now()
                    )
                    self.log(f"Created vendor: {vendor_info['business_name']}")
                else:
                    self.log(f"Vendor already exists: {vendor_info['business_name']}")
                
                self.users[f'vendor_{i+1}'] = user

            # Create customer users
            customer_data = [
                {'phone': '+255744111111', 'names': 'Aisha Mohamed'},
                {'phone': '+255744222222', 'names': 'Rajab Hassan'},
                {'phone': '+255744333333', 'names': 'Grace Mwambile'},
            ]

            for i, customer_info in enumerate(customer_data):
                user, created = User.objects.get_or_create(
                    phone_number=customer_info['phone'],
                    defaults={
                        'user_type': 'customer',
                        'is_verified': True
                    }
                )
                if created:
                    user.set_password('customer123')
                    user.save()
                    
                    Customer.objects.create(
                        user=user,
                        names=customer_info['names'],
                        address=f"Customer address {i+1}, Dar es Salaam",
                        date_of_birth=date(1990, 1, 1)
                    )
                    self.log(f"Created customer: {customer_info['names']}")
                else:
                    self.log(f"Customer already exists: {customer_info['names']}")
                
                self.users[f'customer_{i+1}'] = user

            # Create driver user
            driver_user, created = User.objects.get_or_create(
                phone_number='+255745444444',
                defaults={
                    'user_type': 'driver',
                    'is_verified': True
                }
            )
            if created:
                driver_user.set_password('driver123')
                driver_user.save()
                
                Driver.objects.create(
                    user=driver_user,
                    names="Ahmed Simba",
                    license_number="DL001234",
                    vehicle_type="Motorcycle",
                    vehicle_plate="T123ABC",
                    is_available=True,
                    is_verified=True,
                    verified_at=timezone.now()
                )
                self.log("Created driver user")
            else:
                self.log("Driver user already exists")
            
            self.users['driver'] = driver_user

            self.log("All users created successfully")
            
        except Exception as e:
            self.log(f"Error creating users: {e}", True)

    def create_global_settings(self):
        """Create global settings"""
        try:
            settings_data = [
                {
                    'key': 'DEFAULT_PROFIT_PERCENTAGE',
                    'value': '15.00',
                    'description': 'Default profit percentage for products',
                    'data_type': 'decimal'
                },
                {
                    'key': 'TAX_RATE',
                    'value': '18.00', 
                    'description': 'VAT tax rate percentage',
                    'data_type': 'decimal'
                },
                {
                    'key': 'MIN_STOCK_ALERT',
                    'value': '10',
                    'description': 'Minimum stock level for alerts',
                    'data_type': 'integer'
                },
                {
                    'key': 'MAX_ORDER_QUANTITY',
                    'value': '100',
                    'description': 'Maximum quantity per order',
                    'data_type': 'integer'
                }
            ]

            for setting in settings_data:
                obj, created = GlobalSetting.objects.get_or_create(
                    key=setting['key'],
                    defaults={
                        'value': setting['value'],
                        'description': setting['description'],
                        'data_type': setting['data_type']
                    }
                )
                if created:
                    self.log(f"Created global setting: {setting['key']}")
                else:
                    self.log(f"Global setting already exists: {setting['key']}")
                    
            self.log("Global settings processed")
            
        except Exception as e:
            self.log(f"Error creating global settings: {e}", True)

    def create_measurement_units(self):
        """Create measurement unit types and units"""
        try:
            # Measurement Unit Types
            unit_types_data = [
                {'name': 'Weight', 'base_unit_name': 'gram', 'sort_order': 1},
                {'name': 'Volume', 'base_unit_name': 'milliliter', 'sort_order': 2},
                {'name': 'Count', 'base_unit_name': 'piece', 'sort_order': 3},
            ]

            for type_data in unit_types_data:
                unit_type, created = MeasurementUnitType.objects.get_or_create(
                    name=type_data['name'],
                    defaults=type_data
                )
                if created:
                    self.log(f"Created unit type: {type_data['name']}")
                self.unit_types[type_data['name']] = unit_type

            # Weight Units
            weight_units = [
                {'name': 'gram', 'symbol': 'g', 'conversion_factor': 1.0, 'is_base_unit': True, 'sort_order': 1},
                {'name': 'kilogram', 'symbol': 'kg', 'conversion_factor': 1000.0, 'sort_order': 2},
                {'name': 'robo', 'symbol': 'rb', 'conversion_factor': 250.0, 'sort_order': 3},
                {'name': 'nusu', 'symbol': 'ns', 'conversion_factor': 500.0, 'sort_order': 4},
                {'name': 'pau', 'symbol': 'pau', 'conversion_factor': 100.0, 'sort_order': 5},
            ]

            for unit_data in weight_units:
                unit, created = MeasurementUnit.objects.get_or_create(
                    unit_type=self.unit_types['Weight'],
                    name=unit_data['name'],
                    defaults=unit_data
                )
                if created:
                    self.log(f"Created weight unit: {unit_data['name']}")
                self.units[unit_data['name']] = unit

            # Volume Units
            volume_units = [
                {'name': 'milliliter', 'symbol': 'ml', 'conversion_factor': 1.0, 'is_base_unit': True, 'sort_order': 1},
                {'name': 'liter', 'symbol': 'L', 'conversion_factor': 1000.0, 'sort_order': 2},
            ]

            for unit_data in volume_units:
                unit, created = MeasurementUnit.objects.get_or_create(
                    unit_type=self.unit_types['Volume'],
                    name=unit_data['name'],
                    defaults=unit_data
                )
                if created:
                    self.log(f"Created volume unit: {unit_data['name']}")
                self.units[unit_data['name']] = unit

            # Count Units
            count_units = [
                {'name': 'piece', 'symbol': 'pcs', 'conversion_factor': 1.0, 'is_base_unit': True, 'sort_order': 1},
                {'name': 'dozen', 'symbol': 'doz', 'conversion_factor': 12.0, 'sort_order': 2},
                {'name': 'pack', 'symbol': 'pack', 'conversion_factor': 1.0, 'sort_order': 3},
            ]

            for unit_data in count_units:
                unit, created = MeasurementUnit.objects.get_or_create(
                    unit_type=self.unit_types['Count'],
                    name=unit_data['name'],
                    defaults=unit_data
                )
                if created:
                    self.log(f"Created count unit: {unit_data['name']}")
                self.units[unit_data['name']] = unit

            self.log("Measurement units created successfully")
            
        except Exception as e:
            self.log(f"Error creating measurement units: {e}", True)

    def create_categories(self):
        """Create product categories"""
        try:
            categories_data = [
                {
                    'name': 'Fresh Fruits',
                    'description': 'Fresh and seasonal fruits',
                    'profit_percentage': 20.00,
                    'parent': None
                },
                {
                    'name': 'Vegetables', 
                    'description': 'Fresh vegetables and greens',
                    'profit_percentage': 15.00,
                    'parent': None
                },
                {
                    'name': 'Dairy & Eggs',
                    'description': 'Milk, cheese, eggs and dairy products',
                    'profit_percentage': 12.00,
                    'parent': None
                },
                {
                    'name': 'Meat & Poultry',
                    'description': 'Fresh meat and poultry products',
                    'profit_percentage': 18.00,
                    'parent': None
                },
                {
                    'name': 'Fish & Seafood',
                    'description': 'Fresh and frozen fish products',
                    'profit_percentage': 22.00,
                    'parent': None
                },
            ]

            for cat_data in categories_data:
                category, created = Category.objects.get_or_create(
                    name=cat_data['name'],
                    defaults=cat_data
                )
                if created:
                    self.log(f"Created category: {cat_data['name']}")
                else:
                    self.log(f"Category already exists: {cat_data['name']}")
                self.categories[cat_data['name']] = category

            self.log("Categories created successfully")
            
        except Exception as e:
            self.log(f"Error creating categories: {e}", True)

    def create_markets(self):
        """Create markets and market zones"""
        try:
            markets_data = [
                {
                    'name': 'Kariakoo Market',
                    'description': 'Largest market in Dar es Salaam',
                    'location': 'Kariakoo, Dar es Salaam',
                    'latitude': -6.8161,
                    'longitude': 39.2804,
                    'address': 'Kariakoo Area, Dar es Salaam',
                    'contact_phone': '+255222111111',
                    'opening_time': '06:00:00',
                    'closing_time': '20:00:00',
                    'market_days': 'Daily'
                },
                {
                    'name': 'Mwenge Market',
                    'description': 'Famous for crafts and local products',
                    'location': 'Mwenge, Dar es Salaam', 
                    'latitude': -6.7761,
                    'longitude': 39.2083,
                    'address': 'Mwenge Area, Dar es Salaam',
                    'contact_phone': '+255222222222',
                    'opening_time': '07:00:00',
                    'closing_time': '19:00:00',
                    'market_days': 'Daily'
                },
                {
                    'name': 'Ilala Market',
                    'description': 'Central market in Ilala district',
                    'location': 'Ilala, Dar es Salaam',
                    'latitude': -6.9105,
                    'longitude': 39.2567,
                    'address': 'Ilala Area, Dar es Salaam',
                    'contact_phone': '+255222333333',
                    'opening_time': '06:30:00',
                    'closing_time': '19:30:00',
                    'market_days': 'Monday-Saturday'
                },
                {
                    'name': 'Tandale Market',
                    'description': 'Busy local market',
                    'location': 'Tandale, Dar es Salaam',
                    'latitude': -6.8000,
                    'longitude': 39.2333,
                    'address': 'Tandale Area, Dar es Salaam',
                    'contact_phone': '+255222444444',
                    'opening_time': '06:00:00',
                    'closing_time': '20:00:00',
                    'market_days': 'Daily'
                },
                {
                    'name': 'Buguruni Market',
                    'description': 'Popular residential market',
                    'location': 'Buguruni, Dar es Salaam',
                    'latitude': -6.8236,
                    'longitude': 39.2417,
                    'address': 'Buguruni Area, Dar es Salaam',
                    'contact_phone': '+255222555555',
                    'opening_time': '06:00:00',
                    'closing_time': '19:00:00',
                    'market_days': 'Daily'
                }
            ]

            for market_data in markets_data:
                market, created = Market.objects.get_or_create(
                    name=market_data['name'],
                    defaults=market_data
                )
                if created:
                    self.log(f"Created market: {market_data['name']}")
                else:
                    self.log(f"Market already exists: {market_data['name']}")
                self.markets[market_data['name']] = market

            # Create market zones
            zones_data = [
                {'market': 'Kariakoo Market', 'name': 'Fruits Zone', 'zone_type': 'Fruits'},
                {'market': 'Kariakoo Market', 'name': 'Vegetables Zone', 'zone_type': 'Vegetables'},
                {'market': 'Kariakoo Market', 'name': 'Fish Zone', 'zone_type': 'Fish'},
                {'market': 'Mwenge Market', 'name': 'Produce Section', 'zone_type': 'Produce'},
                {'market': 'Ilala Market', 'name': 'Fresh Foods Zone', 'zone_type': 'Foods'},
            ]

            for zone_data in zones_data:
                zone, created = MarketZone.objects.get_or_create(
                    market=self.markets[zone_data['market']],
                    name=zone_data['name'],
                    defaults={
                        'zone_type': zone_data['zone_type'],
                        'description': f"{zone_data['zone_type']} section in {zone_data['market']}"
                    }
                )
                if created:
                    self.log(f"Created market zone: {zone_data['market']} - {zone_data['name']}")
                else:
                    self.log(f"Market zone already exists: {zone_data['market']} - {zone_data['name']}")
                self.market_zones[f"{zone_data['market']}_{zone_data['name']}"] = zone

            self.log("Markets and zones created successfully")
            
        except Exception as e:
            self.log(f"Error creating markets: {e}", True)

    def create_products(self):
        """Create product templates and variants with new UnitPrice system"""
        try:
            products_data = [
                {
                    'name': 'Fresh Mangoes',
                    'description': 'Sweet and juicy fresh mangoes, perfect for juices and desserts',
                    'category': 'Fresh Fruits',
                    'unit_type': 'Weight',
                    'available_units': ['kilogram', 'robo', 'nusu', 'pau'],
                    'search_keywords': 'mango, maembe, fruit, sweet, juicy, fresh, tropical',
                    'variants': [
                        {
                            'vendor': 'vendor_1',
                            'market_zone': 'Kariakoo Market_Fruits Zone',
                            'base_cost_price': 2.50,
                            'custom_profit_percentage': 25.00,
                            'current_stock': 150.0,
                            'quality_grade': 'premium'
                        },
                        {
                            'vendor': 'vendor_2', 
                            'market_zone': 'Mwenge Market_Produce Section',
                            'base_cost_price': 2.20,
                            'current_stock': 100.0,
                            'quality_grade': 'standard'
                        }
                    ]
                },
                {
                    'name': 'Sukuma Wiki (Kale)',
                    'description': 'Fresh green sukuma wiki, rich in vitamins and minerals',
                    'category': 'Vegetables', 
                    'unit_type': 'Weight',
                    'available_units': ['kilogram', 'robo', 'nusu'],
                    'search_keywords': 'sukuma wiki, kale, greens, vegetable, healthy, fresh',
                    'variants': [
                        {
                            'vendor': 'vendor_1',
                            'market_zone': 'Kariakoo Market_Vegetables Zone', 
                            'base_cost_price': 1.20,
                            'current_stock': 80.0,
                            'quality_grade': 'standard'
                        },
                        {
                            'vendor': 'vendor_3',
                            'market_zone': 'Ilala Market_Fresh Foods Zone',
                            'base_cost_price': 1.00,
                            'current_stock': 60.0,
                            'quality_grade': 'economy'
                        }
                    ]
                },
                {
                    'name': 'Fresh Milk',
                    'description': 'Pure fresh cow milk, pasteurized and packaged',
                    'category': 'Dairy & Eggs',
                    'unit_type': 'Volume', 
                    'available_units': ['liter', 'milliliter'],
                    'search_keywords': 'milk, maziwa, fresh, dairy, cow milk, pasteurized',
                    'variants': [
                        {
                            'vendor': 'vendor_2',
                            'market_zone': 'Kariakoo Market_Fruits Zone',
                            'base_cost_price': 3.00,
                            'current_stock': 50.0,
                            'quality_grade': 'premium'
                        }
                    ]
                },
                {
                    'name': 'Beef Steak',
                    'description': 'Premium quality beef steak, tender and fresh',
                    'category': 'Meat & Poultry',
                    'unit_type': 'Weight',
                    'available_units': ['kilogram', 'robo', 'nusu'],
                    'search_keywords': 'beef, steak, nyama, meat, fresh, protein',
                    'variants': [
                        {
                            'vendor': 'vendor_1',
                            'market_zone': 'Kariakoo Market_Fish Zone',
                            'base_cost_price': 8.50,
                            'custom_profit_percentage': 20.00,
                            'current_stock': 30.0,
                            'quality_grade': 'premium'
                        }
                    ]
                },
                {
                    'name': 'Fresh Tilapia',
                    'description': 'Fresh tilapia fish from Lake Victoria, cleaned and ready to cook',
                    'category': 'Fish & Seafood', 
                    'unit_type': 'Count',
                    'available_units': ['piece', 'kilogram'],
                    'search_keywords': 'tilapia, fish, samaki, fresh, lake victoria, seafood',
                    'variants': [
                        {
                            'vendor': 'vendor_3',
                            'market_zone': 'Kariakoo Market_Fish Zone',
                            'base_cost_price': 4.00,
                            'current_stock': 25.0,
                            'quality_grade': 'standard'
                        }
                    ]
                }
            ]

            for product_data in products_data:
                # Create product template
                template, created = ProductTemplate.objects.get_or_create(
                    name=product_data['name'],
                    defaults={
                        'description': product_data['description'],
                        'category': self.categories[product_data['category']],
                        'primary_unit_type': self.unit_types[product_data['unit_type']],
                        'search_keywords': product_data['search_keywords'],
                        'is_active': True,
                        'is_verified': True,
                        'created_by': self.users['admin']
                    }
                )
                
                if created:
                    self.log(f"Created product template: {product_data['name']}")
                else:
                    self.log(f"Product template already exists: {product_data['name']}")
                
                # Add available units
                for unit_name in product_data['available_units']:
                    template.available_units.add(self.units[unit_name])
                
                self.product_templates[product_data['name']] = template

                # Create product variants
                for variant_data in product_data['variants']:
                    # NEW: Create variant WITHOUT base_cost_price
                    variant, created = ProductVariant.objects.get_or_create(
                        product_template=template,
                        vendor=self.users[variant_data['vendor']].vendor,
                        market_zone=self.market_zones[variant_data['market_zone']],
                        defaults={
                            'current_stock': variant_data['current_stock'],
                            'quality_grade': variant_data['quality_grade'],
                            'is_active': True,
                            'is_approved': True,
                            'custom_profit_percentage': variant_data.get('custom_profit_percentage')
                        }
                    )
                    
                    if created:
                        self.log(f"Created product variant: {product_data['name']} for {variant_data['vendor']}")
                    
                    # NEW: Create UnitPrice with explicit cost_price and selling_price
                    for unit_name in product_data['available_units']:
                        unit = self.units[unit_name]
                        cost_price = Decimal(str(variant_data['base_cost_price']))  # Use this as COST
                        profit_pct = variant.effective_profit_percentage
                        selling_price = cost_price + (cost_price * profit_pct / Decimal('100'))
                        
                        UnitPrice.objects.get_or_create(
                            product_variant=variant,
                            unit=unit,
                            defaults={
                                'cost_price': cost_price,
                                'selling_price': selling_price
                            }
                        )
                        if created:
                            self.log(f"Created unit price: {product_data['name']} - {unit_name}: cost={cost_price}, selling={selling_price}")

            self.log("Products and variants created successfully")
            
        except Exception as e:
            self.log(f"Error creating products: {e}", True)

    def seed_delivery_fee_config(self):
        """Seed delivery fee configuration: 100m = 200 TZS per 100m increment"""
        try:
            # Calculate per_km_rate: 200 TZS per 100m = 2000 TZS per km
            config, created = DeliveryFeeConfig.objects.get_or_create(
                name='Default Delivery Config',
                defaults={
                    'calculation_method': 'haversine',
                    'base_fee': Decimal('1000.00'),  # Minimum 1000 TZS
                    'per_km_rate': Decimal('2000.00'),  # 200 TZS per 100m = 2000 TZS per km
                    'free_delivery_threshold': Decimal('50000.00'),  # Free delivery on orders >= 50,000 TZS
                    'max_delivery_distance': Decimal('50.00'),  # Maximum 50 km
                    'surcharge_percent': Decimal('0.00'),  # No surcharge
                    'delivery_time_estimate_per_km': 3,  # 3 minutes per km
                    'min_delivery_time': 30,  # Minimum 30 minutes
                    'is_active': True,
                    'is_default': True
                }
            )
            if created:
                self.log(f"Created delivery fee config: {config.name}")
                self.log(f"  - Base fee: {config.base_fee} TZS")
                self.log(f"  - Per km rate: {config.per_km_rate} TZS (200 TZS per 100m)")
            else:
                self.log(f"Delivery fee config already exists: {config.name}")
        except Exception as e:
            self.log(f"Error seeding delivery fee config: {e}", True)

    def create_addons(self):
        """Create product addons"""
        try:
            addons_data = [
                {
                    'name': 'Peeling Service',
                    'description': 'Professional peeling and preparation service',
                    'price': 1.50,
                    'addon_type': 'preparation'
                },
                {
                    'name': 'Cutting Service', 
                    'description': 'Cutting and slicing service',
                    'price': 1.00,
                    'addon_type': 'preparation'
                },
                {
                    'name': 'Gift Packaging',
                    'description': 'Special gift wrapping and packaging',
                    'price': 2.00,
                    'addon_type': 'packaging'
                },
                {
                    'name': 'Express Delivery',
                    'description': 'Priority delivery within 1 hour',
                    'price': 3.00,
                    'addon_type': 'delivery'
                }
            ]

            for addon_data in addons_data:
                addon, created = ProductAddon.objects.get_or_create(
                    name=addon_data['name'],
                    defaults=addon_data
                )
                if created:
                    self.log(f"Created addon: {addon_data['name']}")
                else:
                    self.log(f"Addon already exists: {addon_data['name']}")
                self.addons[addon_data['name']] = addon

            self.log("Product addons created successfully")
            
        except Exception as e:
            self.log(f"Error creating addons: {e}", True)

    def seed_all(self):
        """Run all seed methods in transaction"""
        try:
            with transaction.atomic():
                print("🚀 Starting database seeding...")
                print("=" * 50)
                
                self.create_security_questions()
                print("-" * 30)
                
                self.create_users()
                print("-" * 30)
                
                self.create_global_settings()
                print("-" * 30)
                
                self.create_measurement_units()
                print("-" * 30)
                
                self.seed_delivery_fee_config()
                print("-" * 30)
                
                self.create_categories()
                print("-" * 30)
                
                self.create_markets()
                print("-" * 30)
                
                self.create_products()
                print("-" * 30)
                
                self.create_addons()
                print("=" * 50)
                print("✅ Database seeding completed successfully!")
                
        except Exception as e:
            print(f"❌ Database seeding failed: {e}")
            import traceback
            traceback.print_exc()
            raise

def run_seed():
    """Run the seed script"""
    seeder = SeedData()
    seeder.seed_all()

if __name__ == '__main__':
    run_seed()