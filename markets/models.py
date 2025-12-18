from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.contrib.gis.db import models as gis_models


class Market(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
        ('daily', 'Daily'),
        ('weekdays', 'Weekdays (Mon-Fri)'),
        ('weekends', 'Weekends (Sat-Sun)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=13, blank=True)
    
    # Location fields (for backward compatibility)
    location = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # GIS Point field for map integration
    geo_location = gis_models.PointField(
        null=True,
        blank=True,
        srid=4326,
        help_text="Select location on map"
    )
    
    # Market days - using ManyToMany for flexibility
    market_days = models.ManyToManyField(
        'MarketDay',
        related_name='markets',
        blank=True
    )
    
    # Alternative: If you want simple CharField approach
    # market_days_string = models.CharField(
    #     max_length=200,
    #     blank=True,
    #     help_text="Comma-separated days: Monday, Wednesday, Friday"
    # )
    
    is_active = models.BooleanField(default=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'markets'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.location or 'No location specified'}"
    
    def save(self, *args, **kwargs):
        # Sync geo_location with latitude/longitude if provided
        if self.latitude and self.longitude and not self.geo_location:
            from django.contrib.gis.geos import Point
            self.geo_location = Point(float(self.longitude), float(self.latitude))
        
        # If geo_location exists, update latitude/longitude
        if self.geo_location:
            self.longitude = self.geo_location.x
            self.latitude = self.geo_location.y
        
        super().save(*args, **kwargs)
    
    def get_market_days_display(self):
        """Return formatted market days"""
        days = list(self.market_days.all().values_list('day', flat=True))
        return ', '.join(days) if days else "No days specified"


class MarketDay(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAY_CHOICES, unique=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return self.get_day_display()

class MarketZone(models.Model):
    """Different zones within a market (e.g., Sokoni la Matunda, Sokoni la Samaki)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    zone_type = models.CharField(max_length=100, blank=True, help_text="e.g., Fruits, Vegetables, Fish, Meat")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'market_zones'
        unique_together = ['market', 'name']
        ordering = ['market', 'name']
    
    def __str__(self):
        return f"{self.market.name} - {self.name}"