from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Subscription
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Refresh order limits for subscriptions'

    def handle(self, *args, **options):
        now = timezone.now()
        subscriptions = Subscription.objects.filter(next_refresh_date__lte=now)
        for subscription in subscriptions:
            subscription.refresh_order_limit()
            self.stdout.write(self.style.SUCCESS(f'Refreshed order limit for {subscription.user.username}'))
