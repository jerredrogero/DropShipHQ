from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Order, BuyingGroup, Account, Merchant, Card, Subscription, UserProfile

class SubscriptionInline(admin.StackedInline):
    model = Subscription
    can_delete = False
    verbose_name_plural = 'Subscription'
    max_num = 1
    min_num = 1

class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (SubscriptionInline, ProfileInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        Subscription.objects.get_or_create(user=obj)
        UserProfile.objects.get_or_create(user=obj)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Subscription):
                try:
                    existing_subscription = Subscription.objects.get(user=form.instance)
                    for field in instance._meta.fields:
                        if field.name not in ['id', 'user']:
                            setattr(existing_subscription, field.name, getattr(instance, field.name))
                    existing_subscription.save()
                except Subscription.DoesNotExist:
                    instance.user = form.instance
                    instance.save()
            elif isinstance(instance, UserProfile):
                instance.user = form.instance
                instance.save()
            else:
                instance.save()
        formset.save_m2m()

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Order)
admin.site.register(BuyingGroup)
admin.site.register(Account)
admin.site.register(Merchant)
admin.site.register(Card)
admin.site.register(Subscription)
admin.site.register(UserProfile)
