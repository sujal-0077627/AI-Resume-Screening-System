from django import template

register = template.Library()

@register.filter
def split(value, arg):
    if value:
        return value.split(arg)
    return []
