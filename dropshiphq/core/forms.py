from django import forms
from .models import Order, APICredentials

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['date', 'buying_groups', 'account', 'order_number', 'tracking_number', 'product', 'merchant', 'card', 'cost', 'reimbursed', 'cash_back']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance

class APICredentialsForm(forms.ModelForm):
    class Meta:
        model = APICredentials
        fields = ['bfmr_api_key', 'bfmr_api_secret']
        widgets = {
            'bfmr_api_key': forms.PasswordInput(render_value=True),
            'bfmr_api_secret': forms.PasswordInput(render_value=True),
        }
