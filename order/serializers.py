# order/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem, ordertatusUpdate, Cart, CartItem
from location.models import CustomerAddress, DeliveryTimeSlot
from products.models import ProductVariant, MeasurementUnit, ProductAddon

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='product_variant.vendor.business_name', read_only=True)
    unit_name = serializers.CharField(source='measurement_unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='measurement_unit.symbol', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_variant', 'product_name', 'vendor_name',
                 'measurement_unit', 'unit_name', 'unit_symbol', 'quantity',
                 'unit_price', 'total_price', 'selected_addons', 'addons_total',
                 'special_instructions']

class ordererializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.customer.names', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    delivery_address_details = serializers.CharField(source='delivery_address.street_address', read_only=True)
    driver_name = serializers.CharField(source='driver.driver.names', read_only=True, allow_null=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer', 'customer_name', 'customer_phone',
                 'delivery_address', 'delivery_address_details', 'delivery_time_slot',
                 'scheduled_delivery_date', 'scheduled_delivery_time', 'driver', 'driver_name',
                 'items_total', 'delivery_fee', 'service_fee', 'discount_amount', 'total_amount',
                 'payment_method', 'is_paid', 'payment_reference', 'status', 'cancellation_reason',
                 'items', 'created_at', 'confirmed_at', 'assigned_at', 'picked_up_at',
                 'delivered_at', 'cancelled_at']
        read_only_fields = ['order_number', 'created_at', 'confirmed_at', 'assigned_at',
                           'picked_up_at', 'delivered_at', 'cancelled_at']

class Createordererializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['delivery_address', 'delivery_time_slot', 'payment_method']
    
    def validate(self, data):
        customer = self.context['request'].user
        cart = getattr(customer, 'cart', None)
        
        if not cart or cart.items.count() == 0:
            raise serializers.ValidationError("Cart is empty")
        
        if not data.get('delivery_address'):
            raise serializers.ValidationError("Delivery address is required")
        
        if not data.get('delivery_time_slot'):
            raise serializers.ValidationError("Delivery time slot is required")
        
        return data

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='product_variant.vendor.business_name', read_only=True)
    unit_name = serializers.CharField(source='measurement_unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='measurement_unit.symbol', read_only=True)
    in_stock = serializers.BooleanField(source='product_variant.is_in_stock', read_only=True)
    max_quantity = serializers.DecimalField(source='product_variant.current_stock', read_only=True, max_digits=10, decimal_places=3)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product_variant', 'product_name', 'vendor_name',
                 'measurement_unit', 'unit_name', 'unit_symbol', 'quantity',
                 'unit_price', 'total_price', 'selected_addons', 'addons_total',
                 'special_instructions', 'in_stock', 'max_quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    market = serializers.SerializerMethodField()
    market_name = serializers.CharField(source='market.name', read_only=True)
    delivery_address_details = serializers.CharField(source='delivery_address.street_address', read_only=True)
    time_slot_name = serializers.CharField(source='delivery_time_slot.name', read_only=True)
    
    def get_market(self, obj):
        """Return market with id and name"""
        if obj.market:
            return {
                'id': str(obj.market.id),
                'name': obj.market.name,
                'location': obj.market.location,
            }
        return None
    
    class Meta:
        model = Cart
        fields = ['id', 'customer', 'market', 'market_name', 'delivery_address',
                 'delivery_address_details', 'delivery_time_slot', 'time_slot_name',
                 'items_count', 'subtotal', 'delivery_fee', 'total', 'items',
                 'created_at', 'updated_at']
        read_only_fields = ['customer', 'items_count', 'subtotal', 'delivery_fee', 'total']

class AddToCartSerializer(serializers.Serializer):
    product_variant_id = serializers.UUIDField()
    measurement_unit_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0.001)
    addon_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    special_instructions = serializers.CharField(required=False, allow_blank=True)

class ordertatusUpdateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = ordertatusUpdate
        fields = ['id', 'order', 'old_status', 'new_status', 'updated_by',
                 'updated_by_name', 'note', 'created_at']