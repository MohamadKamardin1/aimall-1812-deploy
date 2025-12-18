# location/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Delivery Time Slots
    path('time-slots/', views.delivery_time_slots, name='delivery-time-slots'),
    path('calculate-delivery-time/', views.calculate_delivery_time, name='calculate-delivery-time'),
    
    # Markets with Delivery Info
    path('markets/', views.markets_with_delivery_info, name='markets-with-delivery-info'),
    
    # Delivery Fee Calculation
    path('calculate-fee/', views.calculate_delivery_fee, name='calculate-delivery-fee'),
    
    # Customer Addresses
    path('addresses/', views.customer_addresses, name='customer-addresses'),
    path('addresses/<uuid:address_id>/', views.customer_address_detail, name='customer-address-detail'),
    path('addresses/<uuid:address_id>/set-default/', views.set_default_address, name='set-default-address'),
]