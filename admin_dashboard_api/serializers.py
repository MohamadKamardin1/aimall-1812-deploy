# admin_dashboard_api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from accounts.models import User, Customer, Vendor, Driver, AdminProfile, SecurityQuestion, UserSecurityAnswer

class GroupSerializer(serializers.ModelSerializer):
    permissions_count = serializers.IntegerField(source='permissions.count', read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), source='permissions', required=False
    )
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions_count', 'permission_ids']
from products.models import Category, ProductTemplate, MeasurementUnitType, MeasurementUnit, ProductVariant, UnitPrice, ProductAddon, ProductAddonMapping, ProductImage, GlobalSetting
from order.models import Order, OrderItem, OrderStatusUpdate, Cart, CartItem
from markets.models import Market, MarketDay, MarketZone
from location.models import DeliveryZone, DeliveryFeeConfig, DeliveryTimeSlot, CustomerAddress

class AdminProfileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    full_name = serializers.CharField(source='names', read_only=True)
    
    class Meta:
        model = AdminProfile
        fields = ['id', 'user', 'names', 'full_name', 'email', 'phone', 'department', 'position',
                 'can_manage_users', 'can_manage_vendors', 'can_manage_order',
                 'can_manage_content', 'created_at']

class CustomerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='user.id', read_only=True)
    name = serializers.CharField(source='names', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'user', 'names', 'name', 'phone', 'email', 'address', 'date_of_birth',
                 'is_active', 'created_at']

class SecurityQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityQuestion
        fields = ['id', 'question', 'is_active', 'created_at']

class UserSecurityAnswerSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    question_text = serializers.CharField(source='question.question', read_only=True)
    
    class Meta:
        model = UserSecurityAnswer
        fields = ['id', 'user', 'user_phone', 'question', 'question_text', 'answer', 'created_at']

class CustomerAddressSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.phone_number', read_only=True)
    market_name = serializers.CharField(source='market.name', read_only=True)
    delivery_zone_name = serializers.CharField(source='delivery_zone.name', read_only=True)
    
    class Meta:
        model = CustomerAddress
        fields = '__all__'

class UserListSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'email', 'user_type', 'user_type_display',
                 'is_active', 'is_verified', 'date_joined']

class UserDetailSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'email', 'user_type', 
                 'is_active', 'is_verified', 'date_joined', 'last_login', 'profile']
    
    def get_profile(self, obj):
        if obj.user_type == 'customer' and hasattr(obj, 'customer'):
            return {'name': obj.customer.names, 'address': obj.customer.address}
        elif obj.user_type == 'vendor' and hasattr(obj, 'vendor'):
            return {'name': obj.vendor.names, 'business': obj.vendor.business_name}
        elif obj.user_type == 'driver' and hasattr(obj, 'driver'):
            return {'name': obj.driver.names, 'license': obj.driver.license_number}
        return None

class VendorListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='user.id', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    
    class Meta:
        model = Vendor
        fields = ['id', 'names', 'business_name', 'phone', 'is_verified', 
                 'is_active', 'verified_at', 'created_at']

class DriverListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='user.id', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    
    class Meta:
        model = Driver
        fields = ['id', 'names', 'phone', 'license_number', 'vehicle_type',
                 'vehicle_plate', 'is_verified', 'is_available', 'is_active',
                 'created_at']

class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'profit_percentage', 'parent', 'parent_name', 
                 'sort_order', 'is_active', 'image', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.image:
            try:
                ret['image'] = instance.image.url
            except:
                ret['image'] = str(instance.image)
        return ret


class GlobalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSetting
        fields = '__all__'

class ProductTemplateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_unit_type_name = serializers.CharField(source='primary_unit_type.name', read_only=True)
    
    class Meta:
        model = ProductTemplate
        fields = ['id', 'name', 'description', 'category', 'category_name',
                 'primary_unit_type', 'primary_unit_type_name', 'available_units',
                 'main_image', 'is_active', 'is_verified', 'search_keywords', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.main_image:
            try:
                ret['main_image'] = instance.main_image.url
            except:
                ret['main_image'] = str(instance.main_image)
        return ret

class ProductVariantSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    market_zone_name = serializers.CharField(source='market_zone.name', read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = '__all__'

class UnitPriceSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    product_variant_name = serializers.CharField(source='product_variant.__str__', read_only=True)
    
    class Meta:
        model = UnitPrice
        fields = '__all__'

class ProductAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAddon
        fields = '__all__'

class ProductAddonMappingSerializer(serializers.ModelSerializer):
    addon_name = serializers.CharField(source='addon.name', read_only=True)
    
    class Meta:
        model = ProductAddonMapping
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    product_template_name = serializers.CharField(source='product_template.name', read_only=True)
    
    class Meta:
        model = ProductImage
        fields = ['id', 'product_template', 'product_template_name', 'image', 'caption', 'sort_order', 'is_active']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.image:
            try:
                ret['image'] = instance.image.url
            except:
                ret['image'] = str(instance.image)
        return ret

class OrderListSerializer(serializers.ModelSerializer):
    tracking_id = serializers.CharField(source='order_number', read_only=True)
    customer_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_market = serializers.SerializerMethodField()
    recipient_name = serializers.CharField(source='delivery_address.recipient_name', read_only=True)
    recipient_phone = serializers.CharField(source='delivery_address.recipient_phone', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'tracking_id', 'customer_name', 'status', 'status_display',
                 'payment_method', 'total_amount', 'items_total', 'delivery_fee', 'is_paid', 'created_at',
                 'assigned_market', 'recipient_name', 'recipient_phone']
    
    def get_customer_name(self, obj):
        name = None
        if obj.delivery_address and obj.delivery_address.recipient_name:
            name = obj.delivery_address.recipient_name
            
        if not name and hasattr(obj.customer, 'customer') and obj.customer.customer.names:
            name = obj.customer.customer.names
            
        return name or obj.customer.phone_number

    def get_assigned_market(self, obj):
        if obj.delivery_address and obj.delivery_address.market:
            market = obj.delivery_address.market
            return {
                'name': market.name,
                'latitude': float(market.latitude) if market.latitude else None,
                'longitude': float(market.longitude) if market.longitude else None
            }
        return None

class OrderDetailSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_market = serializers.SerializerMethodField()
    recipient_name = serializers.CharField(source='delivery_address.recipient_name', read_only=True)
    recipient_phone = serializers.CharField(source='delivery_address.recipient_phone', read_only=True)
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    driver_id = serializers.CharField(source='driver.id', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer', 'status', 'status_display', 'payment_method',
                 'items_total', 'delivery_fee', 'total_amount', 'is_paid',
                 'delivery_latitude', 'delivery_longitude', 'delivery_street_address',
                 'delivery_location_name', 'cancellation_reason', 'items', 'created_at',
                 'assigned_market', 'recipient_name', 'recipient_phone', 'driver_name', 'driver_id']
    
    def get_customer(self, obj):
        # 1. Try recipient phone
        phone = obj.delivery_address.recipient_phone if obj.delivery_address and obj.delivery_address.recipient_phone else obj.customer.phone_number
        
        # 2. Try recipient name, then customer profile, then user phone
        name = None
        if obj.delivery_address and obj.delivery_address.recipient_name:
            name = obj.delivery_address.recipient_name
            
        if not name and hasattr(obj.customer, 'customer') and obj.customer.customer.names:
            name = obj.customer.customer.names
            
        if not name:
            name = obj.customer.phone_number
            
        return {
            'name': name,
            'phone': phone
        }
    
    def get_items(self, obj):
        items = obj.items.all()[:50] # Increased limit
        return [{
            'id': str(item.id),
            'product': item.product_variant.product_template.name if item.product_variant else 'N/A',
            'quantity': float(item.quantity),
            'unit_name': item.measurement_unit.name if item.measurement_unit else 'unit',
            'unit_price': float(item.unit_price),
            'total': float(item.total_price)
        } for item in items]

    def get_assigned_market(self, obj):
        if obj.delivery_address and obj.delivery_address.market:
            market = obj.delivery_address.market
            return {
                'name': market.name,
                'latitude': float(market.latitude) if market.latitude else None,
                'longitude': float(market.longitude) if market.longitude else None
            }
        return None

class MarketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = ['id', 'name', 'description', 'contact_phone', 'address',
                 'location', 'latitude', 'longitude', 'is_active', 'created_at']

class DeliveryZoneSerializer(serializers.ModelSerializer):
    market_name = serializers.CharField(source='market.name', read_only=True)
    
    class Meta:
        model = DeliveryZone
        fields = '__all__'

class DeliveryFeeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryFeeConfig
        fields = '__all__'

class DeliveryTimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTimeSlot
        fields = '__all__'

class MarketDaySerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    
    class Meta:
        model = MarketDay
        fields = ['id', 'day', 'day_display']

class MarketZoneSerializer(serializers.ModelSerializer):
    market_name = serializers.CharField(source='market.name', read_only=True)
    
    class Meta:
        model = MarketZone
        fields = '__all__'

class MeasurementUnitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasurementUnitType
        fields = ['id', 'name', 'description', 'base_unit_name', 
                 'is_active', 'created_at']

class MeasurementUnitSerializer(serializers.ModelSerializer):
    unit_type_name = serializers.CharField(source='unit_type.name', read_only=True)
    
    class Meta:
        model = MeasurementUnit
        fields = ['id', 'name', 'symbol', 'unit_type', 'unit_type_name',
                 'conversion_factor', 'is_base_unit', 'is_active', 'created_at']

class PermissionSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'display_name']

    def get_display_name(self, obj):
        return f"{obj.content_type.app_label} | {obj.name}"

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    unit_name = serializers.CharField(source='measurement_unit.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product_variant', 'product_name', 'measurement_unit', 'unit_name',
                 'quantity', 'unit_price', 'total_price', 'addons_total', 'special_instructions', 'created_at']

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.phone_number', read_only=True)
    old_status_display = serializers.CharField(source='get_old_status_display', read_only=True)
    new_status_display = serializers.CharField(source='get_new_status_display', read_only=True)
    
    class Meta:
        model = OrderStatusUpdate
        fields = ['id', 'order', 'old_status', 'old_status_display', 'new_status', 'new_status_display',
                 'updated_by', 'updated_by_name', 'note', 'created_at']

class CartSerializer(serializers.ModelSerializer):
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    market_name = serializers.CharField(source='market.name', read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'customer', 'customer_phone', 'market', 'market_name', 
                 'delivery_address', 'delivery_time_slot', 'items_count', 'created_at', 'updated_at']

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    unit_name = serializers.CharField(source='measurement_unit.name', read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product_variant', 'product_name', 'measurement_unit', 'unit_name',
                 'quantity', 'unit_price', 'total_price', 'addons_total', 'special_instructions', 'created_at', 'updated_at']