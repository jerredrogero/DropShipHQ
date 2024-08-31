from django import forms
from .models import Order, APICredentials

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['date', 'buying_groups', 'account', 'order_number', 'tracking_number', 'product', 'merchant', 'card', 'cost', 'reimbursed', 'cash_back']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'cash_back': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        
        # Make certain fields optional
        optional_fields = ['buying_groups', 'account', 'tracking_number', 'card']
        for field in optional_fields:
            self.fields[field].required = False

    # Remove the clean_order_number method entirely

class APICredentialsForm(forms.ModelForm):
    class Meta:
        model = APICredentials
        fields = ['bfmr_api_key', 'bfmr_api_secret']
        widgets = {
            'bfmr_api_key': forms.PasswordInput(render_value=True),
            'bfmr_api_secret': forms.PasswordInput(render_value=True),
        }
