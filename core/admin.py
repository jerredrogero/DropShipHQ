from django.contrib import admin
from .models import Order, BuyingGroup, Account, Merchant, Card

# Register your models here.

admin.site.register(Order)
admin.site.register(BuyingGroup)
admin.site.register(Account)
admin.site.register(Merchant)
admin.site.register(Card)
