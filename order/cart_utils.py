"""
Cart utilities and helper functions for calculations and validations
"""
from decimal import Decimal
from django.db.models import Sum, F
from products.models import UnitPrice, ProductAddon, MeasurementUnit
from order.models import CartItem


class CartCalculations:
    """Helper class for cart calculations"""
    
    @staticmethod
    def calculate_item_total(unit_price: Decimal, quantity: Decimal, addons_total: Decimal = None) -> Decimal:
        """Calculate total price for a cart item"""
        item_total = unit_price * quantity
        if addons_total:
            item_total += addons_total
        return item_total.quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_addons_total(addons: list, quantity: Decimal = Decimal('1')) -> Decimal:
        """Calculate total addon price"""
        if not addons:
            return Decimal('0.00')
        total = sum(addon.price for addon in addons if addon.is_active)
        return (total * quantity).quantize(Decimal('0.01'))
    
    @staticmethod
    def get_cart_subtotal(cart) -> Decimal:
        """Get cart subtotal from all items"""
        subtotal = cart.items.aggregate(
            total=Sum(F('total_price'))
        )['total'] or Decimal('0.00')
        return subtotal.quantize(Decimal('0.01'))
    
    @staticmethod
    def get_cart_item_count(cart) -> int:
        """Get total item count in cart"""
        return cart.items.count()
    
    @staticmethod
    def get_cart_quantity_total(cart) -> Decimal:
        """Get total quantity of all items (by units, not count)"""
        total_qty = cart.items.aggregate(
            total=Sum('quantity')
        )['total'] or Decimal('0.00')
        return total_qty.quantize(Decimal('0.001'))
    
    @staticmethod
    def validate_unit_price_exists(product_variant, unit) -> UnitPrice:
        """Validate and get unit price for a product variant"""
        try:
            return UnitPrice.objects.get(
                product_variant=product_variant,
                unit=unit,
                is_active=True
            )
        except UnitPrice.DoesNotExist:
            raise ValueError(
                f"Unit price not found for product {product_variant.id} with unit {unit.id}"
            )
    
    @staticmethod
    def validate_addons(addon_ids: list) -> list:
        """Validate and return active addons"""
        if not addon_ids:
            return []
        
        addons = ProductAddon.objects.filter(
            id__in=addon_ids,
            is_active=True
        )
        
        if len(addons) != len(addon_ids):
            invalid_ids = set(addon_ids) - set(addons.values_list('id', flat=True))
            raise ValueError(f"Invalid or inactive addon IDs: {invalid_ids}")
        
        return list(addons)
    
    @staticmethod
    def validate_quantity(quantity: Decimal, min_value: Decimal = Decimal('0.001')) -> bool:
        """Validate quantity is greater than minimum"""
        return quantity >= min_value


class CartItemHelper:
    """Helper methods for cart item operations"""
    
    @staticmethod
    def get_item_details(cart_item: CartItem) -> dict:
        """Get comprehensive item details for serialization"""
        return {
            'id': str(cart_item.id),
            'product_id': str(cart_item.product_variant.product_template.id),
            'product_name': cart_item.product_variant.product_template.name,
            'variant_id': str(cart_item.product_variant.id),
            'vendor_name': cart_item.product_variant.vendor.business_name,
            'vendor_id': str(cart_item.product_variant.vendor.user_id),
            'unit_id': str(cart_item.measurement_unit.id),
            'unit_symbol': cart_item.measurement_unit.symbol,
            'unit_name': cart_item.measurement_unit.name,
            'quantity': str(cart_item.quantity),
            'unit_price': float(cart_item.unit_price),
            'addons_total': float(cart_item.addons_total),
            'total_price': float(cart_item.total_price),
            'addons': [{
                'id': str(addon.id),
                'name': addon.name,
                'price': float(addon.price),
            } for addon in cart_item.selected_addons.all()],
            'special_instructions': cart_item.special_instructions,
        }
    
    @staticmethod
    def update_item_quantity(cart_item: CartItem, new_quantity: Decimal) -> CartItem:
        """Update cart item quantity and recalculate totals"""
        if not CartCalculations.validate_quantity(new_quantity):
            raise ValueError("Quantity must be greater than 0")
        
        cart_item.quantity = new_quantity
        # Recalculate addons total based on new quantity
        addon_price_per_unit = Decimal('0.00')
        if cart_item.selected_addons.exists():
            addon_price_per_unit = sum(
                addon.price for addon in cart_item.selected_addons.all()
            )
        cart_item.addons_total = (addon_price_per_unit * new_quantity).quantize(Decimal('0.01'))
        cart_item.save()
        return cart_item
    
    @staticmethod
    def format_for_display(cart_item: CartItem) -> dict:
        """Format cart item for frontend display"""
        return {
            'id': str(cart_item.id),
            'product_name': cart_item.product_variant.product_template.name,
            'vendor_name': cart_item.product_variant.vendor.business_name,
            'image_url': str(cart_item.product_variant.product_template.main_image.url) if cart_item.product_variant.product_template.main_image else None,
            'unit_symbol': cart_item.measurement_unit.symbol,
            'quantity': float(cart_item.quantity),
            'unit_price': float(cart_item.unit_price),
            'price_display': f"TZS {cart_item.unit_price:.0f} /per {cart_item.measurement_unit.symbol}",
            'total_price': float(cart_item.total_price),
            'addons_count': cart_item.selected_addons.count(),
        }


class CartService:
    """High-level cart operations service"""
    
    @staticmethod
    def add_to_cart(cart, product_variant, unit, quantity: Decimal, addons=None, instructions=""):
        """Add item to cart with full validation and calculation"""
        
        # Validate unit price exists
        unit_price_obj = CartCalculations.validate_unit_price_exists(product_variant, unit)
        
        # Validate quantity
        if not CartCalculations.validate_quantity(quantity):
            raise ValueError("Invalid quantity")
        
        # Calculate addon total
        addons_list = []
        if addons:
            addons_list = CartCalculations.validate_addons(addons)
        addons_total = CartCalculations.calculate_addons_total(addons_list, quantity)
        
        # Create or update cart item
        cart_item, created = CartItem.objects.update_or_create(
            cart=cart,
            product_variant=product_variant,
            measurement_unit=unit,
            defaults={
                'quantity': quantity,
                'unit_price': unit_price_obj.selling_price,
                'addons_total': addons_total,
                'special_instructions': instructions,
            }
        )
        
        # Set addons
        if addons_list:
            cart_item.selected_addons.set(addons_list)
        
        return cart_item
    
    @staticmethod
    def remove_from_cart(cart, cart_item_id):
        """Remove item from cart"""
        try:
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            raise ValueError(f"Cart item {cart_item_id} not found")
    
    @staticmethod
    def clear_cart(cart):
        """Clear all items from cart"""
        cart.items.all().delete()
        return cart
    
    @staticmethod
    def get_cart_summary(cart) -> dict:
        """Get complete cart summary"""
        items = cart.items.all()
        subtotal = CartCalculations.get_cart_subtotal(cart)
        delivery_fee = cart.delivery_fee
        
        return {
            'items_count': CartCalculations.get_cart_item_count(cart),
            'quantity_total': float(CartCalculations.get_cart_quantity_total(cart)),
            'subtotal': float(subtotal),
            'delivery_fee': float(delivery_fee),
            'total': float(subtotal + delivery_fee),
            'items': [CartItemHelper.get_item_details(item) for item in items],
        }
