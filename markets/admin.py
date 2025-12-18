# admin.py
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from leaflet.admin import LeafletGeoAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import folium
from .models import Market, MarketDay, MarketZone


class MarketDayInline(admin.TabularInline):
    """Inline for adding/removing market days from Market"""
    model = Market.market_days.through
    extra = 1
    verbose_name = "Market Day"
    verbose_name_plural = "Market Days"
    can_delete = True


class MarketZoneInline(admin.TabularInline):
    """Inline for managing market zones"""
    model = MarketZone
    extra = 1
    fields = ['name', 'description', 'zone_type', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('market')


@admin.register(Market)
class MarketAdmin(LeafletGeoAdmin):
    # List display configuration
    list_display = [
        'name', 
        'location_preview', 
        'contact_phone', 
        'market_days_list',
        'is_active', 
        'created_at'
    ]
    
    list_filter = [
        'is_active', 
        'market_days',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'name',
        'description',
        'location',
        'address',
        'contact_phone'
    ]
    
    list_per_page = 20
    list_select_related = True
    list_editable = ['is_active']
    
    # Inlines
    inlines = [MarketDayInline, MarketZoneInline]
    
    # Fieldsets for detailed edit form
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'description',
                'contact_phone',
                'is_active'
            ),
            'classes': ('wide',)
        }),
        ('Operating Hours', {
            'fields': (
                'opening_time',
                'closing_time',
            ),
            'classes': ('collapse', 'wide')
        }),
        ('Location Information', {
            'fields': (
                'address',
                'location',
            ),
            'description': 'Text description of the market location'
        }),
        ('Map Location', {
            'fields': ('geo_location',),
            'description': mark_safe(
                '<div class="help">'
                '<strong>Instructions:</strong> Click on the map to set the market location. '
                'You can also search for a location using the search box in the map. '
                'Latitude and Longitude will be automatically updated.'
                '</div>'
            ),
            'classes': ('wide',)
        }),
        ('Coordinates (Auto-filled)', {
            'fields': (
                'latitude',
                'longitude',
            ),
            'classes': ('collapse',),
            'description': 'These fields are automatically populated from the map selection'
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'latitude',
        'longitude'
    ]
    
    # Leaflet map configuration
    settings_overrides = {
        'DEFAULT_CENTER': (-6.193764, 39.239191), # Default center for Tanzania
        'DEFAULT_ZOOM': 10,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
        'TILES': [('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        })],
        'RESET_VIEW': False,
        'SCALE': 'both',
        'ATTRIBUTION_PREFIX': 'Market Locations Management',
    }
    
    # Custom actions
    actions = ['activate_markets', 'deactivate_markets']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('market_days', 'zones')
    
    def location_preview(self, obj):
        """Display location with map link in list view"""
        if obj.latitude and obj.longitude:
            # Create a link to open Google Maps
            google_maps_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<div style="white-space: nowrap;">'
                '<strong>{}</strong><br>'
                '<small>{}</small><br>'
                '<a href="{}" target="_blank" style="color: #666;">'
                '<i class="fas fa-map-marker-alt"></i> View on Map'
                '</a>'
                '</div>',
                obj.location or "No location",
                f"Lat: {obj.latitude}, Lng: {obj.longitude}" if obj.latitude else "",
                google_maps_url
            )
        return format_html(
            '<span style="color: #999;"><i class="fas fa-map-marker-alt"></i> No location set</span>'
        )
    
    location_preview.short_description = 'Location'
    location_preview.admin_order_field = 'location'
    
    def market_days_list(self, obj):
        """Display market days in list view"""
        days = obj.market_days.all()
        if days:
            day_list = ', '.join([str(day) for day in days])
            return format_html(
                '<span style="font-size: 12px; background: #e8f4fd; padding: 2px 8px; '
                'border-radius: 12px; border: 1px solid #b6d4fe;">{}</span>',
                day_list
            )
        return format_html(
            '<span style="color: #999; font-size: 12px;">No days set</span>'
        )
    
    market_days_list.short_description = 'Market Days'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form to add CSS classes"""
        form = super().get_form(request, obj, **kwargs)
        
        # Add help text for geo_location field
        form.base_fields['geo_location'].help_text = mark_safe(
            '<div class="help">'
            '<strong>Click on the map to set location.</strong><br>'
            'Use the search box to find specific addresses. '
            'Drag the marker to adjust position.'
            '</div>'
        )
        
        return form
    
    def activate_markets(self, request, queryset):
        """Admin action to activate selected markets"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, 
            f'Successfully activated {updated} market(s).',
            level='success'
        )
    
    activate_markets.short_description = "Activate selected markets"
    
    def deactivate_markets(self, request, queryset):
        """Admin action to deactivate selected markets"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, 
            f'Successfully deactivated {updated} market(s).',
            level='success'
        )
    
    deactivate_markets.short_description = "Deactivate selected markets"
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        # Ensure coordinates are updated from geo_location
        if obj.geo_location:
            obj.latitude = obj.geo_location.y
            obj.longitude = obj.geo_location.x
        
        # Set location if empty
        if not obj.location and obj.address:
            obj.location = obj.address[:255]
        
        super().save_model(request, obj, form, change)
        
        # Add success message
        action = "updated" if change else "created"
        self.message_user(
            request, 
            f'Market "{obj.name}" was successfully {action}.',
            level='success'
        )
    
    def get_changeform_initial_data(self, request):
        """Set initial data for new markets"""
        initial = super().get_changeform_initial_data(request)
        initial['is_active'] = True
        return initial
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add custom context for change view"""
        extra_context = extra_context or {}
        
        # Get the market object
        market = Market.objects.get(id=object_id)
        
        # Add map preview for existing locations
        if market.latitude and market.longitude:
            m = folium.Map(
                location=[market.latitude, market.longitude],
                zoom_start=15,
                width=300,
                height=200,
                tiles='OpenStreetMap'
            )
            folium.Marker(
                [market.latitude, market.longitude],
                popup=market.name,
                tooltip=market.location or market.name,
                icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa')
            ).add_to(m)
            extra_context['map_preview'] = m._repr_html_()
        
        # Add statistics
        extra_context['zone_count'] = market.zones.count()
        
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(MarketDay)
class MarketDayAdmin(admin.ModelAdmin):
    """Admin for MarketDay model"""
    list_display = ['get_day_display', 'market_count', 'is_weekday', 'is_weekend']
    list_filter = ['day']
    search_fields = ['day']
    ordering = ['id']
    
    def get_ordering(self, request):
        return ['id']
    
    def market_count(self, obj):
        """Count how many markets have this day"""
        return obj.markets.count()
    
    market_count.short_description = 'Number of Markets'
    
    def is_weekday(self, obj):
        """Check if this is a weekday"""
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        return obj.day in weekdays
    
    is_weekday.short_description = 'Weekday'
    is_weekday.boolean = True
    
    def is_weekend(self, obj):
        """Check if this is a weekend day"""
        weekends = ['saturday', 'sunday']
        return obj.day in weekends
    
    is_weekend.short_description = 'Weekend'
    is_weekend.boolean = True
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of system-defined market days"""
        return False


@admin.register(MarketZone)
class MarketZoneAdmin(admin.ModelAdmin):
    """Admin for MarketZone model"""
    list_display = [
        'name', 
        'market_link', 
        'zone_type', 
        'is_active', 
        'created_at'
    ]
    
    list_filter = [
        'market',
        'zone_type',
        'is_active',
        'created_at'
    ]
    
    search_fields = [
        'name',
        'description',
        'zone_type',
        'market__name'
    ]
    
    list_per_page = 20
    list_select_related = ['market']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Zone Information', {
            'fields': (
                'market',
                'name',
                'description',
                'zone_type',
                'is_active'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    autocomplete_fields = ['market']
    
    def market_link(self, obj):
        """Create a link to the market admin page"""
        url = reverse('admin:markets_market_change', args=[obj.market.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.market.name
        )
    
    market_link.short_description = 'Market'
    market_link.admin_order_field = 'market__name'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('market')


# Custom Admin Site Configuration
class MarketAdminSite(admin.AdminSite):
    """Custom admin site for markets"""
    site_header = 'Market Management System'
    site_title = 'Market Admin'
    index_title = 'Market Administration'
    
    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)
        
        # Customize the app list
        for app in app_list:
            if app['app_label'] == 'markets':
                app['name'] = 'Market Management'
                app['models'].sort(key=lambda x: x['object_name'])
        
        return app_list


# Optional: Custom admin templates
class MarketAdminTemplate:
    """Custom admin templates for better UX"""
    
    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
                'css/admin_market.css',  # Custom CSS if needed
            )
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js',
            'js/admin_market.js',  # Custom JS if needed
        )


# Register the custom admin site (optional)
# admin_site = MarketAdminSite(name='market_admin')
# admin_site.register(Market, MarketAdmin)
# admin_site.register(MarketDay, MarketDayAdmin)
# admin_site.register(MarketZone, MarketZoneAdmin)

# If you want to use the custom admin site, uncomment above and use:
# urlpatterns = [path('admin/', admin_site.urls),]