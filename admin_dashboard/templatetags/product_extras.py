# admin_dashboard/templatetags/product_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key))


@register.filter
def get_unit_price(price_map, variant_unit_pair):
    """
    Get unit price from map using "variant_id,unit_id" string
    """
    try:
        variant_id, unit_id = variant_unit_pair.split(',')
        return price_map.get((variant_id, unit_id), 0)
    except (ValueError, AttributeError):
        return 0