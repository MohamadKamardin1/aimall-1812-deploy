"""
API URL routing for Flutter mobile app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Auth
    CustomerRegisterView, CustomerLoginView, AdminLoginView,
    ForgotPasswordRequestView, ForgotPasswordVerifyView,
    CustomerProfileView,
    SecurityQuestionListView,
    ClickPesaWebhookView,
    # Admin Analytics
    AdminDashboardStatsView, AdminSalesAnalyticsView, 
    AdminCustomerAnalyticsView, AdminProductAnalyticsView, AdminDeliveryAnalyticsView,
    AdminOrdersView, AdminOrderDetailView,
    DeliveryFeeCalculateView, NearestMarketView, CalculateDeliveryFeeContextView,
    FeesForLocationView,
    # Products
    ProductTemplateViewSet, MarketListView, MeasurementUnitView,
    # Cart & Orders
    CartViewSet, CustomerAddressViewSet, OrderViewSet,
    # Driver
    DriverLoginView, DriverVerifyOTPView, DriverProfileView,
    DriverUpdateLocationView, DriverStatsView, DriverOrderViewSet,
    DriverRegistrationView, DriverDetailsView,
    # Favorites
    FavoritesViewSet
)

router = DefaultRouter()
router.register(r'products', ProductTemplateViewSet, basename='product-template')
router.register(r'addresses', CustomerAddressViewSet, basename='customer-address')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'driver/orders', DriverOrderViewSet, basename='driver-order')
router.register(r'favorites', FavoritesViewSet, basename='favorite')

app_name = 'api'

urlpatterns = [
    # Authentication Endpoints
    path('auth/register/', CustomerRegisterView.as_view(), name='register'),
    path('auth/login/', CustomerLoginView.as_view(), name='login'),
    path('auth/admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('auth/forgot-password/', ForgotPasswordRequestView.as_view(), name='forgot-password'),
    path('auth/reset-password/', ForgotPasswordVerifyView.as_view(), name='reset-password'),
    path('auth/profile/', CustomerProfileView.as_view(), name='profile'),
    path('auth/security-questions/', SecurityQuestionListView.as_view(), name='security-questions'),
    
    # Admin Analytics Endpoints
    path('admin/dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/analytics/sales/', AdminSalesAnalyticsView.as_view(), name='admin-sales-analytics'),
    path('admin/analytics/customers/', AdminCustomerAnalyticsView.as_view(), name='admin-customer-analytics'),
    path('admin/analytics/products/', AdminProductAnalyticsView.as_view(), name='admin-product-analytics'),
    path('admin/analytics/delivery/', AdminDeliveryAnalyticsView.as_view(), name='admin-delivery-analytics'),
    
    # Admin Orders
    path('admin/orders/', AdminOrdersView.as_view(), name='admin-orders'),
    path('admin/orders/<uuid:pk>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
    
    # Delivery
    path('delivery-fee/calculate/', DeliveryFeeCalculateView.as_view(), name='delivery-fee-calculate'),
    path('markets/nearest_market/', NearestMarketView.as_view(), name='nearest-market'),
    path('markets/fees_for_location/', FeesForLocationView.as_view(), name='markets-fees-for-location'),
    path('delivery-fee/calculate_with_context/', CalculateDeliveryFeeContextView.as_view(), name='delivery-fee-context'),
    
    # Driver Authentication & Profile
    path('driver/register/', DriverRegistrationView.as_view(), name='driver-register'),
    path('driver/login/', DriverLoginView.as_view(), name='driver-login'),
    path('driver/verify-otp/', DriverVerifyOTPView.as_view(), name='driver-verify-otp'),
    path('driver/profile/', DriverProfileView.as_view(), name='driver-profile'),
    path('driver/details/', DriverDetailsView.as_view(), name='driver-details'),
    path('driver/update-location/', DriverUpdateLocationView.as_view(), name='driver-update-location'),
    path('driver/stats/', DriverStatsView.as_view(), name='driver-stats'),
    
    # Markets & Products
    path('markets/', MarketListView.as_view(), name='market-list'),
    path('measurement-units/', MeasurementUnitView.as_view(), name='measurement-unit-list'),
    path('products/', ProductTemplateViewSet.as_view({'get': 'list'}), name='product-list'),
    path('products/search/', ProductTemplateViewSet.as_view({'get': 'search'}), name='product-search'),
    
    # Cart
    path('cart/list/', CartViewSet.as_view({'get': 'list_carts'}), name='cart-list'),
    path('cart/get/', CartViewSet.as_view({'get': 'get_cart'}), name='cart-get'),
    path('cart/add/', CartViewSet.as_view({'post': 'add_item'}), name='cart-add-item'),
    path('cart/remove/', CartViewSet.as_view({'delete': 'remove_item'}), name='cart-remove-item'),
    path('cart/update/', CartViewSet.as_view({'post': 'update_item'}), name='cart-update-item'),
    path('cart/set-address/', CartViewSet.as_view({'post': 'set_delivery_address'}), name='cart-set-address'),
    path('cart/clear/', CartViewSet.as_view({'delete': 'clear_cart'}), name='cart-clear'),
    
    # Favorites
    path('favorites/', FavoritesViewSet.as_view({'get': 'list_favorites'}), name='favorites-list'),
    path('favorites/add/', FavoritesViewSet.as_view({'post': 'add_favorite'}), name='favorites-add'),
    path('favorites/remove/', FavoritesViewSet.as_view({'delete': 'remove_favorite'}), name='favorites-remove'),
    path('favorites/is-favorite/', FavoritesViewSet.as_view({'post': 'is_favorite'}), name='favorites-is-favorite'),
    
    # Payments
    path('payments/clickpesa/webhook/', ClickPesaWebhookView.as_view(), name='clickpesa-webhook'),
    
    # Router includes
    path('', include(router.urls)),
]
