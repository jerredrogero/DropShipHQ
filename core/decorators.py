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

def subscription_required(allowed_plans):
    """
    Decorator to check if the user's subscription plan is within the allowed_plans.
    If not, redirects to the pricing page with an informational message.
    
    :param allowed_plans: List of plan names that are allowed to access the view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect('login')  # Replace 'login' with your actual login URL name
            
            try:
                user_subscription = request.user.subscription
                if user_subscription.plan not in allowed_plans:
                    messages.error(request, "Your current plan does not grant access to this page. Please upgrade your subscription.")
                    return redirect('pricing')  # Replace 'pricing' with your actual pricing page URL name
            except AttributeError:
                messages.error(request, "Subscription information is missing. Please contact support.")
                return redirect('pricing')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
