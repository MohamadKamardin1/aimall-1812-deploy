from rest_framework import serializers
from .models import Market, MarketZone

class MarketZoneSerializer(serializers.ModelSerializer):
    market_name = serializers.CharField(source='market.name', read_only=True)
    
    class Meta:
        model = MarketZone
        fields = [
            'id', 'name', 'description', 'zone_type', 'market', 'market_name',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class MarketZoneDetailSerializer(MarketZoneSerializer):
    class Meta(MarketZoneSerializer.Meta):
        fields = MarketZoneSerializer.Meta.fields

class MarketSerializer(serializers.ModelSerializer):
    zones_count = serializers.SerializerMethodField()
    active_zones_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Market
        fields = [
            'id', 'name', 'description', 'location', 'latitude', 'longitude',
            'address', 'contact_phone', 'opening_time', 'closing_time',
            'market_days', 'is_active', 'zones_count', 'active_zones_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'zones_count', 'active_zones_count']
    
    def get_zones_count(self, obj):
        return obj.zones.count()
    
    def get_active_zones_count(self, obj):
        return obj.zones.filter(is_active=True).count()

class MarketDetailSerializer(MarketSerializer):
    zones = MarketZoneSerializer(many=True, read_only=True)
    
    class Meta(MarketSerializer.Meta):
        fields = MarketSerializer.Meta.fields + ['zones']