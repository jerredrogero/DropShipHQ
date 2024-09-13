from django import forms
from .models import Order, APICredentials, BuyingGroup, Account, Merchant, Card, APIKey
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['date', 'buying_group', 'account', 'order_number', 'tracking_number', 'product', 'merchant', 'card', 'cost', 'reimbursed', 'cash_back']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        
        for field in self.fields:
            if field != 'date':  # We've already set the class for date
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            self.fields[field].required = False

        if user:
            self.fields['buying_group'].queryset = BuyingGroup.objects.filter(user=user)
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['merchant'].queryset = Merchant.objects.filter(user=user)
            self.fields['card'].queryset = Card.objects.filter(user=user)

class APICredentialsForm(forms.ModelForm):
    class Meta:
        model = APICredentials
        fields = ['api_key', 'api_secret']
        widgets = {
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

class DealCalculatorForm(forms.Form):
    purchase_price = forms.DecimalField(label='Purchase Price', min_value=0, decimal_places=2)
    reimbursement_price = forms.DecimalField(label='Reimbursement Price', min_value=0, decimal_places=2)
    cashback_percentage = forms.DecimalField(label='Cashback Percentage', min_value=0, max_value=100, decimal_places=2)

class BuyingGroupForm(forms.ModelForm):
    class Meta:
        model = BuyingGroup
        fields = ['name']

class RegisterForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ["username", "password1", "password2"]

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name']

class MerchantForm(forms.ModelForm):
    class Meta:
        model = Merchant
        fields = ['name']

class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['name']

class APIKeyForm(forms.ModelForm):
    class Meta:
        model = APIKey
        fields = ['name', 'key']
