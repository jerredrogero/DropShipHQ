from django.shortcuts import redirect
from django.contrib import messages

class SubscriptionRequiredMixin:
    allowed_plans = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')  # Replace with your actual login URL name
        
        try:
            user_subscription = request.user.subscription
            if user_subscription.plan not in self.allowed_plans:
                messages.error(request, "Your current plan does not grant access to this page. Please upgrade your subscription.")
                return redirect('pricing')  # Replace with your actual pricing page URL name
        except AttributeError:
            messages.error(request, "Subscription information is missing. Please contact support.")
            return redirect('pricing')
        
        return super().dispatch(request, *args, **kwargs)
