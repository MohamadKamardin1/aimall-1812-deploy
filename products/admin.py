from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from django.contrib import messages
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from .models import (
    GlobalSetting, Category, MeasurementUnitType, MeasurementUnit,
    ProductTemplate, ProductVariant, UnitPrice, ProductAddon,
    ProductAddonMapping, ProductImage
)

# ============ FORM CLASSES ============

class UnitPriceForm(forms.ModelForm):
    class Meta:
        model = UnitPrice
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')
        
        # If selling_price is not provided but cost_price is, calculate it
        if cost_price and not selling_price:
            product_variant = cleaned_data.get('product_variant')
            if product_variant:
                profit_percentage = product_variant.effective_profit_percentage
                selling_price = cost_price + (cost_price * profit_percentage / Decimal('100'))
                cleaned_data['selling_price'] = selling_price
        
        return cleaned_data

# ============ INLINE ADMIN CLASSES ============

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'caption', 'sort_order', 'is_active']

class MeasurementUnitInline(admin.TabularInline):
    model = MeasurementUnit
    extra = 1
    fields = ['name', 'symbol', 'conversion_factor', 'is_base_unit', 'is_active']

class ProductAddonMappingInline(admin.TabularInline):
    model = ProductAddonMapping
    extra = 1
    fields = ['addon', 'is_active']

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ['vendor', 'market_zone', 'custom_profit_percentage', 'quality_grade', 'is_approved', 'is_active']

# ============ CUSTOM FILTERS ============

class CategoryStatusFilter(admin.SimpleListFilter):
    title = 'Category Status'
    parameter_name = 'category_status'
    
    def lookups(self, request, model_admin):
        return (
            ('with_subcategories', 'With Subcategories'),
            ('without_subcategories', 'Without Subcategories'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'with_subcategories':
            return queryset.filter(subcategories__isnull=False).distinct()
        elif self.value() == 'without_subcategories':
            return queryset.filter(subcategories__isnull=True)

class ProductTemplateStatusFilter(admin.SimpleListFilter):
    title = 'Template Status'
    parameter_name = 'template_status'
    
    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified Templates'),
            ('unverified', 'Unverified Templates'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(is_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(is_verified=False)

class ProductVariantStatusFilter(admin.SimpleListFilter):
    title = 'Variant Status'
    parameter_name = 'variant_status'
    
    def lookups(self, request, model_admin):
        return (
            ('approved', 'Approved Variants'),
            ('pending', 'Pending Approval'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(is_approved=True)
        elif self.value() == 'pending':
            return queryset.filter(is_approved=False)

class QualityGradeFilter(admin.SimpleListFilter):
    title = 'Quality Grade'
    parameter_name = 'quality_grade'
    
    def lookups(self, request, model_admin):
        return [
            ('premium', 'Premium'),
            ('standard', 'Standard'),
            ('economy', 'Economy'),
        ]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(quality_grade=self.value())

# ============ MODEL ADMIN CLASSES ============

@admin.register(GlobalSetting)
class GlobalSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'formatted_value', 'data_type', 'is_active']
    list_filter = ['data_type', 'is_active']
    search_fields = ['key', 'description']
    
    def formatted_value(self, obj):
        value = obj.value
        if len(value) > 50:
            return value[:50] + '...'
        return value
    formatted_value.short_description = 'Value'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'profit_percentage', 'products_count', 'is_active']
    list_filter = [CategoryStatusFilter, 'is_active']
    search_fields = ['name', 'description']
    filter_horizontal = ['typical_market_zones']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Products'

    def subcategories_count(self, obj):
        return obj.subcategories.count()
    subcategories_count.short_description = 'Subcategories'

@admin.register(MeasurementUnitType)
class MeasurementUnitTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_unit_name', 'units_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    inlines = [MeasurementUnitInline]
    
    def units_count(self, obj):
        return obj.units.count()
    units_count.short_description = 'Units'

@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'unit_type', 'conversion_factor', 'is_base_unit', 'is_active']
    list_filter = ['unit_type', 'is_base_unit', 'is_active']
    search_fields = ['name', 'symbol']
    list_select_related = ['unit_type']

@admin.register(ProductTemplate)
class ProductTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'primary_unit_type', 'variants_count', 'is_verified', 'is_active']
    list_filter = [ProductTemplateStatusFilter, 'category', 'primary_unit_type', 'is_verified', 'is_active']
    search_fields = ['name', 'description', 'search_keywords']
    filter_horizontal = ['available_units', 'similar_products']
    inlines = [ProductImageInline, ProductVariantInline]
    
    def variants_count(self, obj):
        return obj.variants.count()
    variants_count.short_description = 'Variants'
from django.contrib import admin, messages
from .models import ProductVariant

# Assuming you have these filters defined elsewhere — keep them if they exist
# from .admin_filters import ProductVariantStatusFilter, QualityGradeFilter

@admin.register(UnitPrice)
class UnitPriceAdmin(admin.ModelAdmin):
    # ❌ No custom form — selling_price is auto-calculated
    list_display = [
        'product_variant', 
        'unit', 
        'cost_price', 
        'selling_price', 
        'profit_margin',
        'is_active'
    ]
    list_filter = ['is_active', 'unit__unit_type']
    search_fields = [
        'product_variant__product_template__name',
        'product_variant__vendor__business_name'
    ]
    list_select_related = ['product_variant', 'unit']
    
    # ✅ Make fields read-only
    readonly_fields = ['selling_price', 'profit_margin', 'created_at', 'updated_at']
    fields = [
        'product_variant',
        'unit',
        'cost_price',
        'selling_price',      # read-only
        'profit_margin',      # read-only
        'is_active',
        'created_at',
        'updated_at'
    ]

    def profit_margin(self, obj):
        if obj.cost_price and obj.cost_price > 0:
            margin = ((obj.selling_price - obj.cost_price) / obj.cost_price) * 100
            return f"{margin:.1f}%"
        return "N/A"
    profit_margin.short_description = "Margin %"
    profit_margin.admin_order_field = 'selling_price'  # Optional: allows sorting

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product_variant__product_template',
            'product_variant__vendor',
            'unit'
        )

    # 🔒 Optional: Enforce vendor privacy in admin (if needed)
    # def has_view_permission(self, request, obj=None):
    #     return super().has_view_permission(request, obj)
    #
    # def has_change_permission(self, request, obj=None):
    #     if obj and obj.product_variant.vendor.user != request.user:
    #         return False
    #     return super().has_change_permission(request, obj)
@admin.register(ProductAddon)
class ProductAddonAdmin(admin.ModelAdmin):
    list_display = ['name', 'addon_type', 'price', 'mappings_count', 'is_active']
    list_filter = ['addon_type', 'is_active']
    search_fields = ['name', 'description']
    
    def mappings_count(self, obj):
        return obj.productaddonmapping_set.count()
    mappings_count.short_description = 'Used In'

@admin.register(ProductAddonMapping)
class ProductAddonMappingAdmin(admin.ModelAdmin):
    list_display = ['product_variant', 'addon', 'is_active']
    list_filter = ['is_active', 'addon__addon_type']
    search_fields = [
        'product_variant__product_template__name',
        'addon__name'
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product_variant__product_template',
            'addon'
        )

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product_template', 'caption', 'image_preview', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['product_template__name', 'caption']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"


# products/admin.py

from django import forms
from .models import UnitPrice

class UnitPriceAdminForm(forms.ModelForm):
    class Meta:
        model = UnitPrice
        fields = ['product_variant', 'unit', 'cost_price', 'is_active']  # ❌ No selling_price
        # OR use exclude:
        # exclude = ['selling_price']



from django.contrib import admin
from .models import UnitPrice, ProductVariant

class UnitPriceInline(admin.TabularInline):
    model = UnitPrice
    form = UnitPriceAdminForm
    extra = 0
    readonly_fields = ['selling_price_display']  # Optional: show calculated value
    fields = ['unit', 'cost_price', 'selling_price_display', 'is_active']

    def selling_price_display(self, obj):
        return f"Tsh {obj.selling_price}" if obj.selling_price else "—"
    selling_price_display.short_description = "Selling Price (Auto)"




@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'product_template', 
        'vendor', 
        'market_zone', 
        'effective_profit_percentage_display',
        'quality_grade', 
        'is_approved', 
        'is_active'
    ]
    list_filter = [
        # ProductVariantStatusFilter, 
        # QualityGradeFilter,
        'is_approved', 
        'is_active',
        'product_template__category'
    ]
    search_fields = [
        'product_template__name', 
        'vendor__business_name',
        'market_zone__name'
    ]
    readonly_fields = ['effective_profit_percentage_display']
    inlines = [UnitPriceInline]  # Include addon inline if you have it working

    def effective_profit_percentage_display(self, obj):
        return f"{obj.effective_profit_percentage}%"
    effective_profit_percentage_display.short_description = "Profit %"

    # ✅ Keep actions
    actions = ['approve_variants', 'unapprove_variants', 'activate_variants', 'deactivate_variants']
    
    def approve_variants(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'Approved {updated} variants.', messages.SUCCESS)
    approve_variants.short_description = "Approve selected variants"
    
    def unapprove_variants(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'Unapproved {updated} variants.', messages.WARNING)
    unapprove_variants.short_description = "Unapprove selected variants"
    
    def activate_variants(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} variants.', messages.SUCCESS)
    activate_variants.short_description = "Activate selected variants"
    
    def deactivate_variants(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} variants.', messages.WARNING)
    deactivate_variants.short_description = "Deactivate selected variants"