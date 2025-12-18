from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.core.paginator import Paginator
from django.db import transaction
from .models import (
    Category, MeasurementUnitType, MeasurementUnit, 
    ProductTemplate, ProductVariant, UnitPrice,
    ProductAddon, ProductAddonMapping, GlobalSetting
)
from .serializers import (
    CategorySerializer, CategoryDetailSerializer,
    MeasurementUnitTypeSerializer, MeasurementUnitSerializer,
    ProductTemplateSerializer, ProductTemplateDetailSerializer,
    ProductVariantSerializer, ProductVariantDetailSerializer,
    UnitPriceSerializer, ProductAddonSerializer,
    ProductAddonMappingSerializer, GlobalSettingSerializer
)

# ============ CATEGORY CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def category_list_create(request):
    """
    List all categories or create a new category
    """
    if request.method == 'GET':
        categories = Category.objects.filter(is_active=True)
        include_inactive = request.GET.get('include_inactive', '').lower() == 'true'
        
        if include_inactive:
            categories = Category.objects.all()
        
        # Filter by parent
        parent_id = request.GET.get('parent_id')
        if parent_id:
            if parent_id == 'null':
                categories = categories.filter(parent__isnull=True)
            else:
                categories = categories.filter(parent_id=parent_id)
        
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admin can create categories
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create categories'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(
                CategoryDetailSerializer(category).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def category_detail(request, category_id):
    """
    Retrieve, update or delete a category
    """
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response(
            {'error': 'Category not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = CategoryDetailSerializer(category)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admin can update categories
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update categories'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CategoryDetailSerializer(category).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete categories
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete categories'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete - set inactive
        category.is_active = False
        category.save()
        return Response(
            {'message': 'Category deleted successfully'}, 
            status=status.HTTP_200_OK
        )

# ============ MEASUREMENT UNITS CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def measurement_unit_type_list_create(request):
    """
    List all measurement unit types or create new
    """
    if request.method == 'GET':
        unit_types = MeasurementUnitType.objects.filter(is_active=True)
        serializer = MeasurementUnitTypeSerializer(unit_types, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admin can create unit types
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create measurement unit types'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MeasurementUnitTypeSerializer(data=request.data)
        if serializer.is_valid():
            unit_type = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def measurement_unit_list_create(request):
    """
    List all measurement units or create new
    """
    if request.method == 'GET':
        unit_type_id = request.GET.get('unit_type_id')
        units = MeasurementUnit.objects.filter(is_active=True)
        
        if unit_type_id:
            units = units.filter(unit_type_id=unit_type_id)
        
        serializer = MeasurementUnitSerializer(units, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admin can create units
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create measurement units'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MeasurementUnitSerializer(data=request.data)
        if serializer.is_valid():
            unit = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============ PRODUCT TEMPLATES CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def product_template_list_create(request):
    """
    List all product templates or create new
    """
    if request.method == 'GET':
        # Query parameters
        search = request.GET.get('search', '')
        category_id = request.GET.get('category_id')
        is_active = request.GET.get('is_active', 'true')
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 20)
        
        # Build queryset
        templates = ProductTemplate.objects.all()
        
        if search:
            templates = templates.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(search_keywords__icontains=search)
            )
        
        if category_id:
            templates = templates.filter(category_id=category_id)
        
        if is_active.lower() == 'true':
            templates = templates.filter(is_active=True)
        elif is_active.lower() == 'false':
            templates = templates.filter(is_active=False)
        
        # Pagination
        paginator = Paginator(templates, page_size)
        try:
            templates_page = paginator.page(page)
        except:
            return Response(
                {'error': 'Invalid page number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProductTemplateSerializer(templates_page, many=True)
        
        return Response({
            'data': serializer.data,
            'pagination': {
                'total': paginator.count,
                'pages': paginator.num_pages,
                'current': templates_page.number,
                'has_next': templates_page.has_next(),
                'has_previous': templates_page.has_previous(),
            }
        })
    
    elif request.method == 'POST':
        # Only admin can create product templates
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create product templates'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProductTemplateSerializer(data=request.data)
        if serializer.is_valid():
            template = serializer.save(created_by=request.user)
            return Response(
                ProductTemplateDetailSerializer(template).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def product_template_detail(request, template_id):
    """
    Retrieve, update or delete a product template
    """
    try:
        template = ProductTemplate.objects.get(id=template_id)
    except ProductTemplate.DoesNotExist:
        return Response(
            {'error': 'Product template not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = ProductTemplateDetailSerializer(template)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admin can update templates
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update product templates'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProductTemplateSerializer(template, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProductTemplateDetailSerializer(template).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete templates
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete product templates'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete
        template.is_active = False
        template.save()
        return Response(
            {'message': 'Product template deleted successfully'}, 
            status=status.HTTP_200_OK
        )

# ============ PRODUCT VARIANTS CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def product_variant_list_create(request):
    """
    List all product variants or create new (for vendors)
    """
    if request.method == 'GET':
        # Query parameters
        vendor_id = request.GET.get('vendor_id')
        market_zone_id = request.GET.get('market_zone_id')
        template_id = request.GET.get('template_id')
        is_active = request.GET.get('is_active', 'true')
        
        # Build queryset
        variants = ProductVariant.objects.all()
        
        # Vendor can only see their own variants
        if request.user.user_type == 'vendor':
            variants = variants.filter(vendor__user=request.user)
        elif vendor_id and request.user.user_type == 'admin':
            variants = variants.filter(vendor_id=vendor_id)
        
        if market_zone_id:
            variants = variants.filter(market_zone_id=market_zone_id)
        
        if template_id:
            variants = variants.filter(product_template_id=template_id)
        
        if is_active.lower() == 'true':
            variants = variants.filter(is_active=True)
        elif is_active.lower() == 'false':
            variants = variants.filter(is_active=False)
        
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only vendors can create variants
        if request.user.user_type != 'vendor':
            return Response(
                {'error': 'Only vendors can create product variants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            vendor = request.user.vendor
        except:
            return Response(
                {'error': 'Vendor profile not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = request.data.copy()
        data['vendor'] = vendor.pk
        
        with transaction.atomic():
            serializer = ProductVariantSerializer(data=data)
            if serializer.is_valid():
                variant = serializer.save()
                
                # Automatically create unit prices
                template = variant.product_template
                base_price = variant.selling_price_base
                
                for unit in template.available_units.all():
                    unit_price = base_price * unit.conversion_factor
                    UnitPrice.objects.create(
                        product_variant=variant,
                        unit=unit,
                        price=round(unit_price, 2)
                    )
                
                return Response(
                    ProductVariantDetailSerializer(variant).data,
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def product_variant_detail(request, variant_id):
    """
    Retrieve, update or delete a product variant
    """
    try:
        variant = ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        return Response(
            {'error': 'Product variant not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'vendor' and variant.vendor.user != request.user:
        return Response(
            {'error': 'You can only access your own product variants'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = ProductVariantDetailSerializer(variant)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Check permissions
        if request.user.user_type == 'vendor' and variant.vendor.user != request.user:
            return Response(
                {'error': 'You can only update your own product variants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProductVariantSerializer(variant, data=request.data, partial=True)
        if serializer.is_valid():
            variant = serializer.save()
            
            # Update unit prices if cost price changed
            if 'base_cost_price' in serializer.validated_data or 'custom_profit_percentage' in serializer.validated_data:
                base_price = variant.selling_price_base
                for unit_price in variant.unit_prices.all():
                    new_price = base_price * unit_price.unit.conversion_factor
                    unit_price.price = round(new_price, 2)
                    unit_price.save()
            
            return Response(ProductVariantDetailSerializer(variant).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Check permissions
        if request.user.user_type == 'vendor' and variant.vendor.user != request.user:
            return Response(
                {'error': 'You can only delete your own product variants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete
        variant.is_active = False
        variant.save()
        return Response(
            {'message': 'Product variant deleted successfully'}, 
            status=status.HTTP_200_OK
        )

# ============ SEARCH AND DISCOVERY ============
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_search(request):
    """
    Search products with filters
    """
    search = request.GET.get('q', '')
    category_id = request.GET.get('category_id')
    market_id = request.GET.get('market_id')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    # Start with active variants
    variants = ProductVariant.objects.filter(
        is_active=True, 
        is_approved=True,
        product_template__is_active=True
    )
    
    if search:
        variants = variants.filter(
            Q(product_template__name__icontains=search) |
            Q(product_template__description__icontains=search) |
            Q(product_template__search_keywords__icontains=search) |
            Q(product_template__category__name__icontains=search)
        )
    
    if category_id:
        variants = variants.filter(product_template__category_id=category_id)
    
    if market_id:
        variants = variants.filter(market_zone__market_id=market_id)
    
    # Price filtering would require joining with unit_prices
    # This is simplified - in production you'd want to optimize this
    
    serializer = ProductVariantDetailSerializer(variants, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def similar_products(request, template_id):
    """
    Get similar products for AI recommendations
    """
    try:
        template = ProductTemplate.objects.get(id=template_id)
    except ProductTemplate.DoesNotExist:
        return Response(
            {'error': 'Product template not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get manually defined similar products
    similar_templates = template.similar_products.filter(is_active=True)
    
    # Also get products from same category
    same_category = ProductTemplate.objects.filter(
        category=template.category,
        is_active=True
    ).exclude(id=template_id)
    
    # Combine and remove duplicates
    all_similar = (similar_templates | same_category).distinct()[:10]
    
    # Get active variants for these templates
    variants = ProductVariant.objects.filter(
        product_template__in=all_similar,
        is_active=True,
        is_approved=True
    )
    
    serializer = ProductVariantDetailSerializer(variants, many=True)
    return Response({
        'original_product': ProductTemplateDetailSerializer(template).data,
        'similar_products': serializer.data
    })


# ============ PRODUCT ADDONS CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def product_addon_list_create(request):
    """
    List all product addons or create new
    """
    if request.method == 'GET':
        addons = ProductAddon.objects.filter(is_active=True)
        addon_type = request.GET.get('addon_type')
        
        if addon_type:
            addons = addons.filter(addon_type=addon_type)
        
        serializer = ProductAddonSerializer(addons, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admin can create addons
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create product addons'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProductAddonSerializer(data=request.data)
        if serializer.is_valid():
            addon = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def product_addon_detail(request, addon_id):
    """
    Retrieve, update or delete a product addon
    """
    try:
        addon = ProductAddon.objects.get(id=addon_id)
    except ProductAddon.DoesNotExist:
        return Response(
            {'error': 'Product addon not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = ProductAddonSerializer(addon)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admin can update addons
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update product addons'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProductAddonSerializer(addon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete addons
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete product addons'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete
        addon.is_active = False
        addon.save()
        return Response(
            {'message': 'Product addon deleted successfully'}, 
            status=status.HTTP_200_OK
        )

# ============ ADDON MAPPINGS CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def product_addon_mapping_list_create(request):
    """
    List all addon mappings or create new
    """
    if request.method == 'GET':
        variant_id = request.GET.get('variant_id')
        mappings = ProductAddonMapping.objects.filter(is_active=True)
        
        if variant_id:
            mappings = mappings.filter(product_variant_id=variant_id)
        
        serializer = ProductAddonMappingSerializer(mappings, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only vendors can map addons to their products
        if request.user.user_type != 'vendor':
            return Response(
                {'error': 'Only vendors can map addons to products'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProductAddonMappingSerializer(data=request.data)
        if serializer.is_valid():
            mapping = serializer.save()
            
            # Verify vendor owns the product variant
            if mapping.product_variant.vendor.user != request.user:
                mapping.delete()
                return Response(
                    {'error': 'You can only add addons to your own products'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def product_addon_mapping_detail(request, mapping_id):
    """
    Retrieve or delete an addon mapping
    """
    try:
        mapping = ProductAddonMapping.objects.get(id=mapping_id)
    except ProductAddonMapping.DoesNotExist:
        return Response(
            {'error': 'Addon mapping not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = ProductAddonMappingSerializer(mapping)
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        # Only vendor who owns the product can delete mapping
        if request.user.user_type != 'vendor' or mapping.product_variant.vendor.user != request.user:
            return Response(
                {'error': 'You can only remove addons from your own products'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        mapping.delete()
        return Response(
            {'message': 'Addon mapping deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

# ============ GLOBAL SETTINGS CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def global_setting_list_create(request):
    """
    List all global settings or create new (Admin only)
    """
    if request.method == 'GET':
        settings = GlobalSetting.objects.filter(is_active=True)
        serializer = GlobalSettingSerializer(settings, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admin can create global settings
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create global settings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = GlobalSettingSerializer(data=request.data)
        if serializer.is_valid():
            setting = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def global_setting_detail(request, setting_id):
    """
    Retrieve, update or delete a global setting (Admin only)
    """
    try:
        setting = GlobalSetting.objects.get(id=setting_id)
    except GlobalSetting.DoesNotExist:
        return Response(
            {'error': 'Global setting not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = GlobalSettingSerializer(setting)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admin can update global settings
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update global settings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = GlobalSettingSerializer(setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete global settings
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete global settings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        setting.delete()
        return Response(
            {'message': 'Global setting deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )
    

    # ============ UNIT PRICE CRUD ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def unit_price_list_create(request):
    """
    List all unit prices or create new
    """
    if request.method == 'GET':
        variant_id = request.GET.get('variant_id')
        unit_id = request.GET.get('unit_id')
        is_active = request.GET.get('is_active', 'true')
        
        unit_prices = UnitPrice.objects.all()
        
        if variant_id:
            unit_prices = unit_prices.filter(product_variant_id=variant_id)
        
        if unit_id:
            unit_prices = unit_prices.filter(unit_id=unit_id)
        
        if is_active.lower() == 'true':
            unit_prices = unit_prices.filter(is_active=True)
        elif is_active.lower() == 'false':
            unit_prices = unit_prices.filter(is_active=False)
        
        serializer = UnitPriceSerializer(unit_prices, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only vendors can create unit prices for their products
        if request.user.user_type != 'vendor':
            return Response(
                {'error': 'Only vendors can create unit prices'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UnitPriceSerializer(data=request.data)
        if serializer.is_valid():
            unit_price = serializer.save()
            
            # Verify vendor owns the product variant
            if unit_price.product_variant.vendor.user != request.user:
                unit_price.delete()
                return Response(
                    {'error': 'You can only add unit prices to your own products'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def unit_price_detail(request, unit_price_id):
    """
    Retrieve, update or delete a unit price
    """
    try:
        unit_price = UnitPrice.objects.get(id=unit_price_id)
    except UnitPrice.DoesNotExist:
        return Response(
            {'error': 'Unit price not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = UnitPriceSerializer(unit_price)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Check permissions
        if request.user.user_type == 'vendor' and unit_price.product_variant.vendor.user != request.user:
            return Response(
                {'error': 'You can only update unit prices for your own products'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UnitPriceSerializer(unit_price, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Check permissions
        if request.user.user_type == 'vendor' and unit_price.product_variant.vendor.user != request.user:
            return Response(
                {'error': 'You can only delete unit prices for your own products'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Instead of deleting, we can deactivate or check if it's the last unit price
        if unit_price.product_variant.unit_prices.filter(is_active=True).count() <= 1:
            return Response(
                {'error': 'Cannot delete the last active unit price for a product'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        unit_price.is_active = False
        unit_price.save()
        return Response(
            {'message': 'Unit price deleted successfully'}, 
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unit_price_bulk_update(request, variant_id):
    """
    Bulk update unit prices for a product variant
    """
    try:
        variant = ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        return Response(
            {'error': 'Product variant not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'vendor' and variant.vendor.user != request.user:
        return Response(
            {'error': 'You can only update unit prices for your own products'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'POST':
        unit_prices_data = request.data.get('unit_prices', [])
        
        if not isinstance(unit_prices_data, list):
            return Response(
                {'error': 'unit_prices must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_prices = []
        errors = []
        
        with transaction.atomic():
            for price_data in unit_prices_data:
                unit_id = price_data.get('unit_id')
                new_price = price_data.get('price')
                
                if not unit_id or new_price is None:
                    errors.append(f"Missing unit_id or price for one of the items")
                    continue
                
                try:
                    unit_price = UnitPrice.objects.get(
                        product_variant=variant,
                        unit_id=unit_id
                    )
                    
                    # Validate price
                    try:
                        price_decimal = float(new_price)
                        if price_decimal < 0:
                            errors.append(f"Price for {unit_id} cannot be negative")
                            continue
                    except (ValueError, TypeError):
                        errors.append(f"Invalid price for {unit_id}")
                        continue
                    
                    unit_price.price = price_decimal
                    unit_price.save()
                    updated_prices.append(UnitPriceSerializer(unit_price).data)
                    
                except UnitPrice.DoesNotExist:
                    errors.append(f"Unit price not found for unit {unit_id}")
                    continue
        
        if errors:
            return Response({
                'message': 'Some unit prices were updated, but there were errors',
                'updated_prices': updated_prices,
                'errors': errors
            }, status=status.HTTP_207_MULTI_STATUS)
        
        return Response({
            'message': 'All unit prices updated successfully',
            'updated_prices': updated_prices
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unit_price_recalculate(request, variant_id):
    """
    Recalculate all unit prices based on base cost price and profit percentage
    """
    try:
        variant = ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        return Response(
            {'error': 'Product variant not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'vendor' and variant.vendor.user != request.user:
        return Response(
            {'error': 'You can only recalculate unit prices for your own products'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'POST':
        recalculated_prices = []
        
        with transaction.atomic():
            base_price = variant.selling_price_base
            
            for unit_price in variant.unit_prices.filter(is_active=True):
                new_price = base_price * unit_price.unit.conversion_factor
                unit_price.price = round(new_price, 2)
                unit_price.save()
                recalculated_prices.append(UnitPriceSerializer(unit_price).data)
        
        return Response({
            'message': 'Unit prices recalculated successfully',
            'base_selling_price': float(base_price),
            'recalculated_prices': recalculated_prices
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_prices_by_market(request, market_id):
    """
    Get all product prices for a specific market (public endpoint)
    """
    try:
        from markets.models import Market
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        return Response(
            {'error': 'Market not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get active variants in this market
    variants = ProductVariant.objects.filter(
        market_zone__market=market,
        is_active=True,
        is_approved=True,
        product_template__is_active=True
    )
    
    category_id = request.GET.get('category_id')
    if category_id:
        variants = variants.filter(product_template__category_id=category_id)
    
    product_prices = []
    
    for variant in variants:
        unit_prices = variant.unit_prices.filter(is_active=True)
        if unit_prices.exists():
            product_data = {
                'product_variant_id': variant.id,
                'product_name': variant.product_template.name,
                'vendor_name': variant.vendor.business_name,
                'market_zone': variant.market_zone.name,
                'quality_grade': variant.quality_grade,
                'unit_prices': UnitPriceSerializer(unit_prices, many=True).data
            }
            product_prices.append(product_data)
    
    return Response({
        'market': market.name,
        'total_products': len(product_prices),
        'products': product_prices
    })