# admin_dashboard/templatetags/order_filters.py
from django import template
from django.db.models import QuerySet
from decimal import Decimal

register = template.Library()

@register.filter
def map_attribute(queryset, attribute):
    """Map queryset to list of attribute values"""
    if isinstance(queryset, QuerySet):
        return [getattr(obj, attribute, None) for obj in queryset]
    elif isinstance(queryset, (list, tuple)):
        return [getattr(obj, attribute, None) for obj in queryset]
    return []

@register.filter
def sum_values(value_list):
    """Sum a list of values"""
    if not value_list:
        return 0
    
    total = 0
    for value in value_list:
        if value is not None:
            try:
                if isinstance(value, (Decimal, float, int)):
                    total += float(value)
            except (TypeError, ValueError):
                continue
    return total

@register.filter
def where(queryset, attribute):
    """Filter objects where attribute exists (placeholder)"""
    # This is a simplified placeholder - actual implementation depends on use case
    return queryset

@register.filter
def equals(value, comparison):
    """Check if value equals comparison"""
    return str(value) == str(comparison)

@register.filter
def divide(value, divisor):
    """Divide value by divisor"""
    try:
        if float(divisor) == 0:
            return 0
        return float(value) / float(divisor)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, multiplier):
    """Multiply value by multiplier"""
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0

@register.filter
def where_status_equals(queryset, status_value):
    """Filter orders by status equals"""
    if not queryset:
        return []
    return [order for order in queryset if order.status == status_value]

@register.filter
def get_length(value):
    """Get length of queryset or list"""
    if hasattr(value, 'count'):
        return value.count()
    elif hasattr(value, '__len__'):
        return len(value)
    return 0

@register.filter
def timesince_hours(value):
    """Get hours since datetime"""
    from django.utils import timezone
    if not value:
        return 0
    delta = timezone.now() - value
    return delta.total_seconds() / 3600  # Convert to hours

# More practical filters for order statistics
@register.filter
def total_revenue(queryset):
    """Calculate total revenue from orders"""
    total = Decimal('0.00')
    if not queryset:
        return total
    
    for order in queryset:
        if order.total_amount:
            try:
                total += Decimal(str(order.total_amount))
            except (ValueError, TypeError):
                continue
    return total

@register.filter
def avg_order_value(queryset):
    """Calculate average order value"""
    if not queryset:
        return Decimal('0.00')
    
    total = Decimal('0.00')
    count = 0
    
    for order in queryset:
        if order.total_amount:
            try:
                total += Decimal(str(order.total_amount))
                count += 1
            except (ValueError, TypeError):
                continue
    
    if count == 0:
        return Decimal('0.00')
    
    return total / Decimal(str(count))

@register.filter
def delivered_count(queryset):
    """Count delivered orders"""
    if not queryset:
        return 0
    return sum(1 for order in queryset if order.status == 'delivered')

@register.filter
def active_count(queryset):
    """Count active orders (not delivered, cancelled, or failed)"""
    if not queryset:
        return 0
    excluded_statuses = ['delivered', 'cancelled', 'failed']
    return sum(1 for order in queryset if order.status not in excluded_statuses)

@register.filter
def completion_rate(queryset):
    """Calculate completion rate (delivered / total)"""
    if not queryset:
        return 0
    
    total = len(queryset)
    delivered = sum(1 for order in queryset if order.status == 'delivered')
    
    if total == 0:
        return 0
    
    return (delivered / total) * 100





# Add to admin_dashboard/templatetags/order_filters.py

@register.filter
def avg_age(queryset):
    """Calculate average age of orders in hours"""
    from django.utils import timezone
    
    if not queryset:
        return 0
    
    total_hours = 0
    count = 0
    
    for order in queryset:
        if order.created_at:
            delta = timezone.now() - order.created_at
            total_hours += delta.total_seconds() / 3600
            count += 1
    
    if count == 0:
        return 0
    
    return total_hours / count

@register.filter
def percentage_of(value, total):
    """Calculate percentage of value from total"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
    


# admin_dashboard/templatetags/order_filters.py
# Add these filters if not already present:

@register.filter
def total_revenue(queryset):
    """Calculate total revenue from orders"""
    total = Decimal('0.00')
    if not queryset:
        return total
    
    for order in queryset:
        if order.total_amount:
            try:
                total += Decimal(str(order.total_amount))
            except (ValueError, TypeError):
                continue
    return total

@register.filter
def avg_age(queryset):
    """Calculate average age of orders in hours"""
    from django.utils import timezone
    
    if not queryset:
        return 0
    
    total_hours = 0
    count = 0
    
    for order in queryset:
        if order.created_at:
            delta = timezone.now() - order.created_at
            total_hours += delta.total_seconds() / 3600
            count += 1
    
    if count == 0:
        return 0
    
    return total_hours / count

@register.filter
def divide(value, divisor):
    """Divide value by divisor"""
    try:
        if float(divisor) == 0:
            return 0
        return float(value) / float(divisor)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, multiplier):
    """Multiply value by multiplier"""
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0

@register.filter
def timesince_hours(value):
    """Get hours since datetime"""
    from django.utils import timezone
    if not value:
        return 0
    delta = timezone.now() - value
    return delta.total_seconds() / 3600  # Convert to hours



# admin_dashboard/templatetags/order_filters.py
from django import template

register = template.Library()

@register.filter
def avg_wait_time(orders):
    """Calculate average wait time for a list of orders in minutes"""
    if not orders:
        return 0
    
    total_wait = 0
    count = 0
    
    for order in orders:
        # Assuming order has a method get_wait_time_minutes()
        wait_time = getattr(order, 'get_wait_time_minutes', lambda: None)()
        if wait_time is not None:
            total_wait += wait_time
            count += 1
    
    return total_wait / count if count > 0 else 0