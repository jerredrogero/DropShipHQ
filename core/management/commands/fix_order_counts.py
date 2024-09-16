from django.core.management.base import BaseCommand
from core.models import Subscription, Order

class Command(BaseCommand):
    help = 'Fix order counts based on actual orders'

    def handle(self, *args, **options):
        subscriptions = Subscription.objects.all()
        for subscription in subscriptions:
            count = Order.objects.filter(user=subscription.user).count()
            subscription.order_count = count
            subscription.save()
            self.stdout.write(self.style.SUCCESS(f'Updated order_count for {subscription.user.username} to {count}'))
