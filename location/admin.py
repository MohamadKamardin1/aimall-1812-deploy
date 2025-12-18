# location/admin.py
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from leaflet.admin import LeafletGeoAdmin, LeafletGeoAdminMixin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import DeliveryFeeConfig, DeliveryZone, DeliveryTimeSlot, CustomerAddress


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(LeafletGeoAdmin):
    list_display = [
        'name',
        'market_link',
        'zone_type_display',
        'distance_display',
        'fee_display',
        'estimated_time_display',
        'is_active',
        'priority'
    ]
    
    list_filter = [
        'market',
        'zone_type',
        'is_active',
        'priority'
    ]
    
    search_fields = [
        'name',
        'description',
        'market__name'
    ]
    
    list_editable = ['priority', 'is_active']
    list_per_page = 20
    autocomplete_fields = ['market']
    
    # Correct Leaflet widget settings
    settings_overrides = {
        'DEFAULT_CENTER': (-6.3690, 34.8888),
        'DEFAULT_ZOOM': 12,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
        'TILES': [('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            'attribution': '&copy; OpenStreetMap contributors'
        })],
    }
    
    # Specify which fields use Leaflet widgets
    settings = {
        'DEFAULT_CENTER': (-6.3690, 34.8888),
        'DEFAULT_ZOOM': 12,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
        'TILES': [('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            'attribution': '&copy; OpenStreetMap contributors'
        })],
    }
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'market',
                'name',
                'description',
                'zone_type',
                'priority',
                'is_active'
            )
        }),
        ('Zone Boundaries', {
            'fields': ('boundary', 'center_point'),
            'description': 'Draw the zone boundary polygon and set a center point'
        }),
        ('Pricing Configuration', {
            'fields': ('fixed_price', 'surcharge_percent'),
            'description': 'Configure pricing based on zone type'
        }),
        ('Calculated Fields', {
            'fields': (
                'distance_from_market',
                'estimated_delivery_time'
            ),
            'classes': ('collapse',),
            'description': 'Auto-calculated fields'
        }),
    )
    
    readonly_fields = [
        'distance_from_market',
        'estimated_delivery_time'
    ]
    
    def market_link(self, obj):
        url = reverse('admin:markets_market_change', args=[obj.market.id])
        return format_html('<a href="{}">{}</a>', url, obj.market.name)
    market_link.short_description = 'Market'
    market_link.admin_order_field = 'market__name'
    
    def zone_type_display(self, obj):
        colors = {
            'standard': 'blue',
            'fixed': 'green',
            'free': 'orange',
            'surcharge': 'red',
            'unavailable': 'gray'
        }
        color = colors.get(obj.zone_type, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_zone_type_display()
        )
    zone_type_display.short_description = 'Zone Type'
    
    def distance_display(self, obj):
        if obj.distance_from_market:
            return f"{obj.distance_from_market} km"
        return "-"
    distance_display.short_description = 'Distance'
    
    def fee_display(self, obj):
        config = DeliveryFeeConfig.get_active_config()
        if not config:
            return "-"
        
        # Sample calculation for center point
        if obj.center_point and obj.market.geo_location:
            sample_fee = obj.calculate_delivery_fee(obj.center_point)
            if sample_fee is None:
                return format_html(
                    '<span style="color: red; font-weight: bold;">Unavailable</span>'
                )
            elif sample_fee == 0:
                return format_html(
                    '<span style="color: green; font-weight: bold;">Free</span>'
                )
            else:
                return f"TZS {sample_fee:,.0f}"
        return "N/A"
    fee_display.short_description = 'Sample Fee'
    
    def estimated_time_display(self, obj):
        if obj.estimated_delivery_time:
            return f"{obj.estimated_delivery_time} min"
        return "-"
    estimated_time_display.short_description = 'Est. Time'
    
    def save_model(self, request, obj, form, change):
        """Custom save logic for zone"""
        # Calculate center point from boundary if not set
        if obj.boundary and not obj.center_point:
            obj.center_point = obj.boundary.centroid
        
        super().save_model(request, obj, form, change)
        
        # Update all addresses in this zone
        if obj.boundary:
            from django.contrib.gis.geos import Point
            addresses = CustomerAddress.objects.filter(
                market=obj.market,
                location_point__isnull=False
            )
            
            for address in addresses:
                if obj.boundary.contains(address.location_point):
                    address.delivery_zone = obj
                    address.save()


@admin.register(CustomerAddress)
class CustomerAddressAdmin(LeafletGeoAdmin):
    list_display = [
        'customer_link',
        'market_link',
        'label',
        'area_display',
        'zone_display',
        'distance_display',
        'fee_display',
        'time_display',
        'is_default',
        'is_verified',
        'is_active'
    ]
    
    list_filter = [
        'market',
        'delivery_zone',
        'is_default',
        'is_verified',
        'is_active',
        'region',
        'district'
    ]
    
    search_fields = [
        'customer__phone_number',
        'customer__email',
        'label',
        'street_address',
        'area',
        'ward',
        'recipient_name',
        'recipient_phone'
    ]
    
    list_select_related = ['customer', 'market', 'delivery_zone']
    autocomplete_fields = ['customer', 'market', 'delivery_zone']
    readonly_fields = [
        'distance_from_market',
        'estimated_delivery_fee',
        'estimated_delivery_time',
        'location_point',
        'created_at',
        'updated_at'
    ]
    
    # Leaflet settings for address admin
    settings = {
        'DEFAULT_CENTER': (-6.3690, 34.8888),
        'DEFAULT_ZOOM': 12,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
        'TILES': [('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            'attribution': '&copy; OpenStreetMap contributors'
        })],
    }
    
    fieldsets = (
        ('Customer & Market', {
            'fields': ('customer', 'market', 'delivery_zone')
        }),
        ('Address Details', {
            'fields': (
                'label',
                'street_address',
                'landmark',
                'area',
                'ward',
                'district',
                'region'
            )
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'location_point'),
            'description': 'Enter coordinates or click on map'
        }),
        ('Contact Information', {
            'fields': (
                'recipient_name',
                'recipient_phone',
                'additional_notes'
            )
        }),
        ('Calculated Fields', {
            'fields': (
                'distance_from_market',
                'estimated_delivery_fee',
                'estimated_delivery_time'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'is_default',
                'is_verified',
                'is_active'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}<br><small>{}</small></a>',
            url,
            obj.customer.get_full_name() or obj.customer.phone_number,
            obj.customer.phone_number
        )
    customer_link.short_description = 'Customer'
    customer_link.admin_order_field = 'customer__phone_number'
    
    def market_link(self, obj):
        url = reverse('admin:markets_market_change', args=[obj.market.id])
        return format_html('<a href="{}">{}</a>', url, obj.market.name)
    market_link.short_description = 'Market'
    
    def area_display(self, obj):
        return obj.area or obj.ward or "-"
    area_display.short_description = 'Area'
    
    def zone_display(self, obj):
        if obj.delivery_zone:
            colors = {
                'standard': 'blue',
                'fixed': 'green',
                'free': 'orange',
                'surcharge': 'red',
                'unavailable': 'gray'
            }
            color = colors.get(obj.delivery_zone.zone_type, 'black')
            return format_html(
                '<span style="color: {};"><strong>{}</strong><br><small>{}</small></span>',
                color,
                obj.delivery_zone.name,
                obj.delivery_zone.get_zone_type_display()
            )
        return format_html('<span style="color: gray;">Not assigned</span>')
    zone_display.short_description = 'Delivery Zone'
    
    def distance_display(self, obj):
        if obj.distance_from_market:
            return f"{obj.distance_from_market} km"
        return "-"
    distance_display.short_description = 'Distance'
    
    def fee_display(self, obj):
        if obj.estimated_delivery_fee is None:
            return format_html('<span style="color: red;">Unavailable</span>')
        elif obj.estimated_delivery_fee == 0:
            return format_html('<span style="color: green;">Free</span>')
        else:
            return f"TZS {obj.estimated_delivery_fee:,.0f}"
    fee_display.short_description = 'Est. Fee'
    
    def time_display(self, obj):
        if obj.estimated_delivery_time:
            return f"{obj.estimated_delivery_time} min"
        return "-"
    time_display.short_description = 'Est. Time'
    
    actions = ['verify_addresses', 'unverify_addresses', 'recalculate_zones']
    
    def verify_addresses(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} addresses verified.')
    verify_addresses.short_description = "Mark selected addresses as verified"
    
    def unverify_addresses(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} addresses unverified.')
    unverify_addresses.short_description = "Mark selected addresses as unverified"
    
    def recalculate_zones(self, request, queryset):
        for address in queryset:
            address.update_zone_and_fee()
        self.message_user(request, f'Zones and fees recalculated for {queryset.count()} addresses.')
    recalculate_zones.short_description = "Recalculate delivery zones and fees"
    
    def save_model(self, request, obj, form, change):
        """Update zone and calculations on save"""
        obj.update_zone_and_fee()
        super().save_model(request, obj, form, change)



admin.site.register(DeliveryFeeConfig)