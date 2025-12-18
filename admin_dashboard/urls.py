# admin_dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [

    path('login/', views.admin_login_view, name='login'),
    path('logout/', views.admin_logout_view, name='logout'), 


    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.manage_users, name='manage-users'),
    path('users/<uuid:user_id>/', views.user_detail, name='user-detail'),
    path('users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='toggle-user-status'),
    path('users/<uuid:user_id>/verify/', views.verify_user, name='verify-user'),
    # User Management
    path('users/<uuid:user_id>/', views.user_detail, name='user-detail'),
    path('users/<uuid:user_id>/edit/', views.edit_user, name='edit-user'),
    path('users/<uuid:user_id>/verify/', views.verify_user, name='verify-user'),
    path('users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='toggle-user-status'),
    path('users/<uuid:user_id>/reset-password/', views.reset_user_password, name='reset-user-password'),
    path('users/<uuid:user_id>/delete/', views.delete_user, name='delete-user'),

    path('users/<uuid:user_id>/edit/', views.edit_user, name='edit-user'),
    path('users/<uuid:user_id>/update-security-answers/', views.update_security_answers, name='update-security-answers'),  # ← ADD THIS
    path('users/<uuid:user_id>/reset-password/', views.reset_user_password, name='reset-user-password'),
    path('users/<uuid:user_id>/delete/', views.delete_user, name='delete-user'),
    # Vendor Management
    # Vendor Management
    path('vendors/', views.manage_vendors, name='manage-vendors'),
    path('vendors/<uuid:vendor_id>/', views.vendor_detail, name='vendor-detail'),
    path('vendors/<uuid:vendor_id>/verify/', views.verify_vendor, name='verify-vendor'),
    path('vendors/<uuid:vendor_id>/suspend/', views.suspend_vendor, name='suspend-vendor'),
    path('vendors/<uuid:vendor_id>/activate/', views.activate_vendor, name='activate-vendor'),
    path('vendors/add/', views.add_vendor, name='add-vendor'),
    path('vendors/export/csv/', views.export_vendors_csv, name='export-vendors-csv'),
    path('vendors/bulk-action/', views.bulk_vendor_action, name='bulk-vendor-action'),                # Driver Management
    # Driver Management
    # Driver Management
    path('drivers/', views.manage_drivers, name='manage-drivers'),
    path('drivers/add/', views.add_driver, name='add-driver'),
    path('drivers/<uuid:driver_id>/', views.driver_detail, name='driver-detail'),
    path('drivers/<uuid:driver_id>/edit/', views.edit_driver, name='edit-driver'),
    path('drivers/<uuid:driver_id>/verify/', views.verify_driver, name='verify-driver'),
    path('drivers/<uuid:driver_id>/toggle-availability/', views.toggle_driver_availability, name='toggle-driver-availability'),
    path('drivers/<uuid:driver_id>/delete/', views.delete_driver, name='delete-driver'),
    path('drivers/export/csv/', views.export_drivers_csv, name='export-drivers-csv'),
    path('drivers/bulk-action/', views.bulk_driver_action, name='bulk-driver-action'),


    path('products/', views.manage_products, name='manage-products'),
    path('products/<uuid:product_id>/', views.product_detail, name='product-detail'),
    path('products/<uuid:product_id>/verify/', views.verify_product, name='verify-product'),
    path('products/<uuid:product_id>/toggle-status/', views.toggle_product_status, name='toggle-product-status'),
    path('products/add/', views.add_product_template, name='add-product'),
    path('products/<uuid:product_id>/edit/', views.edit_product_template, name='edit-product'),
    path('products/export/csv/', views.export_products_csv, name='export-products-csv'),
    # Category Management
    # Category Management
    path('categories/', views.manage_categories, name='manage-categories'),
    path('categories/add/', views.add_category, name='add-category'),
    path('categories/<uuid:category_id>/edit/', views.edit_category, name='edit-category'),
    path('categories/<uuid:category_id>/delete/', views.delete_category, name='delete-category'),


    path('products/bulk-action/', views.bulk_product_action, name='bulk-product-action'),
    path('products/<uuid:product_id>/variants/', views.manage_product_variants, name='manage-product-variants'),
    # admin_dashboard/urls.py
    path('products/<uuid:product_id>/variants/add/', views.add_product_variant, name='add-product-variant'),
    path('product-variants/<uuid:variant_id>/edit/', views.edit_product_variant, name='edit-product-variant'),


    # Market Management
    path('markets/', views.manage_markets, name='manage-markets'),
    path('markets/add/', views.add_market, name='add-market'),
    path('markets/<uuid:market_id>/', views.market_detail, name='market-detail'),
    path('markets/<uuid:market_id>/edit/', views.edit_market, name='edit-market'),
    path('markets/<uuid:market_id>/delete/', views.delete_market, name='delete-market'),
    
    # Market Zone Management URLs
    path('markets/<uuid:market_id>/zones/', views.manage_market_zones, name='manage-market-zones'),
    path('markets/<uuid:market_id>/zones/add/', views.add_market_zone, name='add-market-zone'),
    path('markets/zones/<uuid:zone_id>/edit/', views.edit_market_zone, name='edit-market-zone'),
    path('markets/zones/<uuid:zone_id>/delete/', views.delete_market_zone, name='delete-market-zone'),
    
    # Market Day Management URLs
    path('markets/days/', views.manage_market_days, name='manage-market-days'),
    path('markets/days/add/', views.add_market_day, name='add-market-day'),
    path('markets/days/<uuid:day_id>/delete/', views.delete_market_day, name='delete-market-day'),
    
    # Delivery Management URLs
    path('delivery/', views.delivery_dashboard, name='delivery-dashboard'),
    
    # Delivery Zone Management URLs
    path('delivery/markets/<uuid:market_id>/zones/', views.manage_delivery_zones, name='manage-delivery-zones'),
    path('delivery/markets/<uuid:market_id>/zones/add/', views.add_delivery_zone, name='add-delivery-zone'),
    path('delivery/zones/<uuid:zone_id>/', views.delivery_zone_detail, name='delivery-zone-detail'),
    path('delivery/zones/<uuid:zone_id>/edit/', views.edit_delivery_zone, name='edit-delivery-zone'),
    path('delivery/zones/<uuid:zone_id>/delete/', views.delete_delivery_zone, name='delete-delivery-zone'),
    
    # Delivery Fee Configuration URLs
    path('delivery/fee-configs/', views.manage_delivery_fee_configs, name='manage-delivery-fee-configs'),
    path('delivery/fee-configs/add/', views.add_delivery_fee_config, name='add-delivery-fee-config'),
    path('delivery/fee-configs/<uuid:config_id>/edit/', views.edit_delivery_fee_config, name='edit-delivery-fee-config'),
    path('delivery/fee-configs/<uuid:config_id>/delete/', views.delete_delivery_fee_config, name='delete-delivery-fee-config'),
    
    # Delivery Time Slot URLs
    path('delivery/time-slots/', views.manage_delivery_time_slots, name='manage-delivery-time-slots'),
    path('delivery/time-slots/add/', views.add_delivery_time_slot, name='add-delivery-time-slot'),
    path('delivery/time-slots/<uuid:slot_id>/edit/', views.edit_delivery_time_slot, name='edit-delivery-time-slot'),
    path('delivery/time-slots/<uuid:slot_id>/delete/', views.delete_delivery_time_slot, name='delete-delivery-time-slot'),
    
    # Customer Address Management URLs
    path('customers/addresses/', views.manage_customer_addresses, name='manage-customer-addresses'),
    path('customers/addresses/<uuid:address_id>/', views.customer_address_detail, name='customer-address-detail'),
    path('customers/addresses/<uuid:address_id>/toggle-verification/', views.toggle_address_verification, name='toggle-address-verification'),
    path('customers/addresses/<uuid:address_id>/recalculate-zone/', views.recalculate_address_zone, name='recalculate-address-zone'),
    
    # AJAX Endpoints
    path('ajax/calculate-delivery-fee/', views.calculate_delivery_fee_ajax, name='calculate-delivery-fee-ajax'),
    path('ajax/markets/<uuid:market_id>/zones/', views.get_market_zones_ajax, name='get-market-zones-ajax'),
    path('delivery/all-zones/', views.all_delivery_zones, name='all-delivery-zones'),
    
    # Analytics URLs
    path('analytics/delivery/', views.delivery_analytics, name='delivery-analytics'),
    
    # In urls.py
# Delivery Zones
    path('markets/<uuid:market_id>/delivery-zones/', views.manage_delivery_zones, name='manage-delivery-zones'),
    path('markets/<uuid:market_id>/delivery-zones/add/', views.add_delivery_zone, name='add-delivery-zone'),
    path('delivery-zones/<uuid:zone_id>/edit/', views.edit_delivery_zone, name='edit-delivery-zone'),
    path('delivery-zones/<uuid:zone_id>/delete/', views.delete_delivery_zone, name='delete-delivery-zone'),

    # Add these URLs to your markets URL patterns
    path('markets/bulk-action/', views.bulk_market_action, name='bulk-market-action'),
    path('markets/<uuid:market_id>/toggle-status/', views.toggle_market_status, name='toggle-market-status'),
    path('markets/export-csv/', views.export_markets_csv, name='export-markets-csv'),
    path('markets/zones/bulk-action/<uuid:market_id>/', views.bulk_zone_action, name='bulk-zone-action'),
    path('markets/zones/<uuid:zone_id>/toggle-status/', views.toggle_zone_status, name='toggle-zone-status'),


    # Add these URLs to your delivery URL patterns
    # CSV Export
    path('delivery-zones/<uuid:market_id>/export-csv/', views.export_delivery_zones_csv, name='export-delivery-zones-csv'),

    # Bulk Actions
    path('delivery-zones/bulk-action/<uuid:market_id>/', views.bulk_delivery_zone_action, name='bulk-delivery-zone-action'),
    path('delivery-zones/bulk-update/<uuid:market_id>/', views.bulk_update_delivery_zones, name='bulk-update-delivery-zones'),

    # Status Toggle
    path('delivery-zones/<uuid:zone_id>/toggle-status/', views.toggle_delivery_zone_status, name='toggle-delivery-zone-status'),
    path('delivery-zones/<uuid:zone_id>/quick-toggle/', views.quick_toggle_zone_status, name='quick-toggle-zone-status'),

    # AJAX Endpoints
    path('ajax/delivery-zones/<uuid:zone_id>/details/', views.get_zone_details_ajax, name='get-zone-details-ajax'),
    # path('delivery-settings/', views.manage_delivery_settings, name='manage-delivery-settings'),
    
    # Measurement Units
    # path('measurement-units/', views.measurement_units, name='measurement-units'),
    
    # System Settings
    path('system-settings/', views.system_settings, name='system-settings'),



    # Measurement Units
    path('measurement-units/', views.manage_units, name='measurement-units'),
    path('measurement-units/add/', views.add_unit, name='add-unit'),
    path('measurement-units/<uuid:unit_id>/edit/', views.edit_unit, name='edit-unit'),
    path('measurement-units/<uuid:unit_id>/delete/', views.delete_unit, name='delete-unit'),

    # Unit Types
    path('unit-types/', views.manage_unit_types, name='manage-unit-types'),
    path('unit-types/add/', views.add_unit_type, name='add-unit-type'),
    path('unit-types/<uuid:type_id>/edit/', views.edit_unit_type, name='edit-unit-type'),
    path('unit-types/<uuid:type_id>/delete/', views.delete_unit_type, name='delete-unit-type'),








    path('orders/', views.manage_orders, name='manage-orders'),
    path('orders/<uuid:order_id>/', views.order_detail, name='order-detail'),
    path('orders/<uuid:order_id>/update-status/', views.update_order_status, name='update-order-status'),
    path('orders/<uuid:order_id>/assign-driver/', views.assign_driver, name='assign-driver'),
    path('orders/<uuid:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    path('orders/<uuid:order_id>/update-payment/', views.update_payment_status, name='update-payment-status'),
    path('orders/<uuid:order_id>/timeline/', views.order_timeline, name='order-timeline'),
    path('orders/<uuid:order_id>/print/', views.print_order_invoice, name='print-order'),
    
    # Order Views
    path('orders/status/<str:status>/', views.orders_by_status, name='orders-by-status'),
    path('orders/today/', views.todays_orders, name='todays-orders'),
    path('orders/pending-preparation/', views.pending_preparation, name='pending-preparation'),
    path('orders/ready-for-pickup/', views.ready_for_pickup, name='ready-for-pickup'),
    
    # Bulk Actions
    path('orders/bulk-action/', views.bulk_order_action, name='bulk-order-action'),
    
    # Export
    path('orders/export-csv/', views.export_orders_csv, name='export-orders-csv'),
    
    # Analytics
    path('orders/analytics/', views.order_analytics, name='order-analytics'),
    path('orders/bulk-assign-driver/', views.bulk_assign_driver, name='bulk-assign-driver'),
]