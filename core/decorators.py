from django.shortcuts import redirect
from django.contrib import messages
from .models import Subscription
from functools import wraps

def check_subscription(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            subscription, created = Subscription.objects.get_or_create(user=request.user)
            if not subscription.can_create_order():
                messages.warning(request, "You've reached the limit of your current plan's orders. Please upgrade your plan.")
                return redirect('pricing')
        return view_func(request, *args, **kwargs)
    return wrapper
