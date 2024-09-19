from celery import shared_task
from django.utils import timezone
from core.models import Subscription
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

@shared_task
def refresh_order_limits():
    now = timezone.now()
    subscriptions = Subscription.objects.filter(next_refresh_date__lte=now, status='active')
    
    for subscription in subscriptions:
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            if stripe_sub.status == 'active':
                subscription.refresh_order_limit()
            else:
                subscription.status = 'inactive'
                subscription.save()
        except stripe.error.StripeError as e:
            print(f"Stripe error for subscription {subscription.id}: {str(e)}")
        except Exception as e:
            print(f"Error processing subscription {subscription.id}: {str(e)}")
