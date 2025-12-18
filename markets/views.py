from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Market, MarketZone
from .serializers import (
    MarketSerializer, MarketDetailSerializer, 
    MarketZoneSerializer, MarketZoneDetailSerializer
)

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def market_list_create(request):
    """
    List all markets or create a new market
    """
    if request.method == 'GET':
        # Query parameters
        search = request.GET.get('search', '')
        is_active = request.GET.get('is_active', '')
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 20)
        
        # Build queryset
        markets = Market.objects.all()
        
        if search:
            markets = markets.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search) |
                Q(description__icontains=search)
            )
        
        if is_active.lower() == 'true':
            markets = markets.filter(is_active=True)
        elif is_active.lower() == 'false':
            markets = markets.filter(is_active=False)
        
        # Pagination
        paginator = Paginator(markets, page_size)
        try:
            markets_page = paginator.page(page)
        except:
            return Response(
                {'error': 'Invalid page number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MarketSerializer(markets_page, many=True)
        
        return Response({
            'data': serializer.data,
            'pagination': {
                'total': paginator.count,
                'pages': paginator.num_pages,
                'current': markets_page.number,
                'has_next': markets_page.has_next(),
                'has_previous': markets_page.has_previous(),
            }
        })
    
    elif request.method == 'POST':
        # Only admin can create markets
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create markets'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MarketSerializer(data=request.data)
        if serializer.is_valid():
            market = serializer.save()
            return Response(
                MarketDetailSerializer(market).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def market_detail(request, market_id):
    """
    Retrieve, update or delete a market
    """
    try:
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        return Response(
            {'error': 'Market not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = MarketDetailSerializer(market)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admin can update markets
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update markets'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MarketSerializer(market, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(MarketDetailSerializer(market).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete markets
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete markets'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        market.delete()
        return Response(
            {'message': 'Market deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def market_zones_list_create(request, market_id):
    """
    List all zones for a market or create a new zone
    """
    try:
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        return Response(
            {'error': 'Market not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        zones = market.zones.all()
        serializer = MarketZoneSerializer(zones, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admin can create zones
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create market zones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['market'] = market_id
        
        serializer = MarketZoneSerializer(data=data)
        if serializer.is_valid():
            zone = serializer.save()
            return Response(
                MarketZoneDetailSerializer(zone).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def market_zone_detail(request, market_id, zone_id):
    """
    Retrieve, update or delete a market zone
    """
    try:
        zone = MarketZone.objects.get(id=zone_id, market_id=market_id)
    except MarketZone.DoesNotExist:
        return Response(
            {'error': 'Market zone not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = MarketZoneDetailSerializer(zone)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admin can update zones
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update market zones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MarketZoneSerializer(zone, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(MarketZoneDetailSerializer(zone).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete zones
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete market zones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        zone.delete()
        return Response(
            {'message': 'Market zone deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def markets_nearby(request):
    """
    Find markets near a specific location
    """
    latitude = request.GET.get('lat')
    longitude = request.GET.get('lng')
    radius_km = request.GET.get('radius', 10)  # Default 10km radius
    
    if not latitude or not longitude:
        return Response(
            {'error': 'Latitude and longitude parameters are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lat = float(latitude)
        lng = float(longitude)
        radius = float(radius_km)
    except ValueError:
        return Response(
            {'error': 'Invalid coordinate parameters'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Simple distance calculation (for production, use PostGIS or geopy)
    markets = Market.objects.filter(is_active=True)
    
    nearby_markets = []
    for market in markets:
        if market.latitude and market.longitude:
            # Haversine formula for distance calculation
            from math import radians, sin, cos, sqrt, atan2
            R = 6371  # Earth radius in km
            
            lat1 = radians(lat)
            lon1 = radians(lng)
            lat2 = radians(float(market.latitude))
            lon2 = radians(float(market.longitude))
            
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            if distance <= radius:
                market_data = MarketSerializer(market).data
                market_data['distance_km'] = round(distance, 2)
                nearby_markets.append(market_data)
    
    # Sort by distance
    nearby_markets.sort(key=lambda x: x['distance_km'])
    
    return Response({
        'current_location': {'lat': lat, 'lng': lng},
        'radius_km': radius,
        'markets': nearby_markets,
        'total': len(nearby_markets)
    })