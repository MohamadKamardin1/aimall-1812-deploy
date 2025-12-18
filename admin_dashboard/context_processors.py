# admin_dashboard/context_processors.py
from order.models import Order

def sidebar_counts(request):
    """Add pending order counts to all templates"""
    context = {}
    
    # Only calculate for authenticated users
    if request.user.is_authenticated:
        try:
            # Count pending orders (statuses that need attention)
            pending_orders = Order.objects.filter(
                status__in=['pending', 'confirmed', 'preparing']
            ).count()
            context['pending_orders'] = pending_orders
        except:
            context['pending_orders'] = 0
    
    return context