from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField
import uuid

class GlobalSetting(models.Model):
    """Global settings that can be configured through admin"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('decimal', 'Decimal'),
            ('boolean', 'Boolean'),
            ('json', 'JSON')
        ],
        default='string'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'global_settings'
        verbose_name = 'Global Setting'
        verbose_name_plural = 'Global Settings'
    
    def __str__(self):
        return f"{self.key} = {self.value}"

class Category(models.Model):
    """Product categories with configurable profit percentages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    # Configurable profit percentage
    profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default profit percentage for this category (%)"
    )
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )
    
    # Category can be linked to market zones
    typical_market_zones = models.ManyToManyField(
        'markets.MarketZone', 
        blank=True,
        related_name='categories',
        help_text="Market zones where this category is typically found"
    )
    
    is_active = models.BooleanField(default=True)
    image = CloudinaryField(
        'category_image',
        folder='ai_mall/categories/',
        null=True,
        blank=True,
        transformation=[
            {'width': 400, 'height': 300, 'crop': 'fill'},
            {'quality': 'auto:good'},
        ]
    )
    
    sort_order = models.IntegerField(default=0, help_text="Display order in listings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def has_subcategories(self):
        return self.subcategories.filter(is_active=True).exists()

class MeasurementUnitType(models.Model):
    """Types of measurement units (Weight, Volume, Length, Count, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    base_unit_name = models.CharField(max_length=50, help_text="e.g., gram, milliliter, meter")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'measurement_unit_types'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name

class MeasurementUnit(models.Model):
    """Configurable measurement units (kilo, nusu, robo, litre, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_type = models.ForeignKey(MeasurementUnitType, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10, help_text="e.g., kg, L, m, pcs")
    conversion_factor = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        default=1.0,
        help_text="Conversion factor to base unit (e.g., 1000 for kg to grams)"
    )
    is_base_unit = models.BooleanField(default=False, help_text="Is this the base unit for calculations?")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'measurement_units'
        unique_together = ['unit_type', 'name']
        ordering = ['unit_type', 'sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.symbol}) - {self.unit_type.name}"

class ProductTemplate(models.Model):
    """Base product template - independent of vendors"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    # Measurement Configuration
    primary_unit_type = models.ForeignKey(
        MeasurementUnitType, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    available_units = models.ManyToManyField(
        MeasurementUnit,
        related_name='products',
        help_text="Measurement units available for this product"
    )
    
    # Images
    main_image = CloudinaryField(
        'product_image',
        folder='ai_mall/products/',
        null=True,
        blank=True,
        transformation=[
            {'width': 500, 'height': 500, 'crop': 'fill'},
            {'quality': 'auto:good'},
        ]
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # AI Features
    search_keywords = models.TextField(blank=True, help_text="Comma-separated keywords for search and AI recommendations")
    similar_products = models.ManyToManyField(
        'self',
        symmetrical=True,
        blank=True,
        help_text="Manually define similar products for AI recommendations"
    )
    
    # Metadata
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_templates'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['name', 'category']),
            models.Index(fields=['is_active', 'is_verified']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"
class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_template = models.ForeignKey(ProductTemplate, on_delete=models.CASCADE, related_name='variants')
    vendor = models.ForeignKey('accounts.Vendor', on_delete=models.CASCADE, related_name='products')
    market_zone = models.ForeignKey('markets.MarketZone', on_delete=models.CASCADE, related_name='products')
    
    custom_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Custom profit % (overrides category)"
    )
    
    # ✅ Stock fields REMOVED

    # Quality Information
    quality_grade = models.CharField(
        max_length=50, 
        blank=True,
        choices=[
            ('premium', 'Premium'),
            ('standard', 'Standard'),
            ('economy', 'Economy'),
        ]
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variants'
        unique_together = ['product_template', 'vendor', 'market_zone']
        ordering = ['product_template__name', 'vendor__business_name']
    
    def __str__(self):
        return f"{self.product_template.name} - {self.vendor.business_name} - {self.market_zone.name}"
    
    @property
    def effective_profit_percentage(self):
        return self.custom_profit_percentage or self.product_template.category.profit_percentage
    
    
# products/models.py

class UnitPrice(models.Model):
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='unit_prices')
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE)
    
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    # ✅ Auto-calculated, but stored for performance
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'unit_prices'
        unique_together = ['product_variant', 'unit']

    def __str__(self):
        return f"{self.product_variant} - {self.unit.name}: Tsh {self.selling_price}"

    def save(self, *args, **kwargs):
        # 🔒 Auto-calculate selling_price from cost + profit %
        profit_pct = self.product_variant.effective_profit_percentage  # Decimal
        multiplier = Decimal('1.00') + (profit_pct / Decimal('100.00'))
        self.selling_price = (self.cost_price * multiplier).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class ProductAddon(models.Model):
    """Configurable product addons (e.g., peeling, cutting, delivery)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    addon_type = models.CharField(
        max_length=50,
        choices=[
            ('preparation', 'Preparation'),
            ('service', 'Service'),
            ('packaging', 'Packaging'),
            ('delivery', 'Delivery'),
        ]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_addons'
        ordering = ['addon_type', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.get_addon_type_display()}"

class ProductAddonMapping(models.Model):
    """Which addons are available for which products"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='available_addons')
    addon = models.ForeignKey(ProductAddon, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_addon_mappings'
        unique_together = ['product_variant', 'addon']
    
    def __str__(self):
        return f"{self.product_variant} - {self.addon}"

class ProductImage(models.Model):
    """Additional images for products"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_template = models.ForeignKey(ProductTemplate, on_delete=models.CASCADE, related_name='additional_images')
    image = CloudinaryField(
        'product_image',
        folder='ai_mall/products/additional/',
        transformation=[
            {'width': 500, 'height': 500, 'crop': 'fill'},
            {'quality': 'auto:good'},
        ]
    )
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product_template.name}"


class FavoriteItem(models.Model):
    """Customer's favorite products (wishlist)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(ProductTemplate, on_delete=models.CASCADE, related_name='favorited_by')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'favorite_items'
        unique_together = [['customer', 'product']]
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.customer.phone_number} - {self.product.name}"