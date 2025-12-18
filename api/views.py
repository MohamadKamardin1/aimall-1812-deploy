"""
API ViewSets for Flutter mobile app
Endpoints for:
- Customer authentication (register, login, forgot password)
- Product catalog browsing
- Cart management (per-market carts)
- Order placement with geo-location
- Driver delivery management
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Q
from django.db import transaction, IntegrityError
from decimal import Decimal
import logging
from django.http import Http404
from django.conf import settings

logger = logging.getLogger(__name__)

from accounts.models import User, Customer, Driver, SecurityQuestion, UserSecurityAnswer
from products.models import (
    ProductTemplate, ProductVariant, MeasurementUnit, UnitPrice,
    ProductAddon, ProductAddonMapping, FavoriteItem
)
from markets.models import Market
from location.models import CustomerAddress, DeliveryZone, DeliveryFeeConfig
from order.models import Order, OrderItem, Cart, CartItem
from order.cart_utils import CartService, CartCalculations, CartItemHelper

from .serializers import (
    # Auth
    CustomerLoginSerializer, CustomerRegistrationSerializer,
    ForgotPasswordRequestSerializer, ForgotPasswordVerifySerializer,
    SecurityQuestionSerializer, CustomerProfileSerializer,
    DriverProfileSerializer,
    # Products
    ProductTemplateListSerializer, ProductTemplateDetailSerializer,
    ProductVariantDetailSerializer, MarketListSerializer,
    MeasurementUnitSerializer, ProductAddonSerializer,
    # Cart
    CartSerializer, CartItemSerializer, CartItemCreateSerializer,
    CustomerAddressSerializer, CustomerAddressCreateSerializer,
    # Orders
    OrderDetailSerializer, OrderListSerializer, OrderCreateSerializer,
    OrderItemDetailSerializer,
    # Driver
    DriverOrderListSerializer, DriverOrderDetailSerializer,
    # Favorites
    FavoriteItemSerializer
)

# Import helper functions
from .order_helpers import calculate_order_totals, validate_and_normalize_delivery_fee, format_order_response


class SecurityQuestionListView(generics.ListAPIView):
    """List active security questions (for registration UI)"""
    permission_classes = [AllowAny]
    serializer_class = SecurityQuestionSerializer

    def get_queryset(self):
        return SecurityQuestion.objects.filter(is_active=True)


# ============================================
# AUTHENTICATION VIEWSETS
# ============================================

class CustomerRegisterView(generics.CreateAPIView):
    """Customer registration endpoint"""
    permission_classes = [AllowAny]
    serializer_class = CustomerRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        customer = serializer.save()
        user = customer.user
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Registration successful',
            'customer_id': str(customer.user.id),
            'phone_number': user.phone_number,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class CustomerLoginView(generics.GenericAPIView):
    """Customer login endpoint"""
    permission_classes = [AllowAny]
    serializer_class = CustomerLoginSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'customer_id': str(user.id),
            'phone_number': user.phone_number,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class ForgotPasswordRequestView(generics.GenericAPIView):
    """Get security questions for password reset"""
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordRequestSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        user = User.objects.get(phone_number=phone_number, user_type='customer')
        
        # Get user's security answers (only question IDs, not answers)
        questions = SecurityQuestion.objects.filter(
            is_active=True,
            usersecurityanswer__user=user
        ).values('id', 'question')
        
        return Response({
            'phone_number': phone_number,
            'security_questions': questions
        })


class ForgotPasswordVerifyView(generics.GenericAPIView):
    """Verify security answers and reset password"""
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordVerifySerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        answers = serializer.validated_data['answers']
        new_password = serializer.validated_data['new_password']
        
        user = User.objects.get(phone_number=phone_number, user_type='customer')
        
        # Verify all answers
        for answer_data in answers:
            question_id = answer_data.get('question_id')
            provided_answer = answer_data.get('answer', '').lower().strip()
            
            try:
                saved_answer = UserSecurityAnswer.objects.get(
                    user=user,
                    question_id=question_id
                )
                if saved_answer.answer.lower().strip() != provided_answer:
                    return Response({
                        'error': 'One or more security answers are incorrect.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except UserSecurityAnswer.DoesNotExist:
                return Response({
                    'error': 'Security question not found for this user.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password reset successful. Please log in with your new password.'
        })


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Get/update customer profile"""
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerProfileSerializer
    
    def get_object(self):
        return self.request.user.customer


class DeliveryFeeCalculateView(generics.GenericAPIView):
    """Calculate delivery fee for a given market and delivery location"""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        POST /api/v1/delivery-fee/calculate/
        body: {
            "market_id": "uuid",
            "customer_latitude": 6.7926,
            "customer_longitude": 39.2083,
            "order_total": 50000  // optional, for free delivery threshold
        }
        returns: {
            "delivery_fee": 2500,
            "zone_name": "Zone A",
            "distance_km": 5.5,
            "estimated_delivery_time": 30
        }
        """
        from django.contrib.gis.geos import Point
        
        market_id = request.data.get('market_id')
        customer_lat = request.data.get('customer_latitude')
        customer_lng = request.data.get('customer_longitude')
        order_total = Decimal(str(request.data.get('order_total', 0)))
        
        if not market_id or customer_lat is None or customer_lng is None:
            return Response(
                {'error': 'market_id, customer_latitude, and customer_longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            market = Market.objects.get(id=market_id, is_active=True)
        except Market.DoesNotExist:
            return Response(
                {'error': 'Market not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Compute distance and return fee using global DeliveryFeeConfig only.
        config = DeliveryFeeConfig.get_active_config()
        if not market.geo_location:
            return Response({'error': 'Market does not have a geo_location set'}, status=status.HTTP_400_BAD_REQUEST)

        distance_km = self._haversine_distance(
            market.geo_location.y, market.geo_location.x,
            customer_lat, customer_lng
        )

        # If distance exceeds configured maximum, return not available
        if config and distance_km > (config.max_delivery_distance or Decimal('50')):
            return Response({
                'error': f'Delivery not available beyond {config.max_delivery_distance}km'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Default delivery fee using base + per_km_rate (legacy)
        if order_total >= (config.free_delivery_threshold if config else Decimal('0')):
            legacy_fee = Decimal('0')
        else:
            legacy_fee = (config.base_fee if config else Decimal('0')) + (distance_km * (config.per_km_rate if config else Decimal('0')))

        # Tiered (bucket) fee: ceil(distance_km / step_km) * fee_per_step
        from math import ceil
        step_km = float(getattr(config, 'distance_step_km', Decimal('0.1')))
        fee_per_step = Decimal(str(getattr(config, 'fee_per_step', Decimal('0'))))
        # Convert distance to float km
        dist = float(distance_km)
        steps = ceil(dist / step_km) if step_km > 0 else 0
        tier_fee = fee_per_step * Decimal(steps)

        estimated_time = int((config.min_delivery_time if config else 30) + (float(distance_km) * (config.delivery_time_estimate_per_km if config else 0)))

        return Response({
            'delivery_fee': float(legacy_fee),
            'tier_fee': float(tier_fee),
            'distance_km': float(distance_km),
            'estimated_delivery_time': estimated_time,
            'tier_step_km': float(step_km),
            'tier_fee_per_step': float(fee_per_step),
        })
    
    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points in km"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return Decimal(str(R * c))
    
    def _calculate_zone_fee(self, zone, order_total, distance_km=None):
        """Calculate fee based on zone type"""
        config = DeliveryFeeConfig.get_active_config()
        
        if zone.zone_type == 'fixed':
            fee = zone.fixed_price or Decimal('0')
        elif zone.zone_type == 'free':
            fee = Decimal('0')
        elif zone.zone_type == 'unavailable':
            return Response(
                {'error': f'Delivery not available to {zone.name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif zone.zone_type == 'surcharge':
            base_fee = config.base_fee if config else Decimal('1000')
            surcharge = base_fee * (zone.surcharge_percent or Decimal('0')) / 100
            fee = base_fee + surcharge
        else:  # standard (distance-based)
            if order_total >= (config.free_delivery_threshold if config else Decimal('50000')):
                fee = Decimal('0')
            else:
                base_fee = config.base_fee if config else Decimal('1000')
                km_rate = config.per_km_rate if config else Decimal('500')
                fee = base_fee + (distance_km * km_rate if distance_km else Decimal('0'))
        
        estimated_time = zone.estimated_delivery_time or 30
        
        return Response({
            'delivery_fee': float(fee),
            'zone_name': zone.name,
            'distance_km': float(distance_km) if distance_km else 0,
            'estimated_delivery_time': estimated_time,
        })


class NearestMarketView(generics.GenericAPIView):
    """Find the market with lowest delivery fee for a given customer location"""
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/markets/nearest_market/
        body: {
            "latitude": -6.166667,
            "longitude": 39.283333,
            "order_total": 0  (optional, for free delivery threshold context)
        }
        returns: {
            "success": true,
            "market": {
                "id": "uuid",
                "name": "Market Name",
                "latitude": -6.1639,
                "longitude": 39.1974,
                "description": "..."
            },
            "delivery": {
                "fee": 5000.00,
                "distance_km": 3.2,
                "zone_id": "uuid",
                "zone_name": "Downtown",
                "estimated_time": 45,
                "calculation_method": "haversine"
            },
            "note": "Lowest fee among 5 available markets"
        }
        """
        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        from math import radians, sin, cos, sqrt, atan2, ceil
        
        customer_lat = request.data.get('latitude')
        customer_lng = request.data.get('longitude')
        order_total = Decimal(str(request.data.get('order_total', 0)))
        
        if customer_lat is None or customer_lng is None:
            return Response(
                {'success': False, 'error': 'latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer_lat = float(customer_lat)
            customer_lng = float(customer_lng)
        except (ValueError, TypeError):
            return Response(
                {'success': False, 'error': 'latitude and longitude must be valid numbers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all active markets
        markets = Market.objects.filter(is_active=True, geo_location__isnull=False)
        if not markets.exists():
            return Response({
                'success': False,
                'error': 'No markets available',
                'markets_checked': 0,
            }, status=status.HTTP_404_NOT_FOUND)
        
        config = DeliveryFeeConfig.get_active_config()
        max_distance = float(config.max_delivery_distance) if config else 50.0
        
        best_market = None
        lowest_fee = float('inf')
        best_zone = None
        best_distance = 0
        markets_checked = 0
        
        # Helper: Haversine distance calculation
        def haversine(lat1, lng1, lat2, lng2):
            R = 6371  # Earth radius in km
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c
        
        # Check each market
        for market in markets:
            markets_checked += 1
            market_lat = float(market.geo_location.y)
            market_lng = float(market.geo_location.x)
            
            distance_km = haversine(customer_lat, customer_lng, market_lat, market_lng)
            
            # Skip if beyond max delivery distance
            if distance_km > max_distance:
                continue
            
            # Try to find applicable delivery zone for this market
            customer_point = Point(customer_lng, customer_lat, srid=4326)
            
            # Find zones that contain the customer location
            zones = DeliveryZone.objects.filter(
                market=market,
                is_active=True,
                boundary__contains=customer_point
            ).order_by('priority')
            
            # If no containing zone, find nearest by center point
            if not zones.exists():
                zones = DeliveryZone.objects.filter(
                    market=market,
                    is_active=True,
                    center_point__isnull=False
                ).order_by('priority')
            
            if zones.exists():
                zone = zones.first()
            else:
                # Use default zone calculation
                zone = None
            
            # Calculate fee for this market
            if zone:
                if zone.zone_type == 'unavailable':
                    continue  # Skip unavailable zones
                elif zone.zone_type == 'fixed':
                    fee = float(zone.fixed_price or 0)
                elif zone.zone_type == 'free':
                    fee = 0.0
                elif zone.zone_type == 'surcharge':
                    base = float(config.base_fee) if config else 1000
                    surcharge_pct = float(zone.surcharge_percent or 0)
                    fee = base * (1 + surcharge_pct / 100)
                else:  # standard
                    if order_total >= (config.free_delivery_threshold if config else 50000):
                        fee = 0.0
                    else:
                        base_fee = float(config.base_fee) if config else 1000
                        km_rate = float(config.per_km_rate) if config else 500
                        fee = base_fee + (distance_km * km_rate)
            else:
                # No zone info, use default calculation
                if order_total >= (config.free_delivery_threshold if config else 50000):
                    fee = 0.0
                else:
                    base_fee = float(config.base_fee) if config else 1000
                    km_rate = float(config.per_km_rate) if config else 500
                    fee = base_fee + (distance_km * km_rate)
            
            # Track market with lowest fee
            if fee < lowest_fee:
                lowest_fee = fee
                best_market = market
                best_zone = zone
                best_distance = distance_km
        
        if not best_market:
            return Response({
                'success': False,
                'error': 'No delivery zones available at given location',
                'markets_checked': markets_checked,
                'max_delivery_distance_km': max_distance,
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Estimate delivery time
        estimated_time = 30
        if best_zone:
            estimated_time = best_zone.estimated_delivery_time or 30
        elif config:
            estimated_time = int(config.min_delivery_time + (best_distance * config.delivery_time_estimate_per_km))
        
        return Response({
            'success': True,
            'market': {
                'id': str(best_market.id),
                'name': best_market.name,
                'latitude': float(best_market.geo_location.y),
                'longitude': float(best_market.geo_location.x),
                'description': best_market.description,
                'contact_phone': best_market.contact_phone,
            },
            'delivery': {
                'fee': lowest_fee,
                'distance_km': round(best_distance, 2),
                'zone_id': str(best_zone.id) if best_zone else None,
                'zone_name': best_zone.name if best_zone else 'Default',
                'estimated_time': estimated_time,
                'calculation_method': 'haversine',
            },
            'note': f'Lowest fee among {markets_checked} available markets',
        }, status=status.HTTP_200_OK)


class CalculateDeliveryFeeContextView(generics.GenericAPIView):
    """Calculate delivery fee considering order total for free delivery threshold"""
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/delivery-fee/calculate_with_context/
        body: {
            "market_id": "uuid",
            "latitude": -6.166667,
            "longitude": 39.283333,
            "order_total": 50000  (REQUIRED for free delivery threshold)
        }
        returns: {
            "success": true,
            "delivery_fee": 0.00,
            "distance_km": 3.2,
            "calculation_method": "haversine",
            "fee_breakdown": {
                "base_fee": 5000,
                "surcharge": 0,
                "discount_applied": "free_delivery_threshold"
            },
            "reason": "Free delivery because order total (50000) >= free threshold (50000)",
            "estimated_delivery_time": 45
        }
        """
        from django.contrib.gis.geos import Point
        from math import radians, sin, cos, sqrt, atan2, ceil
        
        market_id = request.data.get('market_id')
        customer_lat = request.data.get('latitude')
        customer_lng = request.data.get('longitude')
        order_total = request.data.get('order_total')
        
        # Validate required fields
        if not market_id or customer_lat is None or customer_lng is None or order_total is None:
            return Response({
                'success': False,
                'error': 'market_id, latitude, longitude, and order_total are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            market = Market.objects.get(id=market_id, is_active=True)
        except Market.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Market not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            customer_lat = float(customer_lat)
            customer_lng = float(customer_lng)
            order_total = Decimal(str(order_total))
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'latitude, longitude, and order_total must be valid numbers'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not market.geo_location:
            return Response({
                'success': False,
                'error': 'Market does not have a geo_location set'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate distance using Haversine
        def haversine(lat1, lng1, lat2, lng2):
            R = 6371  # Earth radius in km
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c
        
        market_lat = float(market.geo_location.y)
        market_lng = float(market.geo_location.x)
        distance_km = haversine(customer_lat, customer_lng, market_lat, market_lng)
        
        config = DeliveryFeeConfig.get_active_config()
        max_distance = float(config.max_delivery_distance) if config else 50.0
        
        # Check if beyond max delivery distance
        if distance_km > max_distance:
            return Response({
                'success': False,
                'error': f'Location outside delivery range (>{max_distance}km)',
                'max_distance_km': max_distance,
                'actual_distance_km': round(distance_km, 2),
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find applicable delivery zone
        customer_point = Point(customer_lng, customer_lat, srid=4326)
        
        zones = DeliveryZone.objects.filter(
            market=market,
            is_active=True,
            boundary__contains=customer_point
        ).order_by('priority')
        
        if not zones.exists():
            zones = DeliveryZone.objects.filter(
                market=market,
                is_active=True,
                center_point__isnull=False
            ).order_by('priority')
        
        zone = zones.first() if zones.exists() else None
        
        # Calculate delivery fee
        delivery_fee = Decimal('0.00')
        reason = ''
        fee_breakdown = {
            'base_fee': 0,
            'surcharge': 0,
            'discount_applied': None,
        }
        estimated_time = 30
        
        # Check free delivery threshold first
        free_threshold = config.free_delivery_threshold if config else Decimal('50000')
        
        if order_total >= free_threshold:
            delivery_fee = Decimal('0.00')
            reason = f'Free delivery because order total ({float(order_total):.2f}) >= free threshold ({float(free_threshold):.2f})'
            fee_breakdown['discount_applied'] = 'free_delivery_threshold'
        else:
            # Apply zone-specific pricing
            if zone:
                if zone.zone_type == 'unavailable':
                    return Response({
                        'success': False,
                        'error': f'Delivery not available to {zone.name}',
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif zone.zone_type == 'fixed':
                    delivery_fee = Decimal(str(zone.fixed_price or 0))
                    reason = f'Fixed price zone: {zone.name}'
                    fee_breakdown['base_fee'] = float(delivery_fee)
                elif zone.zone_type == 'free':
                    delivery_fee = Decimal('0.00')
                    reason = f'Free delivery zone: {zone.name}'
                    fee_breakdown['discount_applied'] = 'free_zone'
                elif zone.zone_type == 'surcharge':
                    base_fee = Decimal(str(config.base_fee)) if config else Decimal('1000')
                    surcharge_pct = Decimal(str(zone.surcharge_percent or 0))
                    surcharge_amt = (base_fee * surcharge_pct) / 100
                    delivery_fee = base_fee + surcharge_amt
                    reason = f'Surcharge zone {zone.name}: {surcharge_pct}% surcharge applied'
                    fee_breakdown['base_fee'] = float(base_fee)
                    fee_breakdown['surcharge'] = float(surcharge_amt)
                else:  # standard
                    base_fee = Decimal(str(config.base_fee)) if config else Decimal('1000')
                    km_rate = Decimal(str(config.per_km_rate)) if config else Decimal('500')
                    delivery_fee = base_fee + (Decimal(str(distance_km)) * km_rate)
                    reason = f'Distance-based: {distance_km:.2f}km x {float(km_rate):.0f} TZS/km + {float(base_fee):.0f} TZS base'
                    fee_breakdown['base_fee'] = float(base_fee)
                
                estimated_time = zone.estimated_delivery_time or 30
            else:
                # No zone info, use default config
                base_fee = Decimal(str(config.base_fee)) if config else Decimal('1000')
                km_rate = Decimal(str(config.per_km_rate)) if config else Decimal('500')
                delivery_fee = base_fee + (Decimal(str(distance_km)) * km_rate)
                reason = f'Default calculation: {distance_km:.2f}km x {float(km_rate):.0f} TZS/km + {float(base_fee):.0f} TZS base'
                fee_breakdown['base_fee'] = float(base_fee)
                
                if config:
                    estimated_time = int(config.min_delivery_time + (distance_km * config.delivery_time_estimate_per_km))
        
        return Response({
            'success': True,
            'delivery_fee': float(delivery_fee),
            'distance_km': round(distance_km, 2),
            'calculation_method': 'haversine',
            'fee_breakdown': fee_breakdown,
            'reason': reason,
            'estimated_delivery_time': estimated_time,
        }, status=status.HTTP_200_OK)


class FeesForLocationView(generics.GenericAPIView):
    """Return all markets with their calculated delivery fees for a given customer location
    Useful for showing a fee comparison dialog when changing markets from the app.
    POST body: {"latitude": -6.16, "longitude": 39.28, "order_total": 0}
    Response: {"success": true, "markets": [{"market": {...}, "delivery": {...}}, ...]}
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        from django.contrib.gis.geos import Point
        from math import radians, sin, cos, sqrt, atan2

        customer_lat = request.data.get('latitude')
        customer_lng = request.data.get('longitude')
        order_total = Decimal(str(request.data.get('order_total', 0)))

        if customer_lat is None or customer_lng is None:
            return Response({'success': False, 'error': 'latitude and longitude are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer_lat = float(customer_lat)
            customer_lng = float(customer_lng)
        except (ValueError, TypeError):
            return Response({'success': False, 'error': 'latitude and longitude must be valid numbers'}, status=status.HTTP_400_BAD_REQUEST)

        markets = Market.objects.filter(is_active=True, geo_location__isnull=False)
        if not markets.exists():
            return Response({'success': False, 'error': 'No markets available', 'markets': []}, status=status.HTTP_404_NOT_FOUND)

        config = DeliveryFeeConfig.get_active_config()
        max_distance = float(config.max_delivery_distance) if config else 50.0

        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c

        results = []

        for market in markets:
            market_lat = float(market.geo_location.y)
            market_lng = float(market.geo_location.x)
            distance_km = haversine(customer_lat, customer_lng, market_lat, market_lng)

            if distance_km > max_distance:
                continue

            customer_point = Point(customer_lng, customer_lat, srid=4326)

            zones = DeliveryZone.objects.filter(market=market, is_active=True, boundary__contains=customer_point).order_by('priority')
            if not zones.exists():
                zones = DeliveryZone.objects.filter(market=market, is_active=True, center_point__isnull=False).order_by('priority')

            zone = zones.first() if zones.exists() else None

            # Calculate fee (same rules as other views)
            if zone:
                if zone.zone_type == 'unavailable':
                    continue
                elif zone.zone_type == 'fixed':
                    fee = float(zone.fixed_price or 0)
                elif zone.zone_type == 'free':
                    fee = 0.0
                elif zone.zone_type == 'surcharge':
                    base = float(config.base_fee) if config else 1000
                    surcharge_pct = float(zone.surcharge_percent or 0)
                    fee = base * (1 + surcharge_pct / 100)
                else:
                    if order_total >= (config.free_delivery_threshold if config else 50000):
                        fee = 0.0
                    else:
                        base_fee = float(config.base_fee) if config else 1000
                        km_rate = float(config.per_km_rate) if config else 500
                        fee = base_fee + (distance_km * km_rate)
            else:
                if order_total >= (config.free_delivery_threshold if config else 50000):
                    fee = 0.0
                else:
                    base_fee = float(config.base_fee) if config else 1000
                    km_rate = float(config.per_km_rate) if config else 500
                    fee = base_fee + (distance_km * km_rate)

            results.append({
                'market': {
                    'id': str(market.id),
                    'name': market.name,
                    'latitude': market_lat,
                    'longitude': market_lng,
                    'description': market.description,
                },
                'delivery': {
                    'fee': round(float(fee), 2),
                    'distance_km': round(distance_km, 2),
                    'zone_id': str(zone.id) if zone else None,
                    'zone_name': zone.name if zone else 'Default',
                }
            })

        # Sort by fee ascending
        results = sorted(results, key=lambda r: r['delivery']['fee'])

        return Response({'success': True, 'markets': results}, status=status.HTTP_200_OK)


# ============================================
# PRODUCT CATALOG VIEWSETS
# ============================================

class MarketListView(generics.ListAPIView):
    """List all markets with locations for map display"""
    permission_classes = [AllowAny]
    queryset = Market.objects.filter(is_active=True)
    serializer_class = MarketListSerializer


class ProductTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Product templates (catalog items)"""
    permission_classes = [AllowAny]
    serializer_class = ProductTemplateListSerializer
    queryset = ProductTemplate.objects.filter(is_active=True, is_verified=True)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductTemplateDetailSerializer
        return ProductTemplateListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get product detail. If market_id provided, filter variants to that market only"""
        instance = self.get_object()
        market_id = request.query_params.get('market_id')
        
        if market_id:
            # Filter variants to only those from vendors in the selected market
            try:
                market = Market.objects.get(id=market_id, is_active=True)
                # Store market context so serializer can use it
                request.market_id = market_id
                request.market = market
            except (Market.DoesNotExist, ValueError):
                # If market is invalid, return error
                return Response(
                    {'error': 'Invalid or unknown market_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_market(self, request):
        """Get products available in a specific market"""
        market_id = request.query_params.get('market_id')
        
        if not market_id:
            return Response(
                {'error': 'market_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Validate market_id and ensure market exists (avoid passing invalid UUIDs to ORM)
        try:
            market = Market.objects.get(id=market_id, is_active=True)
        except (Market.DoesNotExist, ValueError) as e:
            # ValueError can happen if the provided id is not a valid UUID string
            return Response({'error': 'Invalid or unknown market_id'}, status=status.HTTP_400_BAD_REQUEST)

        # Get products from vendors in this market's zones
        products = ProductTemplate.objects.filter(
            is_active=True,
            is_verified=True,
            variants__market_zone__market_id=market.id,
            variants__is_active=True,
            variants__is_approved=True
        ).distinct()
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def products_with_pricing(self, request):
        """
        Get products with highest price and unit for a market.
        This endpoint returns products with their display price and unit already calculated.
        Query params:
        - market_id (required): UUID of the market
        """
        market_id = request.query_params.get('market_id')
        
        if not market_id:
            return Response(
                {'error': 'market_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            market = Market.objects.get(id=market_id, is_active=True)
        except (Market.DoesNotExist, ValueError):
            return Response({'error': 'Invalid or unknown market_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get products from vendors in this market's zones
        products = ProductTemplate.objects.filter(
            is_active=True,
            is_verified=True,
            variants__market_zone__market_id=market.id,
            variants__is_active=True,
            variants__is_approved=True
        ).distinct()
        
        # Build response with pricing data
        result = []
        for product in products:
            result.append(self._get_product_with_pricing(product))
        
        return Response(result)
    
    def _get_product_with_pricing(self, product):
        """
        Extract highest price and unit for a product.
        Returns dict with product info + display_price + display_unit.
        """
        from decimal import Decimal
        
        max_price = None
        unit_symbol = 'pcs'
        
        # Find highest price across all variants' unit prices
        for variant in product.variants.filter(is_active=True, is_approved=True):
            for up in variant.unit_prices.filter(is_active=True):
                try:
                    val = Decimal(str(up.selling_price))
                    if max_price is None or val > max_price:
                        max_price = val
                        # Get unit symbol from the unit price's unit
                        unit_symbol = getattr(up.unit, 'symbol', 'pcs') if up.unit else 'pcs'
                except Exception:
                    continue
        
        # Fallback: if no unit prices found, try to get from available_units
        if max_price is None:
            max_price = Decimal('0')
        
        # Get image URL
        image_url = None
        if product.main_image:
            image_url = product.main_image.url
        
        return {
            'id': str(product.id),
            'name': product.name,
            'description': product.description[:100] if product.description else '',
            'category_name': product.category.name if product.category else 'Other',
            'image_url': image_url,
            'main_image_url': image_url,
            'display_price': float(max_price),
            'display_unit': unit_symbol,
            'is_active': product.is_active,
        }
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search products by name or keywords"""
        query = request.query_params.get('q', '')
        
        if len(query) < 2:
            return Response(
                {'error': 'Search query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = ProductTemplate.objects.filter(
            Q(name__icontains=query) | Q(search_keywords__icontains=query),
            is_active=True,
            is_verified=True
        )
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def variants(self, request, pk=None):
        """Get all variants of a product from different vendors"""
        product = self.get_object()
        variants = product.variants.filter(is_active=True, is_approved=True)
        serializer = ProductVariantDetailSerializer(variants, many=True)
        return Response(serializer.data)


class MeasurementUnitView(generics.ListAPIView):
    """List measurement units"""
    permission_classes = [AllowAny]
    queryset = MeasurementUnit.objects.filter(is_active=True)
    serializer_class = MeasurementUnitSerializer


# ============================================
# CART VIEWSETS
# ============================================

class CartViewSet(viewsets.ViewSet):
    """Shopping cart management - per market"""
    permission_classes = [IsAuthenticated]
    
    def get_cart(self, market_id):
        """Get or create cart for market"""
        cart, _ = Cart.objects.get_or_create(
            customer=self.request.user,
            market_id=market_id
        )
        return cart
    
    @action(detail=False, methods=['get'])
    def list_carts(self, request):
        """Get all user's carts (one per market)"""
        carts = Cart.objects.filter(customer=request.user).prefetch_related('items')
        serializer = CartSerializer(carts, many=True)
        return Response(serializer.data)
    
    def _get_or_create_cart(self, user, market_id):
        """Helper method to get or create a cart for a specific market"""
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return None
        
        cart, created = Cart.objects.get_or_create(
            customer=user,
            market=market
        )
        return cart
    
    @action(detail=False, methods=['get'])
    def get_cart(self, request):
        """Get cart for specific market"""
        market_id = request.query_params.get('market_id')
        
        if not market_id:
            return Response(
                {'error': 'market_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = self._get_or_create_cart(request.user, market_id)
        if not cart:
            return Response(
                {'error': 'Market not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart with full validation and calculations"""
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        market_id = request.data.get('market_id')
        if not market_id:
            return Response(
                {'error': 'market_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get or create cart with transaction safety
            with transaction.atomic():
                try:
                    cart = self._get_or_create_cart(request.user, market_id)
                except IntegrityError as e:
                    logger.warning(f"IntegrityError creating cart for user {request.user.id}: {e}")
                    # Try to get existing cart if creation failed
                    from markets.models import Market
                    try:
                        market = Market.objects.get(id=market_id)
                        cart = Cart.objects.get(customer=request.user, market=market)
                    except (Market.DoesNotExist, Cart.DoesNotExist):
                        return Response(
                            {'error': 'Failed to create or retrieve cart. Please try again.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
            
            if not cart:
                return Response(
                    {'error': 'Market not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get product variant
            product_variant = ProductVariant.objects.get(
                id=serializer.validated_data['product_variant_id'],
                is_active=True
            )
            
            # Validate quantity (stock checks removed as ProductVariant no longer has stock field)
            quantity = Decimal(str(serializer.validated_data['quantity']))
            if quantity <= 0:
                return Response(
                    {'error': 'Quantity must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get measurement unit
            unit = MeasurementUnit.objects.get(
                id=serializer.validated_data['unit_id'],
                is_active=True
            )
            
            # Get addons if provided
            addons = None
            if serializer.validated_data.get('selected_addons'):
                addons = serializer.validated_data['selected_addons']
            
            # Use CartService to add item with all validations
            with transaction.atomic():
                cart_item = CartService.add_to_cart(
                    cart=cart,
                    product_variant=product_variant,
                    unit=unit,
                    quantity=serializer.validated_data['quantity'],
                    addons=addons,
                    instructions=serializer.validated_data.get('special_instructions', '')
                )
            
            # Get complete cart summary
            cart_summary = CartService.get_cart_summary(cart)
            
            return Response({
                'message': 'Item added to cart successfully',
                'cart_item': CartItemHelper.get_item_details(cart_item),
                'cart_summary': cart_summary
            }, status=status.HTTP_201_CREATED)
        
        except ProductVariant.DoesNotExist:
            return Response(
                {'error': 'Product variant not found. Please refresh and try again.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except MeasurementUnit.DoesNotExist:
            return Response(
                {'error': 'Unit of measurement not available. Please select a different unit.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Error adding item to cart: {e}")
            return Response(
                {'error': 'An error occurred while adding item to cart. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove item from cart"""
        cart_item_id = request.query_params.get('item_id')
        
        if not cart_item_id:
            return Response(
                {'error': 'item_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                cart__customer=request.user
            )
            cart = cart_item.cart
            
            # Use CartService to remove item
            CartService.remove_from_cart(cart, cart_item_id)
            
            # Get updated cart summary
            cart_summary = CartService.get_cart_summary(cart)
            
            return Response({
                'message': 'Item removed from cart',
                'cart_summary': cart_summary
            })
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update cart item quantity"""
        cart_item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not cart_item_id or quantity is None:
            return Response(
                {'error': 'item_id and quantity required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Convert quantity to Decimal
            try:
                quantity_decimal = Decimal(str(quantity))
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid quantity format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                cart__customer=request.user
            )
            cart = cart_item.cart
            
            # Use CartItemHelper to update quantity properly
            CartItemHelper.update_item_quantity(cart_item, quantity_decimal)
            
            # Get updated cart summary
            cart_summary = CartService.get_cart_summary(cart)
            
            return Response({
                'message': 'Item quantity updated',
                'cart_item': CartItemHelper.get_item_details(cart_item),
                'cart_summary': cart_summary
            })
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def set_delivery_address(self, request):
        """Set delivery address for cart"""
        market_id = request.data.get('market_id')
        address_id = request.data.get('address_id')
        
        if not market_id or not address_id:
            return Response(
                {'error': 'market_id and address_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart = self.get_cart(market_id)
            address = CustomerAddress.objects.get(
                id=address_id,
                customer=request.user.customer
            )
            cart.delivery_address = address
            cart.save()
            
            return Response({
                'message': 'Delivery address set',
                'cart': CartSerializer(cart).data
            })
        except CustomerAddress.DoesNotExist:
            return Response(
                {'error': 'Address not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def clear_cart(self, request):
        """Clear all items from a specific market cart and delete the cart"""
        market_id = request.query_params.get('market_id')
        
        if not market_id:
            return Response(
                {'error': 'market_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            try:
                from markets.models import Market
                market = Market.objects.get(id=market_id)
                cart = Cart.objects.get(customer=request.user, market=market)
                cart.delete()
                
                return Response({
                    'message': 'Market cart cleared and removed successfully',
                    'remaining_carts': len(Cart.objects.filter(customer=request.user))
                })
            except Cart.DoesNotExist:
                return Response({
                    'message': 'Cart not found (already empty)',
                    'remaining_carts': len(Cart.objects.filter(customer=request.user))
                })
        except Exception as e:
            logger.exception(f"Error clearing market cart: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['delete'])
    def clear_all_carts(self, request):
        """Clear all carts across all markets for the authenticated user"""
        try:
            with transaction.atomic():
                carts = Cart.objects.filter(customer=request.user)
                cart_count = carts.count()
                carts.delete()
                
                return Response({
                    'message': f'All {cart_count} market carts cleared successfully',
                    'cleared_markets': cart_count,
                    'remaining_carts': 0
                })
        except Exception as e:
            logger.exception(f"Error clearing all carts: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================
# ADDRESS VIEWSET
# ============================================

class CustomerAddressViewSet(viewsets.ModelViewSet):
    """Customer delivery addresses"""
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerAddressSerializer
    
    def get_queryset(self):
        return CustomerAddress.objects.filter(customer=self.request.user)
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CustomerAddressCreateSerializer
        return CustomerAddressSerializer
    
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


# ============================================
# ORDER VIEWSET
# ============================================

class OrderViewSet(viewsets.ViewSet):
    """Order management"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get customer's orders"""
        orders = Order.objects.filter(
            customer=request.user
        ).prefetch_related('items').order_by('-created_at')
        
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get order details"""
        try:
            order = Order.objects.get(id=pk, customer=request.user)
            serializer = OrderDetailSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """Create order from cart with validation"""
        logger.info(f'[CreateOrder] ===== NEW ORDER REQUEST =====')
        logger.info(f'[CreateOrder] Raw request.data: {dict(request.data)}')
        
        serializer = OrderCreateSerializer(data=request.data)
        is_valid = serializer.is_valid()
        logger.info(f'[CreateOrder] Serializer valid: {is_valid}')
        if not is_valid:
            logger.error(f'[CreateOrder] Validation errors: {serializer.errors}')
        serializer.is_valid(raise_exception=True)
        
        try:
            with transaction.atomic():
                market_id = serializer.validated_data['market_id']
                delivery_address_id = serializer.validated_data['delivery_address_id']
                customer_lat = serializer.validated_data['customer_latitude']
                customer_lon = serializer.validated_data['customer_longitude']
                raw_fee = serializer.validated_data.get('delivery_fee')
                logger.info(f'[CreateOrder] Raw delivery_fee from serializer: {raw_fee} (type: {type(raw_fee).__name__})')
                
                delivery_fee = validate_and_normalize_delivery_fee(raw_fee)
                logger.info(f'[CreateOrder] After normalization: {delivery_fee} (type: {type(delivery_fee).__name__})')
                
                # Get location name from request (from Flutter app)
                delivery_location_name = serializer.validated_data.get('delivery_location_name', 'Delivery Location')
                logger.info(f'[CreateOrder] Delivery location name from app: {delivery_location_name}')
                
                payment_method = serializer.validated_data['payment_method']
                
                logger.info(f'[CreateOrder] ===== ORDER PARAMETERS =====')
                logger.info(f'[CreateOrder] Market: {market_id}')
                logger.info(f'[CreateOrder] Latitude: {customer_lat}')
                logger.info(f'[CreateOrder] Longitude: {customer_lon}')
                logger.info(f'[CreateOrder] Delivery Fee: {delivery_fee}')
                logger.info(f'[CreateOrder] Payment: {payment_method}')
                
                # Get cart
                try:
                    cart = Cart.objects.get(
                        customer=request.user,
                        market_id=market_id
                    )
                except Cart.DoesNotExist:
                    return Response(
                        {'error': 'Cart not found for this market'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if not cart.items.exists():
                    return Response(
                        {'error': 'Cart is empty'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get or create delivery address
                delivery_address = None
                try:
                    # Try to get existing address
                    delivery_address = CustomerAddress.objects.get(
                        id=delivery_address_id,
                        customer=request.user
                    )
                    logger.info(f'[CreateOrder] Using existing delivery address: {delivery_address_id}')
                except CustomerAddress.DoesNotExist:
                    # Address doesn't exist - create a temporary one from coordinates
                    logger.info(f"[CreateOrder] Creating temporary delivery address for coordinates ({customer_lat}, {customer_lon})")
                    
                    # Get market for the address
                    try:
                        market = Market.objects.get(id=market_id)
                    except Market.DoesNotExist:
                        return Response(
                            {'error': 'Market not found'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                    
                    # Create temporary address
                    from django.contrib.gis.geos import Point
                    location_point = Point(float(customer_lon), float(customer_lat))
                    
                    # Find delivery zone for this location
                    delivery_zone = None
                    try:
                        from django.contrib.gis.db.models.functions import Distance
                        # Find zones that contain this point or are closest
                        delivery_zones = DeliveryZone.objects.filter(
                            market_id=market_id
                        ).annotate(
                            distance=Distance('coverage_area', location_point)
                        ).order_by('distance')
                        
                        if delivery_zones.exists():
                            # Check if point is within any zone
                            for zone in delivery_zones:
                                if zone.coverage_area and zone.coverage_area.contains(location_point):
                                    delivery_zone = zone
                                    break
                            # If not in any zone, use closest
                            if not delivery_zone:
                                delivery_zone = delivery_zones.first()
                    except Exception as e:
                        logger.warning(f"Could not determine delivery zone: {e}")
                    
                    # Create the temporary address
                    delivery_address = CustomerAddress.objects.create(
                        id=delivery_address_id,
                        customer=request.user,
                        market=market,
                        label=delivery_location_name,
                        street_address="Location from app",
                        latitude=customer_lat,
                        longitude=customer_lon,
                        location_point=location_point,
                        delivery_zone=delivery_zone
                    )
                    logger.info(f"[CreateOrder] Temporary address created with name '{delivery_location_name}': {delivery_address.id}")
                
                # Stock validation removed - ProductVariant no longer has stock field
                # Orders can be placed freely, stock management happens at vendor level
                
                # Calculate items total from cart
                items_total = Decimal('0.00')
                logger.info(f'[CreateOrder] ===== CALCULATING ITEMS TOTAL =====')
                for cart_item in cart.items.all():
                    item_subtotal = cart_item.quantity * cart_item.unit_price + cart_item.addons_total
                    logger.info(f'[CreateOrder] Cart item: qty={cart_item.quantity}, unit_price={cart_item.unit_price}, addons={cart_item.addons_total}, subtotal={item_subtotal}')
                    items_total += item_subtotal
                
                logger.info(f'[CreateOrder] Final items_total: {items_total} (type: {type(items_total).__name__})')
                
                # Use the delivery fee from app (already validated)
                # DO NOT recalculate - trust the app's calculation
                logger.info(f'[CreateOrder] ===== USING DELIVERY FEE =====')
                logger.info(f'[CreateOrder] Using delivery_fee from app: {delivery_fee} (type: {type(delivery_fee).__name__})')
                
                # Calculate order totals using helper function
                logger.info(f'[CreateOrder] ===== CALLING CALCULATE_ORDER_TOTALS HELPER =====')
                totals = calculate_order_totals(
                    items_total=items_total,
                    delivery_fee=delivery_fee,
                    service_fee=Decimal('0.00'),
                    discount_amount=Decimal('0.00')
                )
                logger.info(f'[CreateOrder] ===== TOTALS FROM HELPER =====')
                logger.info(f'[CreateOrder] items_total: {totals["items_total"]}')
                logger.info(f'[CreateOrder] delivery_fee: {totals["delivery_fee"]}')
                logger.info(f'[CreateOrder] service_fee: {totals["service_fee"]}')
                logger.info(f'[CreateOrder] total_amount: {totals["total_amount"]}')
                
                # Create order with complete delivery location details for driver tracking
                logger.info(f'[CreateOrder] ===== CREATING ORDER OBJECT =====')
                logger.info(f'[CreateOrder] About to save Order with:')
                logger.info(f'  items_total: {totals["items_total"]}')
                logger.info(f'  delivery_fee: {totals["delivery_fee"]}')
                logger.info(f'  service_fee: {totals["service_fee"]}')
                logger.info(f'  total_amount: {totals["total_amount"]}')
                
                order = Order.objects.create(
                    customer=request.user,
                    delivery_address=delivery_address,
                    # Store delivery location details directly for quick driver access
                    delivery_location_name=delivery_location_name,
                    delivery_latitude=Decimal(str(customer_lat)),
                    delivery_longitude=Decimal(str(customer_lon)),
                    delivery_street_address=getattr(delivery_address, 'street_address', ''),
                    items_total=totals['items_total'],
                    delivery_fee=totals['delivery_fee'],
                    service_fee=totals['service_fee'],
                    total_amount=totals['total_amount'],
                    payment_method=payment_method,
                    status='pending',
                    scheduled_delivery_date=timezone.now().date(),
                    scheduled_delivery_time='TBD'
                )
                logger.info(f'[CreateOrder] ===== ORDER CREATED =====')
                logger.info(f'[CreateOrder] Order ID: {order.id}')
                logger.info(f'[CreateOrder] Order Number: {order.order_number}')
                logger.info(f'[CreateOrder] Saved in DB - items_total: {order.items_total}')
                logger.info(f'[CreateOrder] Saved in DB - delivery_fee: {order.delivery_fee}')
                logger.info(f'[CreateOrder] Saved in DB - total_amount: {order.total_amount}')
                
                # Copy cart items to order items
                for cart_item in cart.items.all():
                    order_item = OrderItem.objects.create(
                        order=order,
                        product_variant=cart_item.product_variant,
                        measurement_unit=cart_item.measurement_unit,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.unit_price,
                        addons_total=cart_item.addons_total,
                        special_instructions=cart_item.special_instructions
                    )
                    order_item.selected_addons.set(cart_item.selected_addons.all())
                
                # Clear cart after order creation
                cart.delete()
                
                logger.info(f"[CreateOrder] Order {order.order_number} created successfully")
                logger.info(f"[CreateOrder] Order totals - Items: {totals['items_total']}, Delivery: {totals['delivery_fee']}, Total: {totals['total_amount']}")
                
                return Response({
                    'message': 'Order created successfully',
                    'order': OrderDetailSerializer(order).data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.exception(f"Error creating order: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        """Cancel order (before confirmation)"""
        try:
            order = Order.objects.get(id=pk, customer=request.user)
            
            if order.status not in ['pending', 'confirmed']:
                return Response(
                    {'error': 'Only pending or confirmed orders can be cancelled'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            order.status = 'cancelled'
            order.cancellation_reason = request.data.get('reason', '')
            order.cancelled_at = timezone.now()
            order.save()
            
            return Response({
                'message': 'Order cancelled',
                'order': OrderDetailSerializer(order).data
            })
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================
# DRIVER AUTHENTICATION & PROFILE
# ============================================

class DriverLoginView(generics.GenericAPIView):
    """Driver login with phone number - initiates OTP via email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/v1/driver/login/
        {
            "phone_number": "+255712345678"
        }
        Returns: {
            "phone_number": "+255712345678",
            "message": "OTP sent to your email address",
            "email": "driver@example.com",
            "is_approved": true
        }
        """
        from .email_service import OTPService
        
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response(
                {'error': 'phone_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(phone_number=phone_number, user_type='driver')
            driver = user.driver
            
            # Check if driver is approved
            if driver.is_approved != 'approved':
                status_msg = 'Your account is pending approval. Please wait for admin approval.'
                if driver.is_approved == 'rejected':
                    status_msg = f'Your account was rejected. Reason: {driver.rejection_reason or "Not specified"}'
                
                return Response({
                    'error': status_msg,
                    'is_approved': False,
                    'approval_status': driver.is_approved,
                    'phone_number': phone_number
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if email exists
            if not user.email:
                return Response(
                    {'error': 'No email address on file. Please update your profile.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate OTP
            otp = OTPService.generate_otp()
            
            # Store OTP in session (with expiry handled by Django session timeout)
            request.session['driver_otp'] = otp
            request.session['driver_phone'] = phone_number
            request.session['driver_email'] = user.email
            
            # Send OTP via email
            email_sent = OTPService.send_driver_otp_email(
                email=user.email,
                phone_number=phone_number,
                otp=otp
            )
            
            if email_sent:
                return Response({
                    'phone_number': phone_number,
                    'email': user.email,
                    'is_approved': True,
                    'message': f'Login code sent to {user.email}. Check your email for the 6-digit code.',
                    'note': f'Code expires in {getattr(settings, "OTP_EXPIRY_MINUTES", 10)} minutes'
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Failed to send OTP email. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Driver not found. Please register first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DriverVerifyOTPView(generics.GenericAPIView):
    """Verify OTP sent via email and get JWT tokens"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/v1/driver/verify-otp/
        {
            "phone_number": "+255712345678",
            "otp": "123456"
        }
        Returns: {
            "access": "<jwt_token>",
            "refresh": "<refresh_token>",
            "driver_id": "<uuid>",
            "phone_number": "+255712345678",
            "email": "driver@example.com",
            "message": "Authentication successful"
        }
        """
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')
        
        if not phone_number or not otp:
            return Response(
                {'error': 'phone_number and otp are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify OTP from session
        session_otp = request.session.get('driver_otp')
        session_phone = request.session.get('driver_phone')
        
        if not session_otp or session_otp != otp:
            return Response(
                {'error': 'Invalid or expired OTP. Please request a new code.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if session_phone != phone_number:
            return Response(
                {'error': 'Phone number mismatch. Please use the same phone number.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            user = User.objects.get(phone_number=phone_number, user_type='driver')
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Clear session OTP data
            session_keys_to_delete = ['driver_otp', 'driver_phone', 'driver_email']
            for key in session_keys_to_delete:
                if key in request.session:
                    del request.session[key]
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'driver_id': str(user.id),
                'phone_number': user.phone_number,
                'email': user.email,
                'message': 'Authentication successful'
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {'error': 'Driver not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DriverProfileView(generics.RetrieveUpdateAPIView):
    """Get/Update driver profile"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get driver object"""
        if not hasattr(self.request.user, 'driver'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only drivers can access this endpoint")
        return self.request.user.driver
    
    def get(self, request, *args, **kwargs):
        """GET /api/v1/driver/profile/"""
        try:
            driver = self.get_object()
            from .serializers import DriverProfileSerializer
            serializer = DriverProfileSerializer(driver)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    def patch(self, request, *args, **kwargs):
        """PATCH /api/v1/driver/profile/ - Update driver profile"""
        try:
            driver = self.get_object()
            from .serializers import DriverProfileSerializer
            
            # Only allow updating certain fields
            allowed_fields = ['names', 'vehicle_type', 'vehicle_plate', 'is_available']
            data = {k: v for k, v in request.data.items() if k in allowed_fields}
            
            serializer = DriverProfileSerializer(driver, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            return Response({
                'message': 'Profile updated successfully',
                'driver': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DriverUpdateLocationView(generics.GenericAPIView):
    """Update driver's current location"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/v1/driver/update-location/
        {
            "latitude": 6.7924,
            "longitude": 39.2083,
            "is_online": true
        }
        """
        if not hasattr(request.user, 'driver'):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        is_online = request.data.get('is_online', True)
        
        if latitude is None or longitude is None:
            return Response(
                {'error': 'latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            driver = request.user.driver
            driver.is_available = is_online
            driver.save()
            
            # TODO: Update location in Redis/Cache for real-time tracking
            
            return Response({
                'message': 'Location updated',
                'latitude': latitude,
                'longitude': longitude,
                'is_online': is_online
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DriverStatsView(generics.GenericAPIView):
    """Get driver delivery statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/v1/driver/stats/ - Get driver statistics"""
        if not hasattr(request.user, 'driver'):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            driver = request.user.driver
            
            # Get statistics
            total_deliveries = Order.objects.filter(
                driver=request.user,
                status='delivered'
            ).count()
            
            pending_deliveries = Order.objects.filter(
                driver=request.user,
                status__in=['assigned', 'picked_up', 'on_the_way']
            ).count()
            
            failed_deliveries = Order.objects.filter(
                driver=request.user,
                status='failed'
            ).count()
            
            return Response({
                'total_deliveries': total_deliveries,
                'pending_deliveries': pending_deliveries,
                'failed_deliveries': failed_deliveries,
                'is_available': driver.is_available,
                'is_verified': driver.is_verified
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================
# DRIVER VIEWSET
# ============================================

class DriverOrderViewSet(viewsets.GenericViewSet):
    """Driver order delivery endpoints"""
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()
    serializer_class = DriverOrderDetailSerializer
    
    def check_driver_permission(self, request):
        """Verify user is a driver"""
        if not hasattr(request.user, 'driver'):
            return False
        return True
    
    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Get assigned orders for driver"""
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get pending and in-progress orders
        orders = Order.objects.filter(
            driver=request.user,
            status__in=['assigned', 'picked_up', 'on_the_way']
        ).prefetch_related('items').order_by('-assigned_at')
        
        serializer = DriverOrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_orders(self, request):
        """Get available orders for driver pickup"""
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get orders ready for pickup (not yet assigned)
        orders = Order.objects.filter(
            status__in=['confirmed', 'preparing', 'ready'],
            driver__isnull=True
        ).prefetch_related('items').order_by('-created_at')
        
        serializer = DriverOrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get order details for driver"""
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            order = Order.objects.get(
                id=pk,
                driver=request.user
            )
            serializer = DriverOrderDetailSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview available order details BEFORE accepting
        
        Allow driver to see full order details (items, map, address, etc.)
        before deciding to accept the order
        """
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Allow preview for orders that are available to drivers (confirmed, preparing, ready)
            order = Order.objects.get(
                id=pk, 
                status__in=['confirmed', 'preparing', 'ready'],
                driver__isnull=True  # Not yet assigned to a driver
            )
            serializer = DriverOrderDetailSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found or not available for preview'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def accept_order(self, request, pk=None):
        """Driver accepts order for delivery"""
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            order = Order.objects.get(id=pk)
            
            if order.driver is not None:
                return Response(
                    {'error': 'Order already assigned to another driver'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            order.driver = request.user
            order.status = 'assigned'
            order.assigned_at = timezone.now()
            order.save()
            
            return Response({
                'message': 'Order accepted',
                'order': DriverOrderDetailSerializer(order).data
            })
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order delivery status"""
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'error': 'status field required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = ['picked_up', 'on_the_way', 'delivered', 'failed']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=pk, driver=request.user)
            order.status = new_status
            
            if new_status == 'delivered':
                order.delivered_at = timezone.now()
            elif new_status == 'failed':
                order.cancellation_reason = request.data.get('reason', '')
            
            order.save()
            
            return Response({
                'message': f'Order status updated to {new_status}',
                'order': DriverOrderDetailSerializer(order).data
            })
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """
        Update driver's current location for real-time tracking
        
        Called every 2 minutes from driver app to update location
        Customer app uses this data to show driver location on map
        
        Endpoint: POST /api/v1/driver/orders/{order_id}/update_location/
        
        Request body:
        {
            'latitude': float,
            'longitude': float
        }
        """
        if not self.check_driver_permission(request):
            return Response(
                {'error': 'Only drivers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude is None or longitude is None:
            return Response(
                {'error': 'latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .driver_order_helpers import record_driver_location
            
            order = Order.objects.get(id=pk, driver=request.user)
            
            # Record location (will be expanded with proper tracking model)
            result = record_driver_location(order, latitude, longitude)
            
            return Response({
                'message': 'Location updated',
                'status': result.get('status'),
                'timestamp': result.get('timestamp')
            })
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FavoritesViewSet(viewsets.ViewSet):
    """Favorite items management for logged-in customers"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def list_favorites(self, request):
        """Get all favorites for current customer"""
        try:
            customer = Customer.objects.get(user=request.user)
            favorites = FavoriteItem.objects.filter(customer=customer).select_related('product')
            serializer = FavoriteItemSerializer(favorites, many=True)
            
            return Response({
                'count': favorites.count(),
                'favorites': serializer.data
            })
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def add_favorite(self, request):
        """Add product to favorites"""
        try:
            customer = Customer.objects.get(user=request.user)
            product_id = request.data.get('product_id')
            
            if not product_id:
                return Response(
                    {'error': 'product_id field required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            product = ProductTemplate.objects.get(id=product_id)
            
            # Check if already favorited
            favorite, created = FavoriteItem.objects.get_or_create(
                customer=customer,
                product=product
            )
            
            if created:
                logger.info(f"Customer {customer.id} added product {product.id} to favorites")
                return Response({
                    'message': 'Product added to favorites',
                    'favorite': FavoriteItemSerializer(favorite).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'message': 'Product already in favorites',
                    'favorite': FavoriteItemSerializer(favorite).data
                }, status=status.HTTP_200_OK)
        
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ProductTemplate.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def remove_favorite(self, request):
        """Remove product from favorites"""
        try:
            customer = Customer.objects.get(user=request.user)
            product_id = request.query_params.get('product_id')
            
            if not product_id:
                return Response(
                    {'error': 'product_id query parameter required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            favorite = FavoriteItem.objects.get(
                customer=customer,
                product_id=product_id
            )
            
            favorite.delete()
            logger.info(f"Customer {customer.id} removed product {product_id} from favorites")
            
            return Response({'message': 'Product removed from favorites'})
        
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except FavoriteItem.DoesNotExist:
            return Response(
                {'error': 'Product not in favorites'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def is_favorite(self, request):
        """Check if product is in favorites"""
        try:
            customer = Customer.objects.get(user=request.user)
            product_id = request.data.get('product_id')
            
            if not product_id:
                return Response(
                    {'error': 'product_id field required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            is_favorited = FavoriteItem.objects.filter(
                customer=customer,
                product_id=product_id
            ).exists()
            
            return Response({
                'product_id': product_id,
                'is_favorite': is_favorited
            })
        
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DriverRegistrationView(generics.GenericAPIView):
    """Driver self-registration with email OTP verification"""
    permission_classes = [AllowAny]
    serializer_class = None  # We'll use a custom serializer
    
    def post(self, request):
        """
        POST /api/v1/driver/register/
        {
            "phone_number": "+255712345678",
            "email": "driver@example.com",
            "password": "securepassword",
            "confirm_password": "securepassword",
            "names": "John Doe",
            "license_number": "DL123456",
            "vehicle_type": "motorcycle",
            "vehicle_plate": "ABC123"
        }
        Returns: {
            "message": "Registration successful. Awaiting admin approval.",
            "driver_id": "<uuid>",
            "phone_number": "+255712345678",
            "email": "driver@example.com",
            "approval_status": "pending"
        }
        """
        from accounts.serializers import DriverRegistrationSerializer
        
        serializer = DriverRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                driver = serializer.save()
                
                return Response({
                    'message': 'Registration successful! Your account is pending admin approval.',
                    'driver_id': str(driver.user.id),
                    'phone_number': driver.user.phone_number,
                    'email': driver.user.email,
                    'approval_status': 'pending',
                    'note': 'You will be able to login and view orders once your account is approved by an admin.'
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response(
                    {'error': f'Registration failed: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


class DriverDetailsView(generics.RetrieveAPIView):
    """Get current driver details including approval status"""
    permission_classes = [IsAuthenticated]
    serializer_class = DriverProfileSerializer
    
    def get_object(self):
        try:
            return self.request.user.driver
        except Driver.DoesNotExist:
            raise Http404("Driver profile not found")
    
    def retrieve(self, request, *args, **kwargs):
        driver = self.get_object()
        
        return Response({
            'driver_id': str(driver.user.id),
            'phone_number': driver.user.phone_number,
            'email': driver.user.email,
            'names': driver.names,
            'license_number': driver.license_number,
            'vehicle_type': driver.vehicle_type,
            'vehicle_plate': driver.vehicle_plate,
            'is_approved': driver.is_approved,
            'is_available': driver.is_available,
            'is_verified': driver.is_verified,
            'approval_status': driver.get_is_approved_display(),
            'rejection_reason': driver.rejection_reason,
            'approved_at': driver.approved_at,
            'created_at': driver.created_at
        }, status=status.HTTP_200_OK)

