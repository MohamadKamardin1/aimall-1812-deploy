"""
Order creation helper functions for ensuring proper fee and total calculations
"""
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def calculate_order_totals(items_total, delivery_fee, service_fee=Decimal('0.00'), discount_amount=Decimal('0.00')):
    """
    Calculate complete order totals from components.
    
    Args:
        items_total (Decimal): Sum of all product item prices
        delivery_fee (Decimal): Delivery fee from app/calculation
        service_fee (Decimal): Service/platform fee (optional)
        discount_amount (Decimal): Discount applied (optional)
    
    Returns:
        dict: {
            'items_total': items total,
            'delivery_fee': delivery fee,
            'service_fee': service fee,
            'subtotal': items + delivery,
            'total_before_discount': items + delivery + service,
            'discount_amount': discount,
            'total_amount': final total after discount,
        }
    """
    try:
        # Ensure all values are Decimal
        items_total = Decimal(str(items_total)) if items_total else Decimal('0.00')
        delivery_fee = Decimal(str(delivery_fee)) if delivery_fee else Decimal('0.00')
        service_fee = Decimal(str(service_fee)) if service_fee else Decimal('0.00')
        discount_amount = Decimal(str(discount_amount)) if discount_amount else Decimal('0.00')
        
        # Log input values
        logger.info(f'[OrderHelpers] Input - Items: {items_total}, Delivery: {delivery_fee}, Service: {service_fee}, Discount: {discount_amount}')
        
        # Calculate intermediate totals
        subtotal = items_total + delivery_fee
        total_before_discount = items_total + delivery_fee + service_fee
        final_total = total_before_discount - discount_amount
        
        # Ensure no negative totals
        final_total = max(final_total, Decimal('0.00'))
        
        result = {
            'items_total': items_total,
            'delivery_fee': delivery_fee,
            'service_fee': service_fee,
            'subtotal': subtotal,
            'total_before_discount': total_before_discount,
            'discount_amount': discount_amount,
            'total_amount': final_total,
        }
        
        # Log output values
        logger.info(f'[OrderHelpers] Calculated - Subtotal: {subtotal}, Total Before Discount: {total_before_discount}, Final Total: {final_total}')
        
        return result
        
    except (ValueError, TypeError) as e:
        logger.error(f'[OrderHelpers] Error calculating totals: {e}')
        raise ValueError(f'Invalid input for total calculation: {e}')


def validate_and_normalize_delivery_fee(delivery_fee):
    """
    Validate and normalize delivery fee from Flutter app.
    
    Args:
        delivery_fee: Delivery fee value (can be float, string, or Decimal)
    
    Returns:
        Decimal: Normalized delivery fee (always 2 decimal places, minimum 0)
    """
    try:
        if delivery_fee is None:
            logger.warning('[OrderHelpers] Delivery fee is None, using 0.00')
            return Decimal('0.00')
        
        fee = Decimal(str(delivery_fee))
        
        # Ensure 2 decimal places
        fee = fee.quantize(Decimal('0.01'))
        
        # Ensure non-negative
        if fee < 0:
            logger.warning(f'[OrderHelpers] Negative delivery fee received: {fee}, using 0.00')
            return Decimal('0.00')
        
        logger.info(f'[OrderHelpers] Delivery fee validated: {fee}')
        return fee
        
    except (ValueError, TypeError) as e:
        logger.error(f'[OrderHelpers] Error validating delivery fee: {e}')
        raise ValueError(f'Invalid delivery fee: {e}')


def format_order_response(order_instance):
    """
    Format order instance into a clean response dict with properly calculated totals.
    
    Args:
        order_instance: Order model instance
    
    Returns:
        dict: Clean order data for API response
    """
    try:
        # Get items total from order items
        items_total = Decimal('0.00')
        for item in order_instance.items.all():
            items_total += item.total_price if hasattr(item, 'total_price') else (item.unit_price * item.quantity)
        
        # Get delivery fee from order
        delivery_fee = order_instance.delivery_fee or Decimal('0.00')
        service_fee = order_instance.service_fee or Decimal('0.00')
        discount_amount = order_instance.discount_amount or Decimal('0.00')
        
        # Calculate totals
        totals = calculate_order_totals(items_total, delivery_fee, service_fee, discount_amount)
        
        # Update order with calculated values if they differ
        if order_instance.items_total != totals['items_total']:
            order_instance.items_total = totals['items_total']
            order_instance.delivery_fee = totals['delivery_fee']
            order_instance.total_amount = totals['total_amount']
            order_instance.save()
            logger.info(f'[OrderHelpers] Updated order {order_instance.order_number} totals')
        
        response_data = {
            'order_number': order_instance.order_number,
            'id': str(order_instance.id),
            'customer_phone': order_instance.customer.phone_number,
            'items_total': str(totals['items_total']),
            'delivery_fee': str(totals['delivery_fee']),
            'service_fee': str(totals['service_fee']),
            'subtotal': str(totals['subtotal']),
            'discount_amount': str(totals['discount_amount']),
            'total_amount': str(totals['total_amount']),
            'payment_method': order_instance.payment_method,
            'status': order_instance.status,
            'created_at': order_instance.created_at.isoformat() if order_instance.created_at else None,
            'delivery_location_name': order_instance.delivery_location_name,
            'delivery_latitude': str(order_instance.delivery_latitude) if order_instance.delivery_latitude else None,
            'delivery_longitude': str(order_instance.delivery_longitude) if order_instance.delivery_longitude else None,
        }
        
        logger.info(f'[OrderHelpers] Order response formatted: {response_data}')
        return response_data
        
    except Exception as e:
        logger.error(f'[OrderHelpers] Error formatting order response: {e}')
        raise


