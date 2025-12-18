from django.urls import path
from . import views

urlpatterns = [
    # Market endpoints
    path('markets/', views.market_list_create, name='market-list-create'),
    path('markets/<uuid:market_id>/', views.market_detail, name='market-detail'),
    path('markets/nearby/', views.markets_nearby, name='markets-nearby'),
    
    # Market zone endpoints
    path('markets/<uuid:market_id>/zones/', views.market_zones_list_create, name='market-zones-list-create'),
    path('markets/<uuid:market_id>/zones/<uuid:zone_id>/', views.market_zone_detail, name='market-zone-detail'),
]