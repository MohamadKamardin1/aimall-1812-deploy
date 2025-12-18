"""
API Tests for Flutter mobile app endpoints

Test coverage:
- Authentication (register, login, forgot password)
- Product catalog browsing
- Cart management
- Order creation and management
- Driver order handling
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from django.utils import timezone

from accounts.models import Customer, Vendor, Driver, SecurityQuestion, UserSecurityAnswer
from products.models import (
    ProductTemplate, ProductVariant, Category, MeasurementUnitType,
    MeasurementUnit, UnitPrice
)
from markets.models import Market, MarketZone
from location.models import CustomerAddress, DeliveryZone, DeliveryFeeConfig
from order.models import Order, OrderItem, Cart, CartItem

User = get_user_model()


class CustomerAuthTestCase(TestCase):
    """Test customer authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create security questions
        self.q1 = SecurityQuestion.objects.create(question="What is your first pet's name?")
        self.q2 = SecurityQuestion.objects.create(question="What city were you born?")
    
    def test_customer_registration(self):
        """Test customer registration with security questions"""
        data = {
            'phone_number': '+255712345678',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'names': 'John Doe',
            'email': 'john@example.com',
            'security_answers': [
                {'question_id': str(self.q1.id), 'answer': 'Fluffy'},
                {'question_id': str(self.q2.id), 'answer': 'Dar es Salaam'}
            ]
        }
        
        response = self.client.post('/api/v1/auth/register/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['phone_number'], '+255712345678')
        
        # Verify user was created
        self.assertTrue(User.objects.filter(phone_number='+255712345678').exists())
        user = User.objects.get(phone_number='+255712345678')
        self.assertEqual(user.user_type, 'customer')
        self.assertTrue(hasattr(user, 'customer'))
    
    def test_customer_login(self):
        """Test customer login"""
        # Create user
        user = User.objects.create_user(
            phone_number='+255712345678',
            password='testpass123',
            user_type='customer'
        )
        Customer.objects.create(user=user, names='John Doe')
        
        # Login
        data = {
            'phone_number': '+255712345678',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/v1/auth/login/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_forgot_password_request(self):
        """Test forgot password request"""
        # Create user
        user = User.objects.create_user(
            phone_number='+255712345678',
            password='testpass123',
            user_type='customer'
        )
        Customer.objects.create(user=user, names='John Doe')
        
        data = {'phone_number': '+255712345678'}
        response = self.client.post('/api/v1/auth/forgot-password/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('security_questions', response.data)
    
    def test_forgot_password_verify(self):
        """Test password reset verification"""
        # Create user with security answers
        user = User.objects.create_user(
            phone_number='+255712345678',
            password='testpass123',
            user_type='customer'
        )
        Customer.objects.create(user=user, names='John Doe')
        UserSecurityAnswer.objects.create(
            user=user,
            question=self.q1,
            answer='Fluffy'
        )
        UserSecurityAnswer.objects.create(
            user=user,
            question=self.q2,
            answer='Dar es Salaam'
        )
        
        data = {
            'phone_number': '+255712345678',
            'answers': [
                {'question_id': str(self.q1.id), 'answer': 'Fluffy'},
                {'question_id': str(self.q2.id), 'answer': 'Dar es Salaam'}
            ],
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        
        response = self.client.post('/api/v1/auth/reset-password/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProductCatalogTestCase(TestCase):
    """Test product catalog endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create category
        self.category = Category.objects.create(
            name='Fruits',
            profit_percentage=Decimal('20.00')
        )
        
        # Create measurement unit
        self.unit_type = MeasurementUnitType.objects.create(
            name='Weight',
            base_unit_name='gram'
        )
        self.unit = MeasurementUnit.objects.create(
            unit_type=self.unit_type,
            name='Kilogram',
            symbol='kg',
            conversion_factor=Decimal('1000.0')
        )
        
        # Create product template
        self.product = ProductTemplate.objects.create(
            name='Mango',
            category=self.category,
            primary_unit_type=self.unit_type,
            is_active=True,
            is_verified=True
        )
        self.product.available_units.add(self.unit)
        
        # Create market and vendor
        self.market = Market.objects.create(
            name='Darajani Market',
            location='Stone Town'
        )
        self.market_zone = MarketZone.objects.create(
            market=self.market,
            name='Sokoni la Matunda'
        )
        
        self.vendor_user = User.objects.create_user(
            phone_number='+255712345679',
            password='vendor123',
            user_type='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            names='Ali Farm',
            business_name='Ali Farm',
            business_license='BL123',
            zanzibar_id='ZID123',
            business_address='Stone Town'
        )
        
        # Create product variant
        self.variant = ProductVariant.objects.create(
            product_template=self.product,
            vendor=self.vendor,
            market_zone=self.market_zone,
            quality_grade='premium',
            is_active=True,
            is_approved=True
        )
        
        # Create unit price
        UnitPrice.objects.create(
            product_variant=self.variant,
            unit=self.unit,
            cost_price=Decimal('2000.00')
        )
    
    def test_list_markets(self):
        """Test market listing for map"""
        response = self.client.get('/api/v1/markets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Darajani Market')
    
    def test_list_products(self):
        """Test product listing"""
        response = self.client.get('/api/v1/products/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        self.assertEqual(response.data['results'][0]['name'], 'Mango')
    
    def test_get_product_details(self):
        """Test product detail view"""
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Mango')
        self.assertEqual(len(response.data['variants']), 1)


class CartTestCase(TestCase):
    """Test cart management endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create customer user
        self.customer_user = User.objects.create_user(
            phone_number='+255712345678',
            password='testpass123',
            user_type='customer'
        )
        self.customer = Customer.objects.create(
            user=self.customer_user,
            names='John Doe'
        )
        
        # Setup products
        self.category = Category.objects.create(
            name='Fruits',
            profit_percentage=Decimal('20.00')
        )
        
        self.unit_type = MeasurementUnitType.objects.create(
            name='Weight',
            base_unit_name='gram'
        )
        self.unit = MeasurementUnit.objects.create(
            unit_type=self.unit_type,
            name='Kilogram',
            symbol='kg'
        )
        
        self.product = ProductTemplate.objects.create(
            name='Mango',
            category=self.category,
            primary_unit_type=self.unit_type,
            is_active=True,
            is_verified=True
        )
        self.product.available_units.add(self.unit)
        
        # Setup market and vendor
        self.market = Market.objects.create(name='Darajani Market', location='Stone Town')
        self.market_zone = MarketZone.objects.create(market=self.market, name='Sokoni la Matunda')
        
        self.vendor_user = User.objects.create_user(
            phone_number='+255712345679',
            password='vendor123',
            user_type='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            names='Ali',
            business_name='Ali Farm',
            business_license='BL123',
            zanzibar_id='ZID123',
            business_address='Stone Town'
        )
        
        self.variant = ProductVariant.objects.create(
            product_template=self.product,
            vendor=self.vendor,
            market_zone=self.market_zone,
            is_active=True,
            is_approved=True
        )
        
        self.unit_price = UnitPrice.objects.create(
            product_variant=self.variant,
            unit=self.unit,
            cost_price=Decimal('2000.00')
        )
        
        # Login customer
        self.client.force_authenticate(user=self.customer_user)
    
    def test_add_to_cart(self):
        """Test adding item to cart"""
        data = {
            'market_id': str(self.market.id),
            'product_variant_id': str(self.variant.id),
            'unit_id': str(self.unit.id),
            'quantity': Decimal('2.5'),
            'special_instructions': 'Peel the mango'
        }
        
        response = self.client.post('/api/v1/cart/add/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Item added to cart')
        
        # Verify cart item was created
        self.assertTrue(CartItem.objects.filter(cart__customer=self.customer_user).exists())
    
    def test_get_cart(self):
        """Test getting cart"""
        # Create cart item
        cart = Cart.objects.create(customer=self.customer_user, market=self.market)
        CartItem.objects.create(
            cart=cart,
            product_variant=self.variant,
            measurement_unit=self.unit,
            quantity=Decimal('2.5'),
            unit_price=self.unit_price.selling_price
        )
        
        response = self.client.get(f'/api/v1/cart/get/?market_id={self.market.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)


class OrderTestCase(TestCase):
    """Test order creation and management"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Setup customer
        self.customer_user = User.objects.create_user(
            phone_number='+255712345678',
            password='testpass123',
            user_type='customer'
        )
        self.customer = Customer.objects.create(user=self.customer_user, names='John Doe')
        
        # Setup market and delivery zone
        self.market = Market.objects.create(name='Darajani Market', location='Stone Town')
        self.market_zone = MarketZone.objects.create(market=self.market, name='Sokoni')
        
        config = DeliveryFeeConfig.objects.create(
            name='Default',
            base_fee=Decimal('500.00'),
            per_km_rate=Decimal('200.00'),
            is_default=True
        )
        
        self.delivery_zone = DeliveryZone.objects.create(
            market=self.market,
            name='Zone A',
            zone_type='standard',
            is_active=True
        )
        
        # Setup address
        self.address = CustomerAddress.objects.create(
            customer=self.customer,
            market=self.market,
            label='Home',
            street_address='House 123',
            latitude=Decimal('-6.1599'),
            longitude=Decimal('39.1925'),
            recipient_name='John Doe',
            recipient_phone='+255712345678',
            delivery_zone=self.delivery_zone
        )
        
        # Setup products
        self.category = Category.objects.create(name='Fruits')
        self.unit_type = MeasurementUnitType.objects.create(name='Weight', base_unit_name='gram')
        self.unit = MeasurementUnit.objects.create(
            unit_type=self.unit_type,
            name='kg',
            symbol='kg'
        )
        
        self.product = ProductTemplate.objects.create(
            name='Mango',
            category=self.category,
            primary_unit_type=self.unit_type,
            is_active=True,
            is_verified=True
        )
        self.product.available_units.add(self.unit)
        
        # Setup vendor
        self.vendor_user = User.objects.create_user(
            phone_number='+255712345679',
            password='vendor123',
            user_type='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            names='Ali',
            business_name='Ali Farm',
            business_license='BL123',
            zanzibar_id='ZID123',
            business_address='Stone Town'
        )
        
        self.variant = ProductVariant.objects.create(
            product_template=self.product,
            vendor=self.vendor,
            market_zone=self.market_zone,
            is_active=True,
            is_approved=True
        )
        
        self.unit_price = UnitPrice.objects.create(
            product_variant=self.variant,
            unit=self.unit,
            cost_price=Decimal('2000.00')
        )
        
        # Login customer
        self.client.force_authenticate(user=self.customer_user)
    
    def test_create_order(self):
        """Test order creation from cart"""
        # Add item to cart
        cart = Cart.objects.create(customer=self.customer_user, market=self.market)
        CartItem.objects.create(
            cart=cart,
            product_variant=self.variant,
            measurement_unit=self.unit,
            quantity=Decimal('2.5'),
            unit_price=self.unit_price.selling_price
        )
        
        # Create order
        data = {
            'market_id': str(self.market.id),
            'delivery_address_id': str(self.address.id),
            'customer_latitude': '-6.1599',
            'customer_longitude': '39.1925',
            'payment_method': 'cash_on_delivery'
        }
        
        response = self.client.post('/api/v1/orders/create_order/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Order created successfully')
        self.assertIn('order', response.data)
        
        # Verify order was created
        order = Order.objects.get(id=response.data['order']['id'])
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.items.count(), 1)


# Run tests with: python manage.py test api
