from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, Cart, CartItem, OrderStatusUpdate

class OrderItemInline(admin.TabularInline):
    """Inline display of order items within order admin"""
    model = OrderItem
    extra = 0
    fields = ('product_variant', 'measurement_unit', 'quantity', 'unit_price', 'addons_total', 'total_price')
    readonly_fields = ('total_price',)
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Complete order management in Django admin"""
    list_display = (
        'order_number_colored', 'customer_phone', 'status_colored', 
        'items_total_display', 'delivery_fee_display', 'total_amount_colored', 
        'payment_method', 'created_at_short'
    )
    list_filter = ('status', 'payment_method', 'is_paid', 'created_at')
    search_fields = ('order_number', 'customer__phone_number', 'customer__customer__names')
    
    # Only include actual model fields in readonly_fields, not methods
    readonly_fields = (
        'id', 'order_number', 'items_total', 'delivery_fee', 'service_fee',
        'discount_amount', 'total_amount', 'created_at', 'confirmed_at', 
        'assigned_at', 'picked_up_at', 'delivered_at', 'cancelled_at', 
        'customer_phone_display_method', 'delivery_latitude', 'delivery_longitude',
        'order_summary_display'  # Financial summary method
    )
    
    inlines = [OrderItemInline]
    
    # Fixed fieldsets - removed customer_phone_display and replaced with actual field
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'order_number', 'status', 'created_at')
        }),
        ('Customer Details', {
            'fields': ('customer', 'customer_phone_display_method')  # Changed from customer_phone_display
        }),
        ('Delivery Information', {
            'fields': (
                'delivery_address', 'delivery_location_name',
                'delivery_latitude', 'delivery_longitude', 'delivery_street_address',
                'scheduled_delivery_date', 'scheduled_delivery_time', 'driver'
            )
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'is_paid', 'payment_reference')
        }),
        ('Order Summary', {
            'fields': ('order_summary_display',),
            'description': 'Complete breakdown of all charges'
        }),
        ('Financial Breakdown', {
            'fields': (
                'items_total', 'delivery_fee', 'service_fee', 
                'discount_amount', 'total_amount'
            )
        }),
        ('Status History', {
            'fields': (
                'confirmed_at', 'assigned_at', 'picked_up_at', 
                'delivered_at', 'cancelled_at'
            ),
            'classes': ('collapse',)
        }),
        ('Cancellation', {
            'fields': ('cancellation_reason',),
            'classes': ('collapse',)
        }),
    )
    
    def order_number_colored(self, obj):
        """Display order number with color coding"""
        colors = {
            'pending': '#FFA500',      # Orange
            'confirmed': '#4169E1',    # Blue
            'preparing': '#9370DB',    # Purple
            'ready': '#3CB371',        # Green
            'assigned': '#20B2AA',     # Teal
            'picked_up': '#1E90FF',    # Dodger Blue
            'on_the_way': '#FF6347',   # Tomato
            'delivered': '#228B22',    # Forest Green
            'cancelled': '#DC143C',    # Crimson
            'failed': '#8B0000',       # Dark Red
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.order_number
        )
    order_number_colored.short_description = 'Order Number'
    
    def status_colored(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#FFA500',
            'confirmed': '#4169E1',
            'preparing': '#9370DB',
            'ready': '#3CB371',
            'assigned': '#20B2AA',
            'picked_up': '#1E90FF',
            'on_the_way': '#FF6347',
            'delivered': '#228B22',
            'cancelled': '#DC143C',
            'failed': '#8B0000',
        }
        color = colors.get(obj.status, '#000000')
        status_display = obj.get_status_display()
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            status_display
        )
    status_colored.short_description = 'Status'
    
    def customer_phone(self, obj):
        """Display customer phone number in list view"""
        if obj.customer and hasattr(obj.customer, 'phone_number'):
            return obj.customer.phone_number
        return "N/A"
    customer_phone.short_description = 'Customer'
    
    def customer_phone_display_method(self, obj):
        """Display customer full details in change view"""
        if obj.customer and hasattr(obj.customer, 'phone_number'):
            phone = obj.customer.phone_number
            # Check if customer has a name attribute
            if hasattr(obj.customer, 'customer') and hasattr(obj.customer.customer, 'names'):
                name = obj.customer.customer.names
                return f"{name} - {phone}"
            return phone
        return "No customer information"
    customer_phone_display_method.short_description = 'Customer Phone'
    
    def created_at_short(self, obj):
        """Display creation date in short format"""
        return obj.created_at.strftime('%d %b %Y %H:%M')
    created_at_short.short_description = 'Created'
    
    def items_total_display(self, obj):
        """Display items total with currency formatting"""
        return format_html(
            '<span style="color: #0066cc; font-weight: bold;">TZS {}</span>',
            f'{obj.items_total:,.2f}'
        )
    items_total_display.short_description = 'Items Total'
    
    def delivery_fee_display(self, obj):
        """Display delivery fee with visual emphasis"""
        if obj.delivery_fee and obj.delivery_fee > 0:
            return format_html(
                '<span style="background-color: #fff3cd; color: #856404; padding: 3px 8px; border-radius: 3px; font-weight: bold;">TZS {}</span>',
                f'{obj.delivery_fee:,.2f}'
            )
        return format_html(
            '<span style="color: #6c757d;">TZS 0.00</span>'
        )
    delivery_fee_display.short_description = 'Delivery Fee'
    
    def total_amount_colored(self, obj):
        """Display total amount with color based on payment status"""
        bg_color = '#d4edda' if obj.is_paid else '#f8d7da'  # Green if paid, Red if not
        text_color = '#155724' if obj.is_paid else '#721c24'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 10px; border-radius: 3px; font-weight: bold; font-size: 1.1em;">TZS {}</span>',
            bg_color,
            text_color,
            f'{obj.total_amount:,.2f}'
        )
    total_amount_colored.short_description = 'Total Amount'
    
    def order_summary_display(self, obj):
        """Display complete financial breakdown in a formatted box"""
        service_fee = obj.service_fee or 0
        discount = obj.discount_amount or 0
        
        html = f'''
        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; font-family: monospace;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; text-align: left; font-weight: bold;">Items Total</td>
                    <td style="padding: 8px; text-align: right; color: #0066cc;">TZS {obj.items_total:,.2f}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6; background-color: #fff3cd;">
                    <td style="padding: 8px; text-align: left; font-weight: bold; color: #856404;">Delivery Fee</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold; color: #856404;">TZS {obj.delivery_fee:,.2f}</td>
                </tr>
        '''
        
        if service_fee > 0:
            html += f'''
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; text-align: left;">Service Fee</td>
                    <td style="padding: 8px; text-align: right; color: #666;">TZS {service_fee:,.2f}</td>
                </tr>
            '''
        
        if discount > 0:
            html += f'''
                <tr style="border-bottom: 1px solid #dee2e6; background-color: #d4edda;">
                    <td style="padding: 8px; text-align: left; color: #155724;">Discount</td>
                    <td style="padding: 8px; text-align: right; color: #155724; font-weight: bold;">-TZS {discount:,.2f}</td>
                </tr>
            '''
        
        payment_status = '✓ PAID' if obj.is_paid else '✗ UNPAID'
        payment_color = '#28a745' if obj.is_paid else '#dc3545'
        
        html += f'''
                <tr style="background-color: #e7f3ff; border-top: 2px solid #0066cc;">
                    <td style="padding: 12px; text-align: left; font-weight: bold; font-size: 1.1em;">TOTAL</td>
                    <td style="padding: 12px; text-align: right; font-weight: bold; font-size: 1.1em; color: #0066cc;">TZS {obj.total_amount:,.2f}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding: 8px; text-align: center;">
                        <span style="background-color: {payment_color}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{payment_status}</span>
                    </td>
                </tr>
            </table>
        </div>
        '''
        
        return format_html(html)
    order_summary_display.short_description = 'Order Summary'
    
    def has_add_permission(self, request):
        """Prevent adding orders from admin (they are created via API)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of orders in pending status only"""
        if obj and obj.status == 'pending':
            return True
        return request.user.is_superuser
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Order item details"""
    list_display = ('order_number', 'product_name', 'quantity', 'unit_price_display', 'total_price_display')
    list_filter = ('order__created_at', 'order__status')
    search_fields = ('order__order_number', 'product_variant__product_template__name')
    readonly_fields = ('order', 'product_variant', 'measurement_unit', 'total_price')
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'
    
    def product_name(self, obj):
        return obj.product_variant.product_template.name if obj.product_variant else 'N/A'
    product_name.short_description = 'Product'
    
    def unit_price_display(self, obj):
        """Display unit price with currency formatting"""
        # Format the number first, then pass to format_html
        formatted_price = "{:,.2f}".format(obj.unit_price)
        return format_html(
            'TZS <span style="font-weight: bold;">{}</span>',
            formatted_price
        )
    unit_price_display.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        """Display total price with color and currency formatting"""
        # Format the number first
        formatted_total = "{:,.2f}".format(obj.total_price)
        return format_html(
            '<span style="background-color: #e7f3ff; color: #0066cc; padding: 3px 8px; border-radius: 3px; font-weight: bold;">TZS {}</span>',
            formatted_total
        )
    total_price_display.short_description = 'Total Price'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

        
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Cart management in admin"""
    list_display = ('id', 'customer_phone', 'market_name', 'items_count', 'created_at_short')
    list_filter = ('created_at', 'market')
    search_fields = ('customer__phone_number', 'market__name')
    readonly_fields = ('id', 'customer', 'market', 'created_at', 'updated_at')
    
    def customer_phone(self, obj):
        if obj.customer and hasattr(obj.customer, 'phone_number'):
            return obj.customer.phone_number
        return "N/A"
    customer_phone.short_description = 'Customer'
    
    def market_name(self, obj):
        return obj.market.name if obj.market else "N/A"
    market_name.short_description = 'Market'
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d %b %Y %H:%M')
    created_at_short.short_description = 'Created'
    
    def has_add_permission(self, request):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Cart item details"""
    list_display = ('cart_id', 'product_name', 'quantity', 'unit_price_display', 'total_price_display')
    list_filter = ('cart__created_at',)
    search_fields = ('cart__id', 'product_variant__product_template__name')
    readonly_fields = ('cart', 'product_variant', 'total_price')
    
    def cart_id(self, obj):
        return str(obj.cart.id)[:8] + '...'
    cart_id.short_description = 'Cart'
    
    def product_name(self, obj):
        return obj.product_variant.product_template.name if obj.product_variant else 'N/A'
    product_name.short_description = 'Product'
    
    def unit_price_display(self, obj):
        formatted_price = f"{obj.unit_price:,.2f}"
        return format_html(
            'TZS <span style="font-weight: bold;">{}</span>',
            formatted_price
        )
    unit_price_display.short_description = 'Unit Price'

    def total_price_display(self, obj):
        formatted_total = f"{obj.total_price:,.2f}"
        return format_html(
            '<span style="background-color: #f0f0f0; color: #333; padding: 3px 8px; border-radius: 3px; font-weight: bold;">TZS {}</span>',
            formatted_total
        )
    total_price_display.short_description = 'Total Price'

    
    def has_add_permission(self, request):
        return False


@admin.register(OrderStatusUpdate)
class OrderStatusUpdateAdmin(admin.ModelAdmin):
    """Order status change history"""
    list_display = ('order_number', 'old_status_colored', 'new_status_colored', 'created_at_short')
    list_filter = ('old_status', 'new_status', 'created_at')
    search_fields = ('order__order_number',)
    readonly_fields = ('order', 'old_status', 'new_status', 'updated_by', 'created_at')
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'
    
    def old_status_colored(self, obj):
        return format_html(
            '<span style="background-color: #ffcccc; padding: 3px 6px; border-radius: 3px;">{}</span>',
            obj.get_old_status_display()
        )
    old_status_colored.short_description = 'From'
    
    def new_status_colored(self, obj):
        return format_html(
            '<span style="background-color: #ccffcc; padding: 3px 6px; border-radius: 3px;">{}</span>',
            obj.get_new_status_display()
        )
    new_status_colored.short_description = 'To'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d %b %Y %H:%M')
    created_at_short.short_description = 'Changed At'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False