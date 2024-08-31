from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    buying_groups = models.CharField(max_length=100, blank=True)
    account = models.CharField(max_length=100, blank=True)
    order_number = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    product = models.CharField(max_length=200)
    merchant = models.CharField(max_length=100, blank=True)
    card = models.CharField(max_length=50, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    reimbursed = models.DecimalField(max_digits=10, decimal_places=2)
    cash_back = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Cash back percentage")

    class Meta:
        unique_together = ['user', 'order_number']

    def __str__(self):
        return f"{self.user.username} - {self.order_number}"

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
