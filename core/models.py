from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class BuyingGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    buying_group = models.ForeignKey(BuyingGroup, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.CharField(max_length=100)
    order_number = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    product = models.CharField(max_length=255)
    merchant = models.CharField(max_length=100)
    card = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    reimbursed = models.DecimalField(max_digits=10, decimal_places=2)
    cash_back = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.date} - {self.product}"

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
    bfmr_api_key = models.CharField(max_length=255, blank=True)
    bfmr_api_secret = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username}'s API Credentials"
