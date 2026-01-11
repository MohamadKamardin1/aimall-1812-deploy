# admin_dashboard_api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'admin_dashboard_api'

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='api-user')
router.register(r'vendors', views.VendorViewSet, basename='api-vendor')
router.register(r'drivers', views.DriverViewSet, basename='api-driver')
router.register(r'products', views.ProductViewSet, basename='api-product')
router.register(r'categories', views.CategoryViewSet, basename='api-category')
router.register(r'orders', views.OrderViewSet, basename='api-order')
router.register(r'markets', views.MarketViewSet, basename='api-market')
router.register(r'delivery-zones', views.DeliveryZoneViewSet, basename='api-delivery-zone')
router.register(r'customer-addresses', views.CustomerAddressViewSet, basename='api-customer-address')
router.register(r'delivery-fees', views.DeliveryFeeConfigViewSet, basename='api-delivery-fee')
router.register(r'delivery-time-slots', views.DeliveryTimeSlotViewSet, basename='api-delivery-time-slot')
router.register(r'market-days', views.MarketDayViewSet, basename='api-market-day')
router.register(r'market-zones', views.MarketZoneViewSet, basename='api-market-zone')
router.register(r'unit-types', views.MeasurementUnitTypeViewSet, basename='api-unit-type')
router.register(r'units', views.MeasurementUnitViewSet, basename='api-unit')
router.register(r'admin-profiles', views.AdminProfileViewSet, basename='api-admin-profile')
router.register(r'customers', views.CustomerViewSet, basename='api-customer')
router.register(r'settings', views.GlobalSettingViewSet, basename='api-setting')
router.register(r'variants', views.ProductVariantViewSet, basename='api-variant')
router.register(r'prices', views.UnitPriceViewSet, basename='api-price')
router.register(r'addons', views.ProductAddonViewSet, basename='api-addon')
router.register(r'addon-mappings', views.ProductAddonMappingViewSet, basename='api-addon-mapping')
router.register(r'product-images', views.ProductImageViewSet, basename='api-product-image')
router.register(r'security-questions', views.SecurityQuestionViewSet, basename='api-security-question')
router.register(r'user-security-answers', views.UserSecurityAnswerViewSet, basename='api-security-answer')
router.register(r'groups', views.GroupViewSet, basename='api-group')
router.register(r'permissions', views.PermissionViewSet, basename='api-permission')
router.register(r'warehouse-locations', views.MarketViewSet, basename='api-warehouse') # Map warehouses to Markets
router.register(r'order-items', views.OrderItemViewSet, basename='api-order-item')
router.register(r'status-updates', views.OrderStatusUpdateViewSet, basename='api-status-update')
router.register(r'carts', views.CartViewSet, basename='api-cart')
router.register(r'cart-items', views.CartItemViewSet, basename='api-cart-item')

# Direct API endpoints (not using router)
urlpatterns = [
    # Auth endpoints
    path('auth/login/', views.AdminLoginView.as_view(), name='admin-login'),
    path('auth/logout/', views.AdminLogoutView.as_view(), name='admin-logout'),
    path('auth/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', views.AdminMeView.as_view(), name='admin-me'),
    
    # Dashboard endpoints
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/overview/', views.DashboardOverviewView.as_view(), name='dashboard-overview'),
    
    # Report endpoints
    path('reports/sales/', views.SalesReportView.as_view(), name='sales-report'),
    path('reports/users/', views.UserAnalyticsView.as_view(), name='user-analytics'),  # Fixed: changed from UserReportView
    
    # Analytics endpoints
    path('analytics/orders/', views.OrderAnalyticsView.as_view(), name='order-analytics'),
    path('analytics/revenue/', views.RevenueAnalyticsView.as_view(), name='revenue-analytics'),
    
    # Export endpoints
    path('export/orders/csv/', views.ExportOrdersCSVView.as_view(), name='export-orders-csv'),
    path('export/vendors/csv/', views.ExportVendorsCSVView.as_view(), name='export-vendors-csv'),
    path('export/drivers/csv/', views.ExportDriversCSVView.as_view(), name='export-drivers-csv'),
    path('export/products/csv/', views.ExportProductsCSVView.as_view(), name='export-products-csv'),
    
    # Bulk action endpoints
    path('bulk/users/', views.BulkUserActionView.as_view(), name='bulk-user-action'),
    path('bulk/vendors/', views.BulkVendorActionView.as_view(), name='bulk-vendor-action'),
    path('bulk/orders/', views.BulkOrderActionView.as_view(), name='bulk-order-action'),
    path('bulk/products/', views.BulkProductActionView.as_view(), name='bulk-product-action'),
    
    # Include router URLs (these will be at api/v2/admin/)
    path('', include(router.urls)),
]