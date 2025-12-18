from django.urls import path
from . import views

urlpatterns = [
    # Category endpoints
    path('categories/', views.category_list_create, name='category-list-create'),
    path('categories/<uuid:category_id>/', views.category_detail, name='category-detail'),
    
    # Measurement unit endpoints
    path('measurement-unit-types/', views.measurement_unit_type_list_create, name='unit-type-list-create'),
    path('measurement-units/', views.measurement_unit_list_create, name='unit-list-create'),
    
    # Product template endpoints
    path('product-templates/', views.product_template_list_create, name='product-template-list-create'),
    path('product-templates/<uuid:template_id>/', views.product_template_detail, name='product-template-detail'),
    
    # Product variant endpoints
    path('product-variants/', views.product_variant_list_create, name='product-variant-list-create'),
    path('product-variants/<uuid:variant_id>/', views.product_variant_detail, name='product-variant-detail'),
    
    # Search and discovery
    path('products/search/', views.product_search, name='product-search'),
    path('products/<uuid:template_id>/similar/', views.similar_products, name='similar-products'),

    path('product-addons/', views.product_addon_list_create, name='product-addon-list-create'),
    path('product-addons/<uuid:addon_id>/', views.product_addon_detail, name='product-addon-detail'),
    
    # Addon mapping endpoints
    path('addon-mappings/', views.product_addon_mapping_list_create, name='addon-mapping-list-create'),
    path('addon-mappings/<uuid:mapping_id>/', views.product_addon_mapping_detail, name='addon-mapping-detail'),
    
    # Global settings endpoints
    path('global-settings/', views.global_setting_list_create, name='global-setting-list-create'),
    path('global-settings/<uuid:setting_id>/', views.global_setting_detail, name='global-setting-detail'),

    path('unit-prices/', views.unit_price_list_create, name='unit-price-list-create'),
    path('unit-prices/<uuid:unit_price_id>/', views.unit_price_detail, name='unit-price-detail'),
    path('product-variants/<uuid:variant_id>/unit-prices/bulk-update/', views.unit_price_bulk_update, name='unit-price-bulk-update'),
    path('product-variants/<uuid:variant_id>/unit-prices/recalculate/', views.unit_price_recalculate, name='unit-price-recalculate'),
    path('markets/<uuid:market_id>/product-prices/', views.product_prices_by_market, name='product-prices-by-market'),
]