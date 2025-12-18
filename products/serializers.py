from rest_framework import serializers
from .models import (
    Category, MeasurementUnitType, MeasurementUnit,
    ProductTemplate, ProductVariant, UnitPrice,
    ProductAddon, ProductAddonMapping, GlobalSetting,
    ProductImage
)

class GlobalSettingSerializer(serializers.ModelSerializer):
    formatted_value = serializers.SerializerMethodField()
    
    class Meta:
        model = GlobalSetting
        fields = [
            'id', 'key', 'value', 'formatted_value', 'description', 
            'data_type', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_formatted_value(self, obj):
        """Convert value based on data type"""
        try:
            if obj.data_type == 'integer':
                return int(obj.value)
            elif obj.data_type == 'decimal':
                return float(obj.value)
            elif obj.data_type == 'boolean':
                return obj.value.lower() in ('true', '1', 'yes')
            elif obj.data_type == 'json':
                import json
                return json.loads(obj.value)
            else:
                return obj.value
        except (ValueError, json.JSONDecodeError):
            return obj.value

class CategorySerializer(serializers.ModelSerializer):
    subcategories_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'profit_percentage', 'parent', 'parent_name',
            'typical_market_zones', 'is_active', 'image', 'sort_order', 
            'subcategories_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'subcategories_count']
    
    def get_subcategories_count(self, obj):
        return obj.subcategories.filter(is_active=True).count()

class CategoryDetailSerializer(CategorySerializer):
    subcategories = CategorySerializer(many=True, read_only=True)
    market_zones = serializers.SerializerMethodField()
    
    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ['subcategories', 'market_zones']
    
    def get_market_zones(self, obj):
        from markets.serializers import MarketZoneSerializer
        return MarketZoneSerializer(obj.typical_market_zones.all(), many=True).data

class MeasurementUnitTypeSerializer(serializers.ModelSerializer):
    units_count = serializers.SerializerMethodField()
    base_unit = serializers.SerializerMethodField()
    
    class Meta:
        model = MeasurementUnitType
        fields = [
            'id', 'name', 'description', 'base_unit_name', 
            'is_active', 'sort_order', 'units_count', 'base_unit',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'units_count', 'base_unit']
    
    def get_units_count(self, obj):
        return obj.units.filter(is_active=True).count()
    
    def get_base_unit(self, obj):
        base_unit = obj.units.filter(is_base_unit=True, is_active=True).first()
        if base_unit:
            return MeasurementUnitSerializer(base_unit).data
        return None

class MeasurementUnitSerializer(serializers.ModelSerializer):
    unit_type_name = serializers.CharField(source='unit_type.name', read_only=True)
    
    class Meta:
        model = MeasurementUnit
        fields = [
            'id', 'name', 'symbol', 'unit_type', 'unit_type_name',
            'conversion_factor', 'is_base_unit', 'is_active',
            'sort_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, attrs):
        # Ensure only one base unit per unit type
        if attrs.get('is_base_unit', False):
            unit_type = attrs.get('unit_type') or self.instance.unit_type
            existing_base = MeasurementUnit.objects.filter(
                unit_type=unit_type, 
                is_base_unit=True,
                is_active=True
            ).exclude(pk=getattr(self.instance, 'pk', None))
            
            if existing_base.exists():
                raise serializers.ValidationError({
                    'is_base_unit': f'There is already a base unit for {unit_type.name}'
                })
        
        return attrs

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'image_url', 'caption', 'sort_order', 
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'image_url']
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

class ProductTemplateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    available_units_details = MeasurementUnitSerializer(source='available_units', many=True, read_only=True)
    primary_unit_type_name = serializers.CharField(source='primary_unit_type.name', read_only=True)
    main_image_url = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductTemplate
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'primary_unit_type', 'primary_unit_type_name', 'available_units', 
            'available_units_details', 'main_image', 'main_image_url',
            'is_active', 'is_verified', 'search_keywords', 'similar_products',
            'created_by', 'variants_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 
            'variants_count', 'main_image_url'
        ]
    
    def get_main_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None
    
    def get_variants_count(self, obj):
        return obj.variants.filter(is_active=True).count()

class ProductTemplateDetailSerializer(ProductTemplateSerializer):
    additional_images = ProductImageSerializer(many=True, read_only=True)
    similar_products_details = ProductTemplateSerializer(source='similar_products', many=True, read_only=True)
    
    class Meta(ProductTemplateSerializer.Meta):
        fields = ProductTemplateSerializer.Meta.fields + [
            'additional_images', 'similar_products_details'
        ]

class UnitPriceSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='unit.symbol', read_only=True)
    unit_type = serializers.CharField(source='unit.unit_type.name', read_only=True)
    product_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='product_variant.vendor.business_name', read_only=True)
    
    class Meta:
        model = UnitPrice
        fields = [
            'id', 'product_variant', 'product_name', 'vendor_name',
            'unit', 'unit_name', 'unit_symbol', 'unit_type', 
            'selling_price','is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        product_variant = attrs.get('product_variant') or self.instance.product_variant
        unit = attrs.get('unit')
        price = attrs.get('price')
        
        # Validate unit belongs to product's available units
        if unit and product_variant:
            available_units = product_variant.product_template.available_units.all()
            if unit not in available_units:
                raise serializers.ValidationError({
                    'unit': f'This unit is not available for the product {product_variant.product_template.name}'
                })
        
        # Validate price is positive
        if price is not None and price < 0:
            raise serializers.ValidationError({
                'price': 'Price cannot be negative'
            })
        
        # Validate that we're not creating duplicate unit prices
        if self.instance is None:  # Only for creation
            existing = UnitPrice.objects.filter(
                product_variant=product_variant,
                unit=unit,
                is_active=True
            )
            if existing.exists():
                raise serializers.ValidationError({
                    'unit': f'A unit price for {unit.name} already exists for this product'
                })
        
        return attrs
    
    def create(self, validated_data):
        # Ensure the unit price is active by default
        validated_data['is_active'] = True
        return super().create(validated_data)

class ProductVariantSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_template.name', read_only=True)
    product_description = serializers.CharField(source='product_template.description', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    market_zone_name = serializers.CharField(source='market_zone.name', read_only=True)
    market_name = serializers.CharField(source='market_zone.market.name', read_only=True)
    category_name = serializers.CharField(source='product_template.category.name', read_only=True)
    profit_percentage = serializers.SerializerMethodField()
    selling_price_base = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product_template', 'product_name', 'product_description',
            'vendor', 'vendor_name', 'market_zone', 'market_zone_name', 'market_name',
            'base_cost_price', 'custom_profit_percentage', 'profit_percentage',
            'selling_price_base', 'current_stock', 'min_stock_alert',
            'is_in_stock', 'quality_grade', 'is_active', 'is_approved',
            'category_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'profit_percentage', 
            'selling_price_base'
        ]
    
    def get_profit_percentage(self, obj):
        return float(obj.profit_percentage)
    
    def get_selling_price_base(self, obj):
        return float(obj.selling_price_base)
    
    def validate(self, attrs):
        # Ensure vendor is creating variant in their authorized market zones
        if self.context['request'].user.user_type == 'vendor':
            vendor = self.context['request'].user.vendor
            market_zone = attrs.get('market_zone')
            
            if market_zone and hasattr(self, 'instance'):
                # For updates, check if market_zone is being changed
                if self.instance and market_zone != self.instance.market_zone:
                    # In real implementation, you might want to restrict this
                    pass
            
            # Ensure vendor is associated with the market
            # This would require a VendorMarket association model in real implementation
        
        return attrs

class ProductVariantDetailSerializer(ProductVariantSerializer):
    unit_prices = UnitPriceSerializer(many=True, read_only=True)
    available_addons = serializers.SerializerMethodField()
    product_template_details = ProductTemplateSerializer(source='product_template', read_only=True)
    
    class Meta(ProductVariantSerializer.Meta):
        fields = ProductVariantSerializer.Meta.fields + [
            'unit_prices', 'available_addons', 'product_template_details'
        ]
    
    def get_available_addons(self, obj):
        addon_mappings = obj.available_addons.filter(is_active=True)
        return ProductAddonMappingSerializer(addon_mappings, many=True).data

class ProductAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAddon
        fields = [
            'id', 'name', 'description', 'price', 'addon_type',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value

class ProductAddonMappingSerializer(serializers.ModelSerializer):
    addon_details = ProductAddonSerializer(source='addon', read_only=True)
    product_variant_name = serializers.CharField(source='product_variant.product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='product_variant.vendor.business_name', read_only=True)
    
    class Meta:
        model = ProductAddonMapping
        fields = [
            'id', 'product_variant', 'product_variant_name', 'vendor_name',
            'addon', 'addon_details', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

# Simplified serializers for list views
class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'profit_percentage', 'is_active']

class ProductTemplateListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductTemplate
        fields = [
            'id', 'name', 'category_name', 'main_image_url', 
            'is_active', 'is_verified'
        ]
    
    def get_main_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None

class ProductVariantListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_template.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    market_name = serializers.CharField(source='market_zone.market.name', read_only=True)
    min_price = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product_name', 'vendor_name', 'market_name',
            'base_cost_price', 'is_in_stock', 'quality_grade',
            'is_active', 'is_approved', 'min_price'
        ]
    
    def get_min_price(self, obj):
        min_unit_price = obj.unit_prices.filter(is_active=True).order_by('price').first()
        return min_unit_price.price if min_unit_price else None