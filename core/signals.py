from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Subscription

@receiver(post_save, sender=User)
def create_or_update_user_subscription(sender, instance, created, **kwargs):
    subscription, created = Subscription.objects.get_or_create(user=instance)
    if not created:
        subscription.save()