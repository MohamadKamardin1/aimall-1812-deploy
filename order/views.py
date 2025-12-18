from django.shortcuts import render

# Create your views here.
# order/views.py
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Order, OrderItem, ordertatusUpdate, Cart, CartItem
from location.models import CustomerAddress, DeliveryTimeSlot
from products.models import ProductVariant, MeasurementUnit, ProductAddon, UnitPrice
from .serializers import (
    ordererializer, Createordererializer, CartSerializer,
    CartItemSerializer, AddToCartSerializer, ordertatusUpdateSerializer
)

# ============ CART MANAGEMENT ============
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def cart_management(request):
    """Manage shopping cart"""
    customer = request.user
    
    # Get or create cart
    cart, created = Cart.objects.get_or_create(customer=customer)
    
    if request.method == 'GET':
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Add item to cart
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    product_variant = ProductVariant.objects.get(
                        id=serializer.validated_data['product_variant_id'],
                        is_active=True,
                        is_approved=True
                    )
                    measurement_unit = MeasurementUnit.objects.get(
                        id=serializer.validated_data['measurement_unit_id']
                    )
                    
                    # Check if item already in cart
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product_variant=product_variant,
                        measurement_unit=measurement_unit,
                        defaults={
                            'quantity': serializer.validated_data['quantity'],
                            'unit_price': product_variant.get_price_for_unit(measurement_unit),
                            'special_instructions': serializer.validated_data.get('special_instructions', '')
                        }
                    )
                    
                    if not created:
                        # Update existing item
                        cart_item.quantity += serializer.validated_data['quantity']
                        cart_item.unit_price = product_variant.get_price_for_unit(measurement_unit)
                        cart_item.special_instructions = serializer.validated_data.get('special_instructions', '')
                    
                    # Handle addons
                    addon_ids = serializer.validated_data.get('addon_ids', [])
                    addons_total = Decimal('0.00')
                    
                    if addon_ids:
                        addons = ProductAddon.objects.filter(id__in=addon_ids, is_active=True)
                        for addon in addons:
                            addons_total += addon.price
                    
                    cart_item.addons_total = addons_total
                    cart_item.selected_addons.set(addon_ids)
                    cart_item.save()
                    
                    # Update cart market if not set
                    if not cart.market:
                        cart.market = product_variant.market_zone.market
                        cart.save()
                    
                    return Response(CartSerializer(cart).data)
                    
            except (ProductVariant.DoesNotExist, MeasurementUnit.DoesNotExist) as e:
                return Response(
                    {'error': 'Product or measurement unit not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'PUT':
        # Update cart delivery info
        delivery_address_id = request.data.get('delivery_address')
        time_slot_id = request.data.get('delivery_time_slot')
        
        if delivery_address_id:
            try:
                address = CustomerAddress.objects.get(id=delivery_address_id, customer=customer)
                cart.delivery_address = address
                
                # Update market based on address
                if address.market != cart.market:
                    # Clear cart items if market changes
                    cart.items.all().delete()
                    cart.market = address.market
                
            except CustomerAddress.DoesNotExist:
                return Response(
                    {'error': 'Address not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        if time_slot_id:
            try:
                time_slot = DeliveryTimeSlot.objects.get(id=time_slot_id, is_active=True)
                cart.delivery_time_slot = time_slot
            except DeliveryTimeSlot.DoesNotExist:
                return Response(
                    {'error': 'Time slot not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        cart.save()
        return Response(CartSerializer(cart).data)
    
    elif request.method == 'DELETE':
        # Clear cart
        cart.items.all().delete()
        cart.delivery_address = None
        cart.delivery_time_slot = None
        cart.market = None
        cart.save()
        return Response({'message': 'Cart cleared successfully'})

@api_view(['PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def cart_item_detail(request, item_id):
    """Update or remove cart item"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__customer=request.user)
    except CartItem.DoesNotExist:
        return Response(
            {'error': 'Cart item not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'PUT':
        quantity = request.data.get('quantity')
        addon_ids = request.data.get('addon_ids', [])
        special_instructions = request.data.get('special_instructions', '')
        
        if quantity is not None:
            try:
                quantity = Decimal(quantity)
                if quantity <= 0:
                    cart_item.delete()
                    return Response({'message': 'Item removed from cart'})
                cart_item.quantity = quantity
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid quantity'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update addons
        if addon_ids:
            addons = ProductAddon.objects.filter(id__in=addon_ids, is_active=True)
            addons_total = sum(addon.price for addon in addons)
            cart_item.addons_total = addons_total
            cart_item.selected_addons.set(addons)
        
        if special_instructions is not None:
            cart_item.special_instructions = special_instructions
        
        cart_item.save()
        return Response(CartItemSerializer(cart_item).data)
    
    elif request.method == 'DELETE':
        cart_item.delete()
        return Response({'message': 'Item removed from cart'})

# ============ ORDER MANAGEMENT ============
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_order(request):
    """Create order from cart"""
    customer = request.user
    
    try:
        cart = Cart.objects.get(customer=customer)
        if cart.items.count() == 0:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart.delivery_address:
            return Response(
                {'error': 'Delivery address is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart.delivery_time_slot:
            return Response(
                {'error': 'Delivery time slot is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Calculate delivery time
            now = timezone.now()
            cutoff_time = cart.delivery_time_slot.cut_off_time
            
            if now.time() < cutoff_time:
                delivery_date = now.date()
            else:
                delivery_date = now.date() + timedelta(days=1)
            
            # Create order
            order = Order.objects.create(
                customer=customer,
                delivery_address=cart.delivery_address,
                delivery_time_slot=cart.delivery_time_slot,
                scheduled_delivery_date=delivery_date,
                scheduled_delivery_time=f"{cart.delivery_time_slot.delivery_start_time} - {cart.delivery_time_slot.delivery_end_time}",
                payment_method=request.data.get('payment_method', 'cash_on_delivery'),
                delivery_fee=cart.delivery_fee,
                service_fee=Decimal('0.00'),  # Can be configured
                discount_amount=Decimal('0.00'),  # Can add discount logic
            )
            
            # Create order items from cart
            items_total = Decimal('0.00')
            for cart_item in cart.items.all():
                # Check stock availability
                if cart_item.product_variant.current_stock < cart_item.quantity:
                    raise Exception(f"Insufficient stock for {cart_item.product_variant.product_template.name}")
                
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
                
                items_total += order_item.total_price
            
            # Update order totals
            order.items_total = items_total
            order.total_amount = items_total + order.delivery_fee + order.service_fee - order.discount_amount
            order.save()
            
            # Clear cart
            cart.items.all().delete()
            cart.delivery_address = None
            cart.delivery_time_slot = None
            cart.market = None
            cart.save()
            
            # Create initial status update
            ordertatusUpdate.objects.create(
                order=order,
                old_status='pending',
                new_status='pending',
                updated_by=customer,
                note='Order created'
            )
            
            return Response(
                ordererializer(order).data,
                status=status.HTTP_201_CREATED
            )
            
    except Cart.DoesNotExist:
        return Response(
            {'error': 'Cart not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_list(request):
    """Get customer's order"""
    order = Order.objects.filter(customer=request.user).select_related(
        'delivery_address', 'delivery_time_slot', 'driver'
    ).prefetch_related('items').order_by('-created_at')
    
    serializer = ordererializer(order, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_detail(request, order_id):
    """Get order details"""
    try:
        order = Order.objects.get(id=order_id, customer=request.user)
        serializer = ordererializer(order)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel order"""
    try:
        order = Order.objects.get(id=order_id, customer=request.user)
        
        if order.status not in ['pending', 'confirmed']:
            return Response(
                {'error': 'Order cannot be cancelled at this stage'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.cancellation_reason = request.data.get('reason', '')
        order.cancelled_at = timezone.now()
        order.save()
        
        # Create status update
        ordertatusUpdate.objects.create(
            order=order,
            old_status=order.status,
            new_status='cancelled',
            updated_by=request.user,
            note=f'Order cancelled: {order.cancellation_reason}'
        )
        
        return Response({'message': 'Order cancelled successfully'})
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

# ============ DRIVER ORDER MANAGEMENT ============
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def driver_order(request):
    """Get order assigned to driver"""
    if request.user.user_type != 'driver':
        return Response(
            {'error': 'Only drivers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    status_filter = request.GET.get('status', '')
    order = Order.objects.filter(driver=request.user)
    
    if status_filter:
        order = order.filter(status=status_filter)
    
    serializer = ordererializer(order, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status (for drivers and admins)"""
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.data.get('status')
        note = request.data.get('note', '')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions
        user = request.user
        if user.user_type not in ['admin', 'driver']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user.user_type == 'driver' and order.driver != user:
            return Response(
                {'error': 'You can only update your assigned order'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        old_status = order.status
        order.status = new_status
        
        # Update timestamps based on status
        now = timezone.now()
        if new_status == 'confirmed' and not order.confirmed_at:
            order.confirmed_at = now
        elif new_status == 'assigned' and not order.assigned_at:
            order.assigned_at = now
        elif new_status == 'picked_up' and not order.picked_up_at:
            order.picked_up_at = now
        elif new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = now
            # Auto-mark as paid for cash on delivery
            if order.payment_method == 'cash_on_delivery':
                order.is_paid = True
        
        order.save()
        
        # Create status update
        ordertatusUpdate.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            updated_by=user,
            note=note
        )
        
        return Response({'message': 'Order status updated successfully'})
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )