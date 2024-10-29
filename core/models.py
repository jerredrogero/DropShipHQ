from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models.signals import post_save
from dateutil.relativedelta import relativedelta



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
        # Create a default subscription for the user
        Subscription.objects.create(user=instance, plan='FREE')
    else:
        # Use get_or_create to handle cases where UserProfile or Subscription might not exist yet
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        subscription, _ = Subscription.objects.get_or_create(user=instance)
        profile.save()
        subscription.save() 

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
    paid = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"

    def calculate_total_profit(self):
        if not self.cost or not self.reimbursed or not self.cash_back:
            return 0
        return (self.cash_back / 100 * self.cost) + (self.reimbursed - self.cost)

    @classmethod
    def order_number_exists(cls, user, order_number):
        return cls.objects.filter(user=user, order_number=order_number).exists()

    def save(self, *args, **kwargs):
        # Ensure values are not None
        cash_back = self.cash_back if self.cash_back is not None else 0
        cost = self.cost if self.cost is not None else 0
        reimbursed = self.reimbursed if self.reimbursed is not None else 0

        # Calculate net gain and total profit
        self.net_gain = reimbursed - cost + (cash_back / 100 * cost)
        super().save(*args, **kwargs)

@receiver(post_save, sender=Order)
def update_subscription_order_count_on_save(sender, instance, created, **kwargs):
    if created:
        subscription = instance.user.subscription
        subscription.increment_order_count()

@receiver(post_delete, sender=Order)
def update_subscription_order_count_on_delete(sender, instance, **kwargs):
    try:
        subscription = instance.user.subscription
        subscription.order_count = max(0, subscription.order_count - 1)
        subscription.save()
    except Subscription.DoesNotExist:
        # If the subscription doesn't exist, we don't need to update anything
        pass

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
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')
    order_count = models.IntegerField(default=0)
    next_refresh_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')
    stripe_subscription_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def increment_order_count(self):
        self.order_count += 1
        self.save()

    def recalculate_order_count(self):
        self.order_count = self.user.order_set.count()
        self.save()

    def __str__(self):
        return f"{self.user.username}'s {self.get_plan_display()} Subscription"

    def save(self, *args, **kwargs):
        if not self.next_refresh_date:
            self.next_refresh_date = timezone.now() + relativedelta(months=1)
        super().save(*args, **kwargs)

    def refresh_order_limit(self):
        now = timezone.now()
        if not self.next_refresh_date:
            self.next_refresh_date = now + relativedelta(months=1)
            self.save()
        elif now >= self.next_refresh_date:
            self.order_count = 0
            self.next_refresh_date = now + relativedelta(months=1)
            self.save()

    def orders_left(self):
        limit = self.get_order_limit()
        if limit == 'Unlimited':
            return 'Unlimited'
        return max(0, limit - self.order_count)

    def days_until_refresh(self):
        if not self.next_refresh_date:
            return None
        days = (self.next_refresh_date - timezone.now()).days
        return max(0, days)

    def is_paid(self):
        return self.plan in ['FREE', 'STARTER', 'PRO', 'PREMIUM', 'ENTERPRISE']

    def get_order_limit(self):
        PLAN_LIMITS = {
            'FREE': 10,
            'STARTER': 50,
            'PRO': 150,
            'PREMIUM': 300,
            'ENTERPRISE': 'Unlimited',
        }
        return PLAN_LIMITS.get(self.plan, 0)

    def can_create_order(self):
        limit = self.get_order_limit()
        if limit == 'Unlimited':
            return True
        return self.order_count < limit