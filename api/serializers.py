"""
API Serializers for Flutter mobile app
- Customer authentication (register, login, forgot password via security questions)
- Product catalog (templates, variants, options, prices)
- Cart management (per-market carts)
- Order placement with geo-location
- Driver order delivery
"""

from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from accounts.models import User, Customer, SecurityQuestion, UserSecurityAnswer, Vendor, Driver
from products.models import (
    ProductTemplate, ProductVariant, MeasurementUnit, UnitPrice, 
    ProductAddon, ProductAddonMapping, ProductImage, FavoriteItem
)
from markets.models import Market, MarketZone
from location.models import CustomerAddress, DeliveryZone, DeliveryFeeConfig
from order.models import Order, OrderItem, Cart, CartItem


# ============================================
# AUTHENTICATION SERIALIZERS
# ============================================

class CustomerLoginSerializer(serializers.Serializer):
    """Customer phone number and password login"""
    phone_number = serializers.CharField(max_length=13)
    password = serializers.CharField(write_only=True, min_length=6)
    
    def validate_phone_number(self, value):
        if not value.startswith('+255'):
            raise serializers.ValidationError("Phone number must start with +255")
        return value
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        
        user = authenticate(username=phone_number, password=password)
        if not user:
            raise serializers.ValidationError("Invalid phone number or password.")
        
        if user.user_type != 'customer':
            raise serializers.ValidationError("Only customers can log in through this endpoint.")
        
        attrs['user'] = user
        return attrs


class SecurityQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityQuestion
        fields = ('id', 'question')


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=13, write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)
    security_answers = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        write_only=True,
        required=True
    )
    names = serializers.CharField(max_length=255)
    
    class Meta:
        model = Customer
        fields = (
            'names', 'phone_number', 'email', 'address', 'date_of_birth',
            'password', 'password_confirm', 'security_answers'
        )
    
    def validate_phone_number(self, value):
        if not value.startswith('+255'):
            raise serializers.ValidationError("Phone number must start with +255")
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("User with this phone number already exists.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        validate_password(attrs['password'])
        return attrs
    
    def create(self, validated_data):
        # Extract data
        phone_number = validated_data.pop('phone_number')
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        security_answers = validated_data.pop('security_answers')
        names = validated_data.pop('names')
        
        # Create user
        user = User.objects.create_user(
            phone_number=phone_number,
            password=password,
            user_type='customer',
            email=validated_data.pop('email', '')
        )
        
        # Create customer profile
        customer = Customer.objects.create(user=user, names=names, **validated_data)
        
        # Save security answers
        for answer_data in security_answers:
            question_id = answer_data.get('question_id')
            answer = answer_data.get('answer')
            if question_id and answer:
                UserSecurityAnswer.objects.create(
                    user=user,
                    question_id=question_id,
                    answer=answer
                )
        
        return customer


class ForgotPasswordRequestSerializer(serializers.Serializer):
    """Request password reset security questions"""
    phone_number = serializers.CharField(max_length=13)
    
    def validate_phone_number(self, value):
        if not value.startswith('+255'):
            raise serializers.ValidationError("Phone number must start with +255")
        try:
            User.objects.get(phone_number=value, user_type='customer')
        except User.DoesNotExist:
            raise serializers.ValidationError("Customer with this phone number not found.")
        return value


class ForgotPasswordVerifySerializer(serializers.Serializer):
    """Verify security answers and reset password"""
    phone_number = serializers.CharField(max_length=13)
    answers = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        required=True
    )
    new_password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        validate_password(attrs['new_password'])
        return attrs


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Customer profile with user details"""
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.CharField(source='user.email')
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = ('phone_number', 'email', 'names', 'address', 'date_of_birth', 'profile_picture_url')
    
    def get_profile_picture_url(self, obj):
        return obj.user.get_profile_picture_url()


class DriverProfileSerializer(serializers.ModelSerializer):
    """Driver profile with vehicle and verification details"""
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    driver_id = serializers.CharField(source='user.id', read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Driver
        fields = (
            'driver_id', 'phone_number', 'names', 'license_number', 
            'vehicle_type', 'vehicle_plate', 'is_available', 'is_verified',
            'verified_at', 'created_at', 'profile_picture_url'
        )
        read_only_fields = ('license_number', 'is_verified', 'verified_at', 'created_at')
    
    def get_profile_picture_url(self, obj):
        return obj.user.get_profile_picture_url()


# ============================================
# PRODUCT CATALOG SERIALIZERS
# ============================================

class MeasurementUnitSerializer(serializers.ModelSerializer):
    """Measurement unit (kg, L, pcs, etc.)"""
    unit_type_name = serializers.CharField(source='unit_type.name', read_only=True)
    
    class Meta:
        model = MeasurementUnit
        fields = ('id', 'name', 'symbol', 'unit_type_name', 'unit_type')


class UnitPriceSerializer(serializers.ModelSerializer):
    """Price per measurement unit"""
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='unit.symbol', read_only=True)
    
    class Meta:
        model = UnitPrice
        fields = ('id', 'unit', 'unit_name', 'unit_symbol', 'cost_price', 'selling_price')


class ProductAddonSerializer(serializers.ModelSerializer):
    """Optional product add-ons (peeling, cutting, etc.)"""
    class Meta:
        model = ProductAddon
        fields = ('id', 'name', 'price', 'addon_type')


class ProductVariantDetailSerializer(serializers.ModelSerializer):
    """Detailed product variant with prices and options"""
    product_name = serializers.CharField(source='product_template.name', read_only=True)
    category_name = serializers.CharField(source='product_template.category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    vendor_id = serializers.CharField(source='vendor.user.id', read_only=True)
    market_zone_name = serializers.CharField(source='market_zone.name', read_only=True)
    
    unit_prices = UnitPriceSerializer(many=True, read_only=True)
    available_addons = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = (
            'id', 'product_name', 'category_name', 'vendor_name', 'vendor_id',
            'market_zone_name', 'quality_grade', 'unit_prices', 'available_addons',
            'product_image', 'is_active'
        )
    
    def get_available_addons(self, obj):
        mappings = ProductAddonMapping.objects.filter(product_variant=obj, is_active=True)
        return ProductAddonSerializer([m.addon for m in mappings], many=True).data
    
    def get_product_image(self, obj):
        if obj.product_template.main_image:
            return obj.product_template.main_image.url
        return None


class ProductTemplateListSerializer(serializers.ModelSerializer):
    """Product template for catalog listing"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    vendors_count = serializers.SerializerMethodField()
    available_units = serializers.SerializerMethodField()
    display_price = serializers.SerializerMethodField()
    display_unit = serializers.SerializerMethodField()
    primary_variant = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductTemplate
        fields = (
            'id', 'name', 'category_name', 'image_url', 'vendors_count',
            'description', 'available_units', 'display_price', 'display_unit', 'primary_variant'
        )
    
    def get_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None
    
    def get_vendors_count(self, obj):
        return obj.variants.filter(is_active=True).count()
    
    def get_available_units(self, obj):
        """Return list of available units for this product with their symbols"""
        units = obj.available_units.filter(is_active=True).order_by('sort_order')
        # Deduplicate units by id while preserving order
        seen = set()
        out = []
        for u in units:
            if u.id in seen:
                continue
            seen.add(u.id)
            out.append({'id': str(u.id), 'symbol': u.symbol, 'name': u.name})
        return out

    def get_display_price(self, obj):
        """
        Choose a sensible display price for the product template.
        Strategy: find the largest `selling_price` among all variants' unit_prices
        (so customers see the highest price option in the listing). Return as string.
        """
        from decimal import Decimal
        max_price = None
        for variant in obj.variants.filter(is_active=True, is_approved=True):
            for up in variant.unit_prices.all():
                try:
                    val = Decimal(str(up.selling_price))
                except Exception:
                    continue
                if max_price is None or val > max_price:
                    max_price = val

        return str(max_price) if max_price is not None else None

    def get_display_unit(self, obj):
        """
        Return the unit symbol associated with the display price (if available).
        If multiple units tie, prefer the first encountered.
        """
        from decimal import Decimal
        max_price = None
        unit_symbol = None
        for variant in obj.variants.filter(is_active=True, is_approved=True):
            for up in variant.unit_prices.all():
                try:
                    val = Decimal(str(up.selling_price))
                except Exception:
                    continue
                if max_price is None or val > max_price:
                    max_price = val
                    unit_symbol = getattr(up, 'unit_symbol', None) or getattr(getattr(up, 'unit', None), 'symbol', None)

        return unit_symbol

    def get_primary_variant(self, obj):
        """
        Return a compact representation of the single primary variant for this
        product template. Primary variant is chosen as the variant/unit_price
        combination with the highest selling_price across active, approved
        variants. The returned dict includes variant id, vendor info and the
        selected unit_price data.
        """
        from decimal import Decimal
        primary = None
        primary_up = None

        for variant in obj.variants.filter(is_active=True, is_approved=True):
            for up in variant.unit_prices.all():
                try:
                    val = Decimal(str(up.selling_price))
                except Exception:
                    continue
                if primary_up is None or val > Decimal(str(primary_up.selling_price)):
                    primary = variant
                    primary_up = up

        if not primary or not primary_up:
            return None

        return {
            'variant_id': str(primary.id),
            'vendor_name': getattr(primary, 'vendor').business_name if getattr(primary, 'vendor', None) else None,
            'vendor_id': str(getattr(primary.vendor.user, 'id', None)) if getattr(primary, 'vendor', None) else None,
            'unit_price': {
                'id': str(primary_up.id),
                'unit': str(getattr(primary_up.unit, 'id', None)) if getattr(primary_up, 'unit', None) else None,
                'unit_symbol': getattr(primary_up.unit, 'symbol', None) if getattr(primary_up, 'unit', None) else None,
                'selling_price': str(primary_up.selling_price),
                'cost_price': str(primary_up.cost_price) if getattr(primary_up, 'cost_price', None) is not None else None,
            }
        }


class ProductTemplateDetailSerializer(serializers.ModelSerializer):
    """Detailed product template with variants from available markets"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    additional_images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductTemplate
        fields = (
            'id', 'name', 'description', 'category_name', 'primary_unit_type',
            'image_url', 'additional_images', 'variants'
        )
    
    def get_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None
    
    def get_additional_images(self, obj):
        images = obj.additional_images.filter(is_active=True)
        return [img.image.url for img in images]
    
    def get_variants(self, obj):
        """Return variants, optionally filtered by market"""
        variants = obj.variants.filter(is_active=True, is_approved=True)
        
        # Check if we should filter by market
        market_id = self.context.get('request').query_params.get('market_id') if self.context.get('request') else None
        
        if market_id:
            # Filter variants to only those from vendors registered in this market
            from markets.models import Market
            try:
                market = Market.objects.get(id=market_id, is_active=True)
                # Filter variants whose vendor's market_zones include this market
                variants = variants.filter(
                    market_zone__market_id=market.id
                ).distinct()
            except (Market.DoesNotExist, ValueError):
                # If market is invalid, return empty variants
                variants = variants.none()
        
        # Choose the single primary variant (highest unit_price selling_price)
        from decimal import Decimal
        primary_variant = None
        primary_up = None

        for variant in variants:
            for up in variant.unit_prices.all():
                try:
                    val = Decimal(str(up.selling_price))
                except Exception:
                    continue
                if primary_up is None or val > Decimal(str(primary_up.selling_price)):
                    primary_variant = variant
                    primary_up = up

        if not primary_variant:
            # Fallback: return empty list
            return []

        return ProductVariantDetailSerializer([primary_variant], many=True).data


class MarketListSerializer(serializers.ModelSerializer):
    """Market with location for map display"""
    zone_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Market
        fields = ('id', 'name', 'location', 'latitude', 'longitude', 'zone_count')
    
    def get_zone_count(self, obj):
        return obj.zones.filter(is_active=True).count()


# ============================================
# CART SERIALIZERS
# ============================================

class CartItemCreateSerializer(serializers.Serializer):
    """Add item to cart"""
    product_variant_id = serializers.UUIDField()
    unit_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0.001)
    selected_addons = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    special_instructions = serializers.CharField(required=False, allow_blank=True)


class CartItemSerializer(serializers.ModelSerializer):
    """Cart item with product details"""
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='product_variant.vendor.business_name', read_only=True)
    unit_symbol = serializers.CharField(source='measurement_unit.symbol', read_only=True)
    selected_addons_data = serializers.SerializerMethodField()
    main_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = (
            'id', 'product_variant', 'product_name', 'vendor_name', 'measurement_unit',
            'unit_symbol', 'quantity', 'unit_price', 'addons_total', 'total_price',
            'selected_addons_data', 'special_instructions', 'main_image_url'
        )
    
    def get_selected_addons_data(self, obj):
        addons = obj.selected_addons.all()
        return ProductAddonSerializer(addons, many=True).data
    
    def get_main_image_url(self, obj):
        """Get product image from the product variant's template"""
        if obj.product_variant and obj.product_variant.product_template:
            if obj.product_variant.product_template.main_image:
                return obj.product_variant.product_template.main_image.url
        return None


class CartSerializer(serializers.ModelSerializer):
    """Shopping cart with items and pricing"""
    items = CartItemSerializer(many=True, read_only=True)
    market = serializers.SerializerMethodField()
    market_name = serializers.CharField(source='market.name', read_only=True)
    delivery_address_data = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = (
            'id', 'market', 'market_name', 'items', 'delivery_address_data',
            'subtotal', 'delivery_fee', 'total'
        )
    
    def get_delivery_address_data(self, obj):
        if obj.delivery_address:
            return {
                'id': str(obj.delivery_address.id),
                'address': obj.delivery_address.address,
                'latitude': str(obj.delivery_address.latitude),
                'longitude': str(obj.delivery_address.longitude),
            }
        return None

    def get_market(self, obj):
        if obj.market:
            return {
                'id': str(obj.market.id),
                'name': obj.market.name,
                'location': obj.market.location,
            }
        return None


# ============================================
# ADDRESS SERIALIZERS
# ============================================

class CustomerAddressSerializer(serializers.ModelSerializer):
    """Customer delivery address with coordinates"""
    class Meta:
        model = CustomerAddress
        fields = ('id', 'address', 'latitude', 'longitude', 'is_default')


class CustomerAddressCreateSerializer(serializers.ModelSerializer):
    """Create/update customer address"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    
    class Meta:
        model = CustomerAddress
        fields = ('label', 'street_address', 'latitude', 'longitude', 'market', 'recipient_name', 'recipient_phone', 'is_default')
        extra_kwargs = {
            'street_address': {'required': False, 'allow_blank': True},
            'recipient_name': {'required': False, 'allow_blank': True},
            'recipient_phone': {'required': False, 'allow_blank': True},
            'is_default': {'required': False, 'default': False},
        }


# ============================================
# ORDER SERIALIZERS
# ============================================

class OrderItemDetailSerializer(serializers.ModelSerializer):
    """Order item with full product, variant, and vendor details"""
    product_template_id = serializers.CharField(source='product_variant.product_template.id', read_only=True)
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    vendor_id = serializers.CharField(source='product_variant.vendor.user.id', read_only=True)
    vendor_name = serializers.CharField(source='product_variant.vendor.business_name', read_only=True)
    vendor_phone = serializers.CharField(source='product_variant.vendor.user.phone_number', read_only=True)
    unit_name = serializers.CharField(source='measurement_unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='measurement_unit.symbol', read_only=True)
    selected_addons_data = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = (
            'id', 'product_template_id', 'product_name', 'product_image',
            'vendor_id', 'vendor_name', 'vendor_phone',
            'unit_name', 'unit_symbol', 'quantity', 'unit_price',
            'addons_total', 'total_price', 'selected_addons_data',
            'special_instructions'
        )
    
    def get_product_image(self, obj):
        if obj.product_variant.product_template.main_image:
            return obj.product_variant.product_template.main_image.url
        return None
    
    def get_selected_addons_data(self, obj):
        addons = obj.selected_addons.all()
        return ProductAddonSerializer(addons, many=True).data


class OrderCreateSerializer(serializers.Serializer):
    """Create order from cart with delivery details and location"""
    market_id = serializers.UUIDField()
    delivery_address_id = serializers.UUIDField()
    customer_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    customer_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal('0.00'))
    delivery_location_name = serializers.CharField(max_length=255, required=False, default='Delivery Location')
    payment_method = serializers.ChoiceField(choices=['cash_on_delivery', 'mobile_money', 'card'])


class OrderDetailSerializer(serializers.ModelSerializer):
    """Complete order details with all information"""
    customer_name = serializers.CharField(source='customer.customer.names', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_address = serializers.SerializerMethodField()
    customer_location = serializers.SerializerMethodField()
    delivery_location = serializers.SerializerMethodField()
    market_name = serializers.CharField(source='delivery_address.delivery_zone.market.name', read_only=True)
    delivery_zone_name = serializers.CharField(source='delivery_address.delivery_zone.name', read_only=True)
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()
    driver_vehicle = serializers.SerializerMethodField()
    items = OrderItemDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'customer_name', 'customer_phone',
            'customer_address', 'customer_location', 'delivery_location',
            'delivery_location_name', 'delivery_latitude', 'delivery_longitude', 
            'delivery_street_address', 'market_name',
            'delivery_zone_name', 'items', 'items_total', 'delivery_fee',
            'service_fee', 'discount_amount', 'total_amount', 'payment_method',
            'is_paid', 'status', 'driver_name', 'driver_phone', 'driver_vehicle',
            'created_at', 'scheduled_delivery_date', 'scheduled_delivery_time'
        )
    
    def get_customer_address(self, obj):
        """Get customer address from delivery address"""
        addr = obj.delivery_address
        # Build address from available fields
        address_parts = []
        if hasattr(addr, 'street_address') and addr.street_address:
            address_parts.append(addr.street_address)
        if hasattr(addr, 'landmark') and addr.landmark:
            address_parts.append(f"({addr.landmark})")
        if hasattr(addr, 'area') and addr.area:
            address_parts.append(addr.area)
        return ', '.join(address_parts) if address_parts else f"{addr.label}" if hasattr(addr, 'label') else "Delivery Location"
    
    def get_customer_location(self, obj):
        return {
            'latitude': str(obj.delivery_address.latitude),
            'longitude': str(obj.delivery_address.longitude),
        }
    
    def get_delivery_location(self, obj):
        """Get complete delivery location details for driver"""
        return {
            'name': obj.delivery_location_name or 'Delivery Location',
            'latitude': str(obj.delivery_latitude) if obj.delivery_latitude else None,
            'longitude': str(obj.delivery_longitude) if obj.delivery_longitude else None,
            'street_address': obj.delivery_street_address or '',
            'label': obj.delivery_location_name or 'Location'
        }
    
    def get_driver_name(self, obj):
        if obj.driver and hasattr(obj.driver, 'driver'):
            return obj.driver.driver.names
        return None
    
    def get_driver_phone(self, obj):
        if obj.driver:
            return obj.driver.phone_number
        return None
    
    def get_driver_vehicle(self, obj):
        if obj.driver and hasattr(obj.driver, 'driver'):
            driver = obj.driver.driver
            return {
                'type': driver.vehicle_type,
                'plate': driver.vehicle_plate,
            }
        return None


class OrderListSerializer(serializers.ModelSerializer):
    """Order summary for listing"""
    order_items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'total_amount', 'status', 'payment_method',
            'order_items_count', 'created_at', 'scheduled_delivery_date'
        )
    
    def get_order_items_count(self, obj):
        return obj.items.count()


# ============================================
# DRIVER SERIALIZERS
# ============================================

class DriverOrderListSerializer(serializers.ModelSerializer):
    """Order for driver delivery list"""
    customer_name = serializers.CharField(source='customer.customer.names', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_location = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'customer_name', 'customer_phone',
            'customer_location', 'items_count', 'total_amount', 'status',
            'scheduled_delivery_date', 'scheduled_delivery_time'
        )
    
    def get_customer_location(self, obj):
        return {
            'latitude': str(obj.delivery_address.latitude),
            'longitude': str(obj.delivery_address.longitude),
        }
    
    def get_items_count(self, obj):
        """Count only valid items (quantity > 0)"""
        from .driver_order_helpers import get_valid_items
        return get_valid_items(obj).count()


class DriverOrderDetailSerializer(serializers.ModelSerializer):
    """
    Detailed order view for driver with complete location and item information
    
    Data includes:
    - Customer details (name, phone, address)
    - Market location (from vendor's market, used for map)
    - Delivery location (customer's coordinates, used for map)
    - Distance calculation between market and delivery point
    - Items with measurement units (NOT quantities with 0)
    - Total amount (items only, NO delivery fee exposed)
    - Order status and payment info
    - Scheduled delivery time
    
    IMPORTANT: Does NOT include:
    - delivery_fee (driver paid in bulk, not per order)
    - service_fee (hidden from driver)
    - discount_amount (hidden from driver)
    """
    customer_name = serializers.CharField(source='customer.customer.names', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_address = serializers.SerializerMethodField()
    market_location = serializers.SerializerMethodField()
    delivery_location = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    items_total = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = (
            'id', 'order_number',
            'customer_name', 'customer_phone', 'customer_address',
            'market_location', 'delivery_location', 'distance_km',
            'items', 'items_total', 'items_count',
            'total_amount', 'payment_method', 'is_paid', 'status',
            'scheduled_delivery_date', 'scheduled_delivery_time'
        )
    
    def get_customer_address(self, obj):
        """
        Build complete customer delivery address
        
        Returns:
            dict with street_address, location_name, area, landmark
        """
        return {
            'street_address': obj.delivery_street_address or 'Delivery Address',
            'location_name': obj.delivery_location_name or 'Delivery Location',
            'area': getattr(obj.delivery_address, 'area', '') if obj.delivery_address else '',
            'landmark': getattr(obj.delivery_address, 'landmark', '') if obj.delivery_address else ''
        }
    
    def get_market_location(self, obj):
        """
        Extract market location from order items
        
        Logic:
        1. Get first item's vendor
        2. Get vendor's associated market
        3. Return market name, latitude, longitude, address
        4. Fallback to default if not found
        
        Returns:
            dict with name, latitude, longitude, address
        """
        from .driver_order_helpers import get_market_location
        return get_market_location(obj)
    
    def get_delivery_location(self, obj):
        """
        Extract delivery location from order
        
        Returns:
            dict with latitude, longitude, address, location_name
        """
        from .driver_order_helpers import get_delivery_location
        return get_delivery_location(obj)
    
    def get_distance_km(self, obj):
        """
        Calculate distance between market and delivery point
        
        Logic:
        1. Get market coordinates
        2. Get delivery coordinates
        3. Calculate geodesic distance
        4. Return in kilometers
        
        Returns:
            float: Distance in kilometers
        """
        from .driver_order_helpers import (
            get_market_location, 
            get_delivery_location, 
            calculate_distance_between_points
        )
        
        market = get_market_location(obj)
        delivery = get_delivery_location(obj)
        
        return calculate_distance_between_points(
            market['latitude'],
            market['longitude'],
            delivery['latitude'],
            delivery['longitude']
        )
    
    def get_items(self, obj):
        """
        Get order items with measurement units
        
        Logic:
        1. Filter items with quantity > 0 (exclude zero quantities)
        2. Include measurement unit name and symbol for each item
        3. Include quantity, unit_price, total_price
        4. Include product details and image
        5. Include special instructions if any
        
        Returns:
            list of formatted order items with all display information
        """
        from .driver_order_helpers import get_valid_items
        
        valid_items = get_valid_items(obj)
        
        items_data = []
        for item in valid_items:
            try:
                product = item.product_variant.product_template
                items_data.append({
                    'id': str(item.id),
                    'product_name': product.name,
                    'product_image': product.main_image.url if product.main_image else None,
                    'vendor_name': item.product_variant.vendor.business_name,
                    'quantity': float(item.quantity),
                    'measurement_unit': {
                        'name': item.measurement_unit.name,
                        'symbol': item.measurement_unit.symbol
                    },
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price),
                    'addons': [
                        {'name': addon.name, 'price': float(addon.price)}
                        for addon in item.selected_addons.all()
                    ],
                    'special_instructions': item.special_instructions or ''
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error formatting item {item.id}: {e}")
                continue
        
        return items_data
    
    def get_items_total(self, obj):
        """
        Calculate items total (NOT including delivery fee, service fee, or discounts)
        
        Logic:
        1. Get only valid items (quantity > 0)
        2. Sum their total_price field
        3. This is what customer paid for items only
        4. Driver gets delivery fee separately (bulk, not per order)
        
        Returns:
            float: Sum of all item prices
        """
        from .driver_order_helpers import calculate_items_total_only
        return float(calculate_items_total_only(obj))
    
    def get_items_count(self, obj):
        """Count of valid items in order"""
        from .driver_order_helpers import get_valid_items
        return get_valid_items(obj).count()


class FavoriteItemSerializer(serializers.ModelSerializer):
    """Serializer for favorite items with product details"""
    product = ProductTemplateListSerializer(source='product', read_only=True)
    
    class Meta:
        model = FavoriteItem
        fields = ('id', 'product', 'added_at')
        read_only_fields = ('id', 'added_at')

