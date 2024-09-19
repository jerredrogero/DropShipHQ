from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import User, Subscription
from dateutil.relativedelta import relativedelta
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class Command(BaseCommand):
    help = 'Test subscription refresh functionality'

    def handle(self, *args, **options):
        # Create a test user and subscription
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create a Stripe test subscription
        stripe_subscription = stripe.Subscription.create(
            customer=user.stripe_customer_id,  # Assume user has a Stripe customer ID
            items=[{'price': 'price_XXXXXXXXXXXXXX'}],  # Use a test price ID
        )

        subscription = Subscription.objects.create(
            user=user,
            plan='PRO',
            status='active',
            stripe_subscription_id=stripe_subscription.id,
            subscription_start_date=timezone.now() - relativedelta(days=30),
            next_refresh_date=timezone.now() - relativedelta(days=1),
            order_count=10
        )

        self.stdout.write(self.style.SUCCESS(f'Created test subscription for {user.username}'))

        # Run the Celery task
        from core.tasks import refresh_order_limits
        refresh_order_limits.delay()

        self.stdout.write(self.style.SUCCESS('Triggered refresh_order_limits task'))

        # Wait for a moment to allow the task to complete
        import time
        time.sleep(5)

        # Refresh the subscription from the database
        subscription.refresh_from_db()

        if subscription.order_count == 0 and subscription.next_refresh_date > timezone.now():
            self.stdout.write(self.style.SUCCESS('Subscription successfully refreshed'))
        else:
            self.stdout.write(self.style.ERROR('Subscription refresh failed'))

        # Clean up
        subscription.delete()
        user.delete()
        stripe.Subscription.delete(stripe_subscription.id)

        self.stdout.write(self.style.SUCCESS('Test completed'))
