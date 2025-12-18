# location/models.py
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError


class DeliveryFeeConfig(models.Model):
    """Configuration for delivery fee calculations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Configuration name")
    
    # Distance calculation method
    CALCULATION_CHOICES = [
        ('haversine', 'Haversine (Accurate)'),
        ('euclidean', 'Euclidean (Fast)'),
        ('manhattan', 'Manhattan (City blocks)'),
    ]
    
    calculation_method = models.CharField(
        max_length=20,
        choices=CALCULATION_CHOICES,
        default='haversine',
        help_text="Method for distance calculation"
    )
    
    # Pricing tiers
    base_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1000.00'),
        validators=[MinValueValidator(0)],
        help_text="Minimum delivery fee"
    )
    
    per_km_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('500.00'),
        validators=[MinValueValidator(0)],
        help_text="Fee per kilometer"
    )
    
    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('50000.00'),
        validators=[MinValueValidator(0)],
        help_text="Order amount for free delivery"
    )
    
    max_delivery_distance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(0)],
        help_text="Maximum delivery distance in km"
    )
    
    surcharge_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage surcharge for remote areas (%)"
    )

    # Tiered (bucket) pricing - admin can configure a minimum distance step and fee per step
    distance_step_km = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal('0.1'),
        validators=[MinValueValidator(0.001)],
        help_text="Distance step in kilometers (e.g., 0.1 for 100m)"
    )

    fee_per_step = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('200.00'),
        validators=[MinValueValidator(0)],
        help_text="Fee for each distance step"
    )
    
    # Timing
    delivery_time_estimate_per_km = models.IntegerField(
        default=3,
        validators=[MinValueValidator(0)],
        help_text="Estimated minutes per km"
    )
    
    min_delivery_time = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0)],
        help_text="Minimum delivery time in minutes"
    )
    
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_fee_configs'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({'Default' if self.is_default else 'Custom'})"
    
    def clean(self):
        """Ensure only one default configuration"""
        if self.is_default:
            DeliveryFeeConfig.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_active_config():
        """Get active configuration (default or first active)"""
        try:
            config = DeliveryFeeConfig.objects.get(is_default=True, is_active=True)
        except DeliveryFeeConfig.DoesNotExist:
            config = DeliveryFeeConfig.objects.filter(is_active=True).first()

        # If there is no active config in the database, return a sensible
        # in-memory default so the API and admin pages behave predictably.
        # Default rule: first 1 km is TZS 2000 (admin can override this by
        # creating a DeliveryFeeConfig in the admin UI).
        if not config:
            return DeliveryFeeConfig(
                name='Default (fallback)',
                calculation_method='haversine',
                base_fee=Decimal('2000.00'),
                per_km_rate=Decimal('0.00'),
                free_delivery_threshold=Decimal('50000.00'),
                max_delivery_distance=Decimal('50.00'),
                surcharge_percent=Decimal('0.00'),
                distance_step_km=Decimal('1.000'),
                fee_per_step=Decimal('2000.00'),
                delivery_time_estimate_per_km=3,
                min_delivery_time=30,
                is_active=True,
                is_default=True,
            )

        return config


class DeliveryZone(models.Model):
    """Delivery zones with pricing rules"""
    ZONE_TYPE_CHOICES = [
        ('standard', 'Standard (Distance-based)'),
        ('fixed', 'Fixed Price'),
        ('free', 'Free Delivery'),
        ('surcharge', 'Surcharge Area'),
        ('unavailable', 'Delivery Unavailable'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='delivery_zones')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Zone type determines pricing strategy
    zone_type = models.CharField(
        max_length=20,
        choices=ZONE_TYPE_CHOICES,
        default='standard',
        help_text="Type of delivery zone"
    )
    
    # For fixed price zones
    fixed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Fixed delivery price (for fixed price zones)"
    )
    
    # For surcharge zones
    surcharge_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(200)],
        help_text="Extra percentage charge (for surcharge zones)"
    )
    
    # GIS polygon for zone boundaries
    boundary = gis_models.PolygonField(
        null=True,
        blank=True,
        srid=4326,
        help_text="Zone boundary polygon (draw on map)"
    )
    
    # Center point for distance calculation
    center_point = gis_models.PointField(
        null=True,
        blank=True,
        srid=4326,
        help_text="Center point of the zone"
    )
    
    # Distance from market
    distance_from_market = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Distance from market in km"
    )
    
    # Estimated delivery time
    estimated_delivery_time = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated delivery time in minutes"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Priority (1=highest, 10=lowest)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_zones'
        unique_together = ['market', 'name']
        ordering = ['market', 'priority', 'name']
        indexes = [
            models.Index(fields=['market', 'is_active']),
            models.Index(fields=['zone_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.market.name} - {self.name} ({self.get_zone_type_display()})"
    
    def clean(self):
        """Validate zone data"""
        if self.zone_type == 'fixed' and not self.fixed_price:
            raise ValidationError("Fixed price zones require a fixed price")
        if self.zone_type == 'surcharge' and not self.surcharge_percent:
            raise ValidationError("Surcharge zones require a surcharge percentage")
    
    def save(self, *args, **kwargs):
        self.clean()
        
        # Calculate distance from market if not set
        if self.market.geo_location and self.center_point and not self.distance_from_market:
            self.distance_from_market = self._calculate_distance(
                self.market.geo_location,
                self.center_point
            )
        
        # Calculate estimated delivery time
        config = DeliveryFeeConfig.get_active_config()
        if config and self.distance_from_market:
            time_per_km = config.delivery_time_estimate_per_km
            min_time = config.min_delivery_time
            estimated = int(self.distance_from_market * time_per_km)
            self.estimated_delivery_time = max(min_time, estimated)
        
        super().save(*args, **kwargs)
    
    def _calculate_distance(self, point1, point2):
        """Calculate distance between two points in km"""
        from math import radians, sin, cos, sqrt, atan2
        
        # Convert to lat/lng
        lat1 = radians(point1.y)
        lon1 = radians(point1.x)
        lat2 = radians(point2.y)
        lon2 = radians(point2.x)
        
        # Haversine formula
        R = 6371  # Earth radius in km
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return Decimal(str(distance))
    
    def calculate_delivery_fee(self, customer_point=None, order_amount=Decimal('0.00')):
        """Calculate delivery fee based on zone type and location"""
        config = DeliveryFeeConfig.get_active_config()
        if not config:
            return Decimal('0.00')
        
        # Free delivery for orders above threshold
        if order_amount >= config.free_delivery_threshold and self.zone_type != 'unavailable':
            return Decimal('0.00')
        
        # Check maximum distance
        if customer_point and self.distance_from_market:
            distance = self._calculate_distance(self.market.geo_location, customer_point)
            if distance > config.max_delivery_distance:
                return None  # Delivery not available
        
        # Calculate based on zone type
        if self.zone_type == 'fixed':
            return self.fixed_price
        elif self.zone_type == 'free':
            return Decimal('0.00')
        elif self.zone_type == 'unavailable':
            return None  # Delivery not available
        elif self.zone_type == 'surcharge':
            base_fee = self._calculate_distance_fee(customer_point, config)
            surcharge = base_fee * (self.surcharge_percent / 100)
            return base_fee + surcharge
        else:  # standard
            return self._calculate_distance_fee(customer_point, config)
    
    def _calculate_distance_fee(self, customer_point, config):
        """Calculate distance-based fee"""
        if not customer_point or not self.market.geo_location:
            return config.base_fee
        
        distance = self._calculate_distance(self.market.geo_location, customer_point)
        calculated_fee = config.base_fee + (distance * config.per_km_rate)
        return max(config.base_fee, calculated_fee)
    
    def contains_location(self, latitude, longitude):
        """Check if a location is within this zone's boundary"""
        if not self.boundary:
            return False
        
        point = Point(float(longitude), float(latitude), srid=4326)
        return self.boundary.contains(point)


class DeliveryTimeSlot(models.Model):
    """Delivery time slots"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g., Morning (8AM-12PM), Afternoon (12PM-4PM)")
    cut_off_time = models.TimeField(help_text="Last order time for this slot")
    delivery_start_time = models.TimeField(help_text="Delivery window start")
    delivery_end_time = models.TimeField(help_text="Delivery window end")
    
    # Slot restrictions
    max_orders = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        help_text="Maximum orders per slot"
    )
    
    delivery_fee_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(0.5), MaxValueValidator(3.0)],
        help_text="Fee multiplier for this time slot"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_time_slots'
        ordering = ['delivery_start_time']
    
    def __str__(self):
        return f"{self.name} ({self.delivery_start_time} - {self.delivery_end_time})"
    
    def get_available_slots(date):
        """Get available slots for a given date"""
        from django.utils import timezone
        from datetime import datetime, time
        
        now = timezone.now()
        current_time = now.time()
        
        slots = DeliveryTimeSlot.objects.filter(is_active=True)
        available_slots = []
        
        for slot in slots:
            # Check if slot is still available for today
            if now.date() == date.date():
                if current_time < slot.cut_off_time:
                    available_slots.append(slot)
            else:
                available_slots.append(slot)
        
        return available_slots


class CustomerAddress(models.Model):
    """Customer delivery addresses with zone mapping"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='addresses')
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='customer_addresses')
    
    # Address details
    label = models.CharField(max_length=100, help_text="e.g., Home, Office, Shop")
    street_address = models.TextField()
    landmark = models.CharField(max_length=255, blank=True, help_text="Nearby landmark")
    area = models.CharField(max_length=255, blank=True, help_text="Area/Neighborhood")
    ward = models.CharField(max_length=255, blank=True, help_text="Ward")
    district = models.CharField(max_length=255, blank=True, help_text="District")
    region = models.CharField(max_length=255, blank=True, help_text="Region")
    
    # Location coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=False, default=0.0)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=False, default=0.0)
    
    # GIS point
    location_point = gis_models.PointField(
        null=True,
        blank=True,
        srid=4326,
        help_text="Geographic point for this address"
    )
    
    # Zone assignment (auto-detected)
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_addresses'
    )
    
    # Calculated fields
    distance_from_market = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance from market in km"
    )
    
    estimated_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated delivery fee"
    )
    
    estimated_delivery_time = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated delivery time in minutes"
    )
    
    # Contact info
    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=13)
    additional_notes = models.TextField(blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False, help_text="Address has been verified")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_addresses'
        ordering = ['-is_default', 'label']
        indexes = [
            models.Index(fields=['customer', 'market', 'is_default']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.customer.phone_number} - {self.label} ({self.area})"
    
    def clean(self):
        """Validate and auto-assign delivery zone"""
        # Ensure only one default address per customer per market
        if self.is_default:
            CustomerAddress.objects.filter(
                customer=self.customer,
                market=self.market,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        # Create location point from coordinates
        if self.latitude and self.longitude:
            self.location_point = Point(float(self.longitude), float(self.latitude), srid=4326)
        
        # Auto-detect delivery zone
        if self.location_point and self.market:
            self.delivery_zone = self._detect_delivery_zone()
            
            # Calculate distance and estimated fee
            if self.delivery_zone:
                self.distance_from_market = self.delivery_zone._calculate_distance(
                    self.market.geo_location,
                    self.location_point
                )
                self.estimated_delivery_fee = self.delivery_zone.calculate_delivery_fee(
                    self.location_point
                )
                self.estimated_delivery_time = self.delivery_zone.estimated_delivery_time
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def _detect_delivery_zone(self):
        """Find the appropriate delivery zone for this address"""
        if not self.location_point or not self.market:
            return None
        
        # Try to find zones that contain this point
        zones = DeliveryZone.objects.filter(
            market=self.market,
            is_active=True,
            boundary__contains=self.location_point
        ).order_by('priority')
        
        if zones.exists():
            return zones.first()
        
        # If no zone contains the point, find nearest zone
        zones = DeliveryZone.objects.filter(
            market=self.market,
            is_active=True,
            center_point__isnull=False
        )
        
        if zones.exists():
            # Calculate distance to each zone's center point
            nearest_zone = None
            min_distance = float('inf')
            
            for zone in zones:
                distance = zone._calculate_distance(
                    self.location_point,
                    zone.center_point
                )
                if distance < min_distance:
                    min_distance = distance
                    nearest_zone = zone
            
            return nearest_zone
        
        return None
    
    def update_zone_and_fee(self):
        """Update zone assignment and fee calculation"""
        self.clean()
        self.save(update_fields=[
            'delivery_zone',
            'distance_from_market',
            'estimated_delivery_fee',
            'estimated_delivery_time',
            'location_point',
            'updated_at'
        ])
    
    def get_formatted_address(self):
        """Get formatted address string"""
        parts = []
        if self.street_address:
            parts.append(self.street_address)
        if self.landmark:
            parts.append(f"Near {self.landmark}")
        if self.area:
            parts.append(self.area)
        if self.ward:
            parts.append(f"Ward: {self.ward}")
        if self.district:
            parts.append(f"District: {self.district}")
        if self.region:
            parts.append(f"Region: {self.region}")
        return ", ".join(parts)
    
    def get_delivery_estimate(self):
        """Get delivery estimate string"""
        if not self.estimated_delivery_fee or not self.estimated_delivery_time:
            return "Delivery estimate not available"
        
        fee = f"TZS {self.estimated_delivery_fee:,.0f}"
        time = f"{self.estimated_delivery_time} mins"
        
        if self.delivery_zone and self.delivery_zone.zone_type == 'free':
            return f"Free delivery • {time}"
        elif self.delivery_zone and self.delivery_zone.zone_type == 'unavailable':
            return "Delivery not available"
        
        return f"{fee} • {time}"