# order/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Cart Management
    path('cart/', views.cart_management, name='cart-management'),
    path('cart/items/<uuid:item_id>/', views.cart_item_detail, name='cart-item-detail'),
    
    # Order Management
    path('order/', views.order_list, name='order-list'),
    path('order/create/', views.create_order, name='create-order'),
    path('order/<uuid:order_id>/', views.order_detail, name='order-detail'),
    path('order/<uuid:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    path('order/<uuid:order_id>/update-status/', views.update_order_status, name='update-order-status'),
    
    # Driver order
    path('driver/order/', views.driver_order, name='driver-order'),
]