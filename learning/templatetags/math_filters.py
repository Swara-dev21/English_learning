from django import template

register = template.Library()

@register.filter
def floor(value):
    """Return the floor of a number as integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0