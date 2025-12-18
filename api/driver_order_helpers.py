"""
Driver Order Helper Functions - Backend Logic
================================================

This module provides helper functions for driver order delivery system:
1. Order data formatting and serialization
2. Location calculations (market to delivery distance/coordinates)
3. Item filtering and quantity validation
4. Location tracking and distance calculations
5. Order status and totals calculation
"""

from decimal import Decimal
from django.utils import timezone
from geopy.distance import geodesic
from order.models import Order, OrderItem
from products.models import MeasurementUnit
import logging

logger = logging.getLogger(__name__)


# ============================================
# 1. LOCATION HELPERS
# ============================================

def get_market_location(order):
    """
    Extract market location from order items
    
    Args:
        order (Order): The order instance
    
    Returns:
        dict: {
            'name': str,
            'latitude': float,
            'longitude': float,
            'address': str
        }
    
    Logic:
    - Get first order item's vendor
    - Fetch vendor's associated market
    - Return market coordinates and name
    - Fallback to default if no market found
    """
    if not order.items.exists():
        return {
            'name': 'Market',
            'latitude': -6.8,
            'longitude': 39.2,
            'address': 'Default Market Location'
        }
    
    try:
        first_item = order.items.first()
        vendor = first_item.product_variant.vendor
        
        # Get vendor's market
        if hasattr(vendor, 'market') and vendor.market:
            market = vendor.market
            return {
                'name': market.name,
                'latitude': float(market.latitude) if market.latitude else -6.8,
                'longitude': float(market.longitude) if market.longitude else 39.2,
                'address': market.address or market.location or 'Market Location'
            }
    except Exception as e:
        logger.warning(f"Error getting market location: {e}")
    
    # Fallback
    return {
        'name': 'Market',
        'latitude': -6.8,
        'longitude': 39.2,
        'address': 'Default Market Location'
    }


def get_delivery_location(order):
    """
    Extract delivery location from order
    
    Args:
        order (Order): The order instance
    
    Returns:
        dict: {
            'latitude': float,
            'longitude': float,
            'address': str,
            'location_name': str
        }
    
    Logic:
    - Use delivery_latitude and delivery_longitude from order
    - Build address from delivery_address and location_name
    """
    return {
        'latitude': float(order.delivery_latitude) if order.delivery_latitude else 0.0,
        'longitude': float(order.delivery_longitude) if order.delivery_longitude else 0.0,
        'address': order.delivery_street_address or 'Delivery Address',
        'location_name': order.delivery_location_name or 'Delivery Location'
    }


def calculate_distance_between_points(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates in kilometers
    
    Args:
        lat1, lon1: Market coordinates (floats)
        lat2, lon2: Delivery coordinates (floats)
    
    Returns:
        float: Distance in kilometers
    
    Logic:
    - Use geodesic formula for accurate earth distance
    - Handle invalid coordinates gracefully
    """
    try:
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
        
        point1 = (float(lat1), float(lon1))
        point2 = (float(lat2), float(lon2))
        
        distance = geodesic(point1, point2).kilometers
        return round(distance, 2)
    except Exception as e:
        logger.warning(f"Error calculating distance: {e}")
        return 0.0


# ============================================
# 2. ITEM FILTERING & VALIDATION
# ============================================

def get_valid_items(order):
    """
    Get only valid items (quantity > 0)
    
    Args:
        order (Order): The order instance
    
    Returns:
        QuerySet: OrderItems with quantity > 0
    
    Logic:
    - Filter items by quantity > 0
    - Exclude items with zero or negative quantities
    - Ordered by creation date
    """
    return order.items.filter(quantity__gt=0).order_by('created_at')


def format_order_item_for_display(item):
    """
    Format a single order item for driver display
    
    Args:
        item (OrderItem): The order item instance
    
    Returns:
        dict: {
            'id': str,
            'product_name': str,
            'product_image_url': str,
            'quantity': float,
            'measurement_unit': {
                'name': str,
                'symbol': str
            },
            'unit_price': Decimal,
            'total_price': Decimal,
            'addons': list,
            'special_instructions': str
        }
    
    Logic:
    - Extract product details
    - Include measurement unit info (essential for display)
    - Format prices as decimals
    - Include any addons selected
    """
    try:
        product = item.product_variant.product_template
        
        return {
            'id': str(item.id),
            'product_name': product.name,
            'product_image_url': product.main_image.url if product.main_image else None,
            'quantity': float(item.quantity),
            'measurement_unit': {
                'name': item.measurement_unit.name,
                'symbol': item.measurement_unit.symbol
            },
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price),
            'addons': [
                {
                    'name': addon.name,
                    'price': float(addon.price)
                }
                for addon in item.selected_addons.all()
            ],
            'special_instructions': item.special_instructions or ''
        }
    except Exception as e:
        logger.error(f"Error formatting item {item.id}: {e}")
        return {}


# ============================================
# 3. ORDER TOTALS CALCULATION
# ============================================

def calculate_items_total_only(order):
    """
    Calculate total from ONLY items (no fees)
    
    Args:
        order (Order): The order instance
    
    Returns:
        Decimal: Sum of all valid items' total_price
    
    Logic:
    - Get valid items (quantity > 0)
    - Sum their total_price field
    - Do NOT include delivery_fee, service_fee, discount
    - This is what driver sees and customer paid for items
    """
    valid_items = get_valid_items(order)
    items_total = sum(
        Decimal(str(item.total_price)) for item in valid_items
    ) or Decimal('0.00')
    return items_total


def get_order_summary_for_driver(order):
    """
    Get complete order summary for driver display
    
    Args:
        order (Order): The order instance
    
    Returns:
        dict: Complete order information
    
    Structure:
    {
        'id': str,
        'order_number': str,
        'customer': {...},
        'locations': {
            'market': {...},
            'delivery': {...},
            'distance_km': float
        },
        'items': [...],
        'items_total': Decimal,
        'payment_method': str,
        'is_paid': bool,
        'status': str,
        'scheduled_time': str,
        'notes': str
    }
    
    Logic:
    - Gather all information driver needs
    - Calculate locations and distance
    - Filter items
    - DO NOT include delivery_fee, service_fee
    - Include total amount only (items total)
    """
    market_location = get_market_location(order)
    delivery_location = get_delivery_location(order)
    
    distance = calculate_distance_between_points(
        market_location['latitude'],
        market_location['longitude'],
        delivery_location['latitude'],
        delivery_location['longitude']
    )
    
    items_total = calculate_items_total_only(order)
    valid_items = get_valid_items(order)
    
    return {
        'id': str(order.id),
        'order_number': order.order_number,
        'customer': {
            'name': order.customer.customer.names if hasattr(order.customer, 'customer') else 'Customer',
            'phone': order.customer.phone_number,
            'address': order.delivery_street_address or 'Delivery Address'
        },
        'locations': {
            'market': market_location,
            'delivery': delivery_location,
            'distance_km': distance
        },
        'items': [format_order_item_for_display(item) for item in valid_items],
        'items_total': float(items_total),
        'items_count': valid_items.count(),
        'payment_method': order.get_payment_method_display() if hasattr(order, 'get_payment_method_display') else order.payment_method,
        'is_paid': order.is_paid,
        'status': order.status,
        'scheduled_date': str(order.scheduled_delivery_date),
        'scheduled_time': order.scheduled_delivery_time
    }


# ============================================
# 4. LOCATION TRACKING
# ============================================

def record_driver_location(order, driver_latitude, driver_longitude):
    """
    Record driver's current location for order tracking
    
    Args:
        order (Order): The order instance
        driver_latitude (float): Current driver latitude
        driver_longitude (float): Current driver longitude
    
    Returns:
        dict: Status and saved location
    
    Logic:
    - Store driver location in a tracking model (if created)
    - Or update a field on the order/driver
    - Called every 2 minutes from driver app
    - Used to show customer driver's real-time location
    """
    try:
        # For now, log the location
        # In future: Create DriverLocationTracking model
        logger.info(
            f"Driver location: Order {order.order_number}, "
            f"Lat: {driver_latitude}, Lon: {driver_longitude}"
        )
        
        return {
            'status': 'recorded',
            'order_id': str(order.id),
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error recording driver location: {e}")
        return {'status': 'error', 'message': str(e)}


# ============================================
# 5. VALIDATION HELPERS
# ============================================

def validate_order_for_driver_pickup(order):
    """
    Validate if order is ready for driver pickup
    
    Args:
        order (Order): The order instance
    
    Returns:
        tuple: (is_valid, error_message)
    
    Logic:
    - Check order has valid items (qty > 0)
    - Check order has valid locations
    - Check driver is assigned
    - Check order status is valid
    """
    errors = []
    
    # Check items
    if not get_valid_items(order).exists():
        errors.append("Order has no valid items")
    
    # Check locations
    if not order.delivery_latitude or not order.delivery_longitude:
        errors.append("Delivery location not set")
    
    market_location = get_market_location(order)
    if market_location['latitude'] == -6.8 and market_location['longitude'] == 39.2:
        errors.append("Market location could not be determined")
    
    # Check status
    valid_statuses = ['assigned', 'picked_up', 'on_the_way']
    if order.status not in valid_statuses:
        errors.append(f"Order status '{order.status}' is not valid for delivery")
    
    return (len(errors) == 0, errors)


# ============================================
# 6. MEASUREMENT UNIT HELPERS
# ============================================

def get_measurement_unit_symbol(unit_id):
    """
    Get measurement unit symbol by ID
    
    Args:
        unit_id (str): MeasurementUnit ID
    
    Returns:
        str: Unit symbol (e.g., 'kg', 'L')
    """
    try:
        unit = MeasurementUnit.objects.get(id=unit_id)
        return unit.symbol
    except MeasurementUnit.DoesNotExist:
        return ''


# ============================================
# 7. DISTANCE-BASED HELPERS
# ============================================

def estimate_delivery_time(distance_km, avg_speed_kmh=20):
    """
    Estimate delivery time based on distance
    
    Args:
        distance_km (float): Distance in kilometers
        avg_speed_kmh (float): Average speed in km/h (default 20)
    
    Returns:
        dict: {
            'minutes': int,
            'estimated_arrival': datetime
        }
    
    Logic:
    - Simple calculation: distance / speed
    - Assumes urban delivery average of 20 km/h
    - Returns estimated arrival time
    """
    try:
        minutes = (distance_km / avg_speed_kmh) * 60
        arrival = timezone.now() + timezone.timedelta(minutes=minutes)
        
        return {
            'minutes': int(round(minutes)),
            'estimated_arrival': arrival.isoformat()
        }
    except Exception as e:
        logger.error(f"Error estimating delivery time: {e}")
        return {'minutes': 0, 'estimated_arrival': None}
