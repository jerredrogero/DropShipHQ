from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class BuyingGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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

class APICredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=100, null=True, blank=True)
    api_secret = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"API Credentials for {self.user.username}"

class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}: {self.key}"
