from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    if hasattr(value, 'as_widget'):
        # This is a form field
        return value.as_widget(attrs={'class': arg})
    else:
        # This is likely a string, just return it unchanged
        return value

@register.filter(is_safe=True)
def safe_link(value):
    return f"<a href='https://www.amazon.com/gp/your-account/order-details?orderID={value}' target='_blank'>{value}</a>"