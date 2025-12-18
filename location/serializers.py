# location/serializers.py
from rest_framework import serializers
from .models import DeliveryTimeSlot, DeliveryZone, CustomerAddress
from markets.models import Market

class DeliveryTimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTimeSlot
        fields = ['id', 'name', 'cut_off_time', 'delivery_start_time', 
                 'delivery_end_time', 'is_active']

class DeliveryZoneSerializer(serializers.ModelSerializer):
    market_name = serializers.CharField(source='market.name', read_only=True)
    
    class Meta:
        model = DeliveryZone
        fields = ['id', 'market', 'market_name', 'name', 'description', 
                 'base_delivery_fee', 'is_manual_pricing', 'manual_delivery_fee',
                 'is_active', 'created_at']

class CustomerAddressSerializer(serializers.ModelSerializer):
    market_name = serializers.CharField(source='market.name', read_only=True)
    delivery_zone_name = serializers.CharField(source='delivery_zone.name', read_only=True)
    estimated_delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CustomerAddress
        fields = ['id', 'customer', 'market', 'market_name', 'delivery_zone', 
                 'delivery_zone_name', 'label', 'street_address', 'landmark',
                 'latitude', 'longitude', 'recipient_name', 'recipient_phone',
                 'additional_notes', 'is_default', 'is_active', 
                 'estimated_delivery_fee', 'created_at']
        read_only_fields = ['customer']
    
    def validate(self, data):
        # Calculate delivery fee if coordinates are provided
        if data.get('latitude') and data.get('longitude') and data.get('market'):
            delivery_zone = data.get('delivery_zone')
            if delivery_zone:
                data['estimated_delivery_fee'] = delivery_zone.calculate_delivery_fee(
                    data['latitude'], data['longitude']
                )
        return data

class MarketWithZonesSerializer(serializers.ModelSerializer):
    delivery_zones = DeliveryZoneSerializer(many=True, read_only=True)
    time_slots = DeliveryTimeSlotSerializer(many=True, read_only=True)
    
    class Meta:
        model = Market
        fields = ['id', 'name', 'description', 'location', 'latitude', 'longitude',
                 'address', 'contact_phone', 'opening_time', 'closing_time',
                 'delivery_zones', 'time_slots']