from django import template

register = template.Library()

@register.filter
def dict_lookup(dictionary, key):
    """Get value from dict by key in templates"""
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None