from django import template

register = template.Library()

@register.filter
def map_attribute(objects, attr_name):
    return [getattr(obj, attr_name) for obj in objects]

@register.filter
def sum_list(values):
    return sum(values)
