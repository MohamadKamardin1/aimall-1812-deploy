# location/views.py
from decimal import Decimal
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time
from .models import DeliveryTimeSlot, DeliveryZone, CustomerAddress
from markets.models import Market
from .serializers import (
    DeliveryTimeSlotSerializer, DeliveryZoneSerializer,
    CustomerAddressSerializer, MarketWithZonesSerializer
)

# ============ DELIVERY TIME SLOTS ============
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def delivery_time_slots(request):
    """Get available delivery time slots"""
    slots = DeliveryTimeSlot.objects.filter(is_active=True)
    serializer = DeliveryTimeSlotSerializer(slots, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def calculate_delivery_time(request):
    """Calculate delivery time based on current time"""
    now = timezone.now().time()
    today = timezone.now().date()
    
    slots = DeliveryTimeSlot.objects.filter(is_active=True).order_by('cut_off_time')
    
    available_slots = []
    for slot in slots:
        if now < slot.cut_off_time:
            # Can deliver today
            delivery_date = today
            delivery_time = f"{slot.delivery_start_time} - {slot.delivery_end_time}"
        else:
            # Will deliver tomorrow
            delivery_date = today + timezone.timedelta(days=1)
            delivery_time = f"{slot.delivery_start_time} - {slot.delivery_end_time}"
        
        available_slots.append({
            'slot': DeliveryTimeSlotSerializer(slot).data,
            'delivery_date': delivery_date,
            'delivery_time_range': delivery_time,
            'is_available': True
        })
    
    return Response({
        'current_time': now,
        'available_slots': available_slots
    })

# ============ MARKETS WITH DELIVERY INFO ============
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def markets_with_delivery_info(request):
    """Get all markets with delivery zones and time slots"""
    markets = Market.objects.filter(is_active=True).prefetch_related(
        'delivery_zones', 'zones'
    )
    serializer = MarketWithZonesSerializer(markets, many=True)
    return Response(serializer.data)

# ============ DELIVERY FEE CALCULATION ============
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_delivery_fee(request):
    """Calculate delivery fee for a location"""
    market_id = request.data.get('market_id')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    zone_id = request.data.get('zone_id')
    
    if not market_id:
        return Response(
            {'error': 'Market ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        market = Market.objects.get(id=market_id, is_active=True)
        
        if zone_id:
            # Use specific zone
            zone = DeliveryZone.objects.get(id=zone_id, market=market, is_active=True)
            delivery_fee = zone.calculate_delivery_fee(latitude, longitude)
        else:
            # Find appropriate zone based on coordinates
            zones = DeliveryZone.objects.filter(market=market, is_active=True)
            delivery_fee = None
            
            for zone in zones:
                # Check if coordinates fall within zone boundaries
                if (zone.min_latitude and zone.max_latitude and 
                    zone.min_longitude and zone.max_longitude):
                    if (zone.min_latitude <= float(latitude) <= zone.max_latitude and
                        zone.min_longitude <= float(longitude) <= zone.max_longitude):
                        delivery_fee = zone.calculate_delivery_fee(latitude, longitude)
                        break
            
            if delivery_fee is None:
                # Use base zone or minimum fee
                base_zone = zones.first()
                delivery_fee = base_zone.calculate_delivery_fee(latitude, longitude) if base_zone else Decimal('2000.00')
        
        return Response({
            'market': market.name,
            'delivery_fee': delivery_fee,
            'currency': 'TZS'
        })
        
    except Market.DoesNotExist:
        return Response(
            {'error': 'Market not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except DeliveryZone.DoesNotExist:
        return Response(
            {'error': 'Delivery zone not found'},
            status=status.HTTP_404_NOT_FOUND
        )

# ============ CUSTOMER ADDRESSES ============
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def customer_addresses(request):
    """List and create customer addresses"""
    if request.method == 'GET':
        addresses = CustomerAddress.objects.filter(
            customer=request.user, 
            is_active=True
        ).select_related('market', 'delivery_zone')
        serializer = CustomerAddressSerializer(addresses, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['customer'] = request.user.id
        
        # Calculate delivery fee
        market_id = data.get('market')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        zone_id = data.get('delivery_zone')
        
        if market_id and latitude and longitude:
            try:
                market = Market.objects.get(id=market_id)
                if zone_id:
                    zone = DeliveryZone.objects.get(id=zone_id, market=market)
                else:
                    zone = DeliveryZone.objects.filter(market=market, is_active=True).first()
                
                if zone:
                    data['delivery_zone'] = zone.id
                    data['estimated_delivery_fee'] = zone.calculate_delivery_fee(latitude, longitude)
            except (Market.DoesNotExist, DeliveryZone.DoesNotExist):
                pass
        
        serializer = CustomerAddressSerializer(data=data)
        if serializer.is_valid():
            address = serializer.save()
            return Response(
                CustomerAddressSerializer(address).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def customer_address_detail(request, address_id):
    """Retrieve, update or delete customer address"""
    try:
        address = CustomerAddress.objects.get(id=address_id, customer=request.user)
    except CustomerAddress.DoesNotExist:
        return Response(
            {'error': 'Address not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = CustomerAddressSerializer(address)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = CustomerAddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            # Recalculate delivery fee if location changed
            if any(field in request.data for field in ['latitude', 'longitude', 'market', 'delivery_zone']):
                market = address.market
                zone = address.delivery_zone
                if market and zone and address.latitude and address.longitude:
                    address.estimated_delivery_fee = zone.calculate_delivery_fee(
                        address.latitude, address.longitude
                    )
                    address.save()
            
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        address.is_active = False
        address.save()
        return Response(
            {'message': 'Address deleted successfully'}, 
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_default_address(request, address_id):
    """Set an address as default"""
    try:
        address = CustomerAddress.objects.get(id=address_id, customer=request.user)
        address.is_default = True
        address.save()
        
        return Response({
            'message': 'Default address updated successfully'
        })
        
    except CustomerAddress.DoesNotExist:
        return Response(
            {'error': 'Address not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )