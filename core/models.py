from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models.signals import post_save



# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Use get_or_create to handle cases where UserProfile might not exist yet
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        profile.save() 

class BuyingGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Merchant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Card(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    buying_group = models.ForeignKey('BuyingGroup', on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey('Account', on_delete=models.SET_NULL, null=True, blank=True)
    order_number = models.CharField(max_length=100, null=True, blank=True)
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    product = models.CharField(max_length=200, null=True, blank=True)
    merchant = models.ForeignKey('Merchant', on_delete=models.SET_NULL, null=True, blank=True)
    card = models.ForeignKey('Card', on_delete=models.SET_NULL, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reimbursed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cash_back = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"

    @property
    def commission(self):
        return self.reimbursed - self.cost

    @property
    def total_profit(self):
        return (self.cash_back / 100 * self.cost) + self.commission

    @classmethod
    def order_number_exists(cls, user, order_number):
        return cls.objects.filter(user=user, order_number=order_number).exists()

@receiver(post_save, sender=Order)
def update_subscription_order_count_on_save(sender, instance, created, **kwargs):
    if created:
        subscription = instance.user.subscription
        subscription.increment_order_count()

@receiver(post_delete, sender=Order)
def update_subscription_order_count_on_delete(sender, instance, **kwargs):
    subscription = instance.user.subscription
    subscription.order_count = max(0, subscription.order_count - 1)
    subscription.save()

class APICredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)

    def __str__(self):
        return f"API Credentials for {self.user.username}"

class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}: {self.key}"

class Subscription(models.Model):
    PLAN_CHOICES = [
        ('FREE', 'Free'),
        ('STARTER', 'Starter'),
        ('PRO', 'Pro'),
        ('PREMIUM', 'Premium'),
        ('ENTERPRISE', 'Enterprise'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='FREE')
    order_count = models.IntegerField(default=0)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')

    def get_plan_display(self):
        return dict(self.PLAN_CHOICES)[self.plan]

    def get_order_limit(self):
        limits = {
            'FREE': 5,
            'STARTER': 30,
            'PRO': 100,
            'PREMIUM': 500,
            'ENTERPRISE': 'Unlimited'
        }
        return limits[self.plan]

    def can_create_order(self):
        if self.plan == 'FREE':
            return self.order_count < 5
        elif self.plan == 'STARTER':
            return self.order_count < 30
        elif self.plan == 'PRO':
            return self.order_count < 100
        else:  # PREMIUM and ENTERPRISE
            return True

    def increment_order_count(self):
        self.order_count += 1
        self.save()

    def recalculate_order_count(self):
        self.order_count = self.user.order_set.count()
        self.save()

    def __str__(self):
        return f"{self.user.username}'s {self.get_plan_display()} Subscription"