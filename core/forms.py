from django import forms
from .models import Order, APICredentials, BuyingGroup

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['date', 'buying_group', 'account', 'order_number', 'tracking_number', 'product', 'merchant', 'card', 'cost', 'reimbursed', 'cash_back']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['buying_group'].queryset = BuyingGroup.objects.filter(user=user)
        self.fields['buying_group'].required = False
        self.fields['tracking_number'].required = False

class APICredentialsForm(forms.ModelForm):
    class Meta:
        model = APICredentials
        fields = ['bfmr_api_key', 'bfmr_api_secret']
        widgets = {
            'bfmr_api_key': forms.PasswordInput(render_value=True),
            'bfmr_api_secret': forms.PasswordInput(render_value=True),
        }

class DealCalculatorForm(forms.Form):
    purchase_price = forms.DecimalField(label='Purchase Price', min_value=0, decimal_places=2)
    reimbursement_price = forms.DecimalField(label='Reimbursement Price', min_value=0, decimal_places=2)
    cashback_percentage = forms.DecimalField(label='Cashback Percentage', min_value=0, max_value=100, decimal_places=2)

class BuyingGroupForm(forms.ModelForm):
    class Meta:
        model = BuyingGroup
        fields = ['name']
