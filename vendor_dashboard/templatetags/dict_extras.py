from django import template

register = template.Library()

@register.filter
def dict_lookup(d, key):
    """Return d[key] if it exists, else None."""
    return d.get(key)
