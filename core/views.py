from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from .models import Order, APICredentials, BuyingGroup, Account, Merchant, Card
from .forms import OrderForm, APICredentialsForm, DealCalculatorForm, BuyingGroupForm, AccountForm, MerchantForm, CardForm
from datetime import datetime
from django.utils import timezone
import requests
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
import calendar
from decimal import Decimal
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from .forms import UserCreationForm
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import AccountForm, MerchantForm, CardForm, BuyingGroupForm, APICredentialsForm
from .models import Account, Merchant, Card, BuyingGroup, APICredentials

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    orders = Order.objects.filter(user=request.user).order_by('-date')
    buying_groups = BuyingGroup.objects.filter(user=request.user)
    accounts = Account.objects.filter(user=request.user)
    merchants = Merchant.objects.filter(user=request.user)
    cards = Card.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            messages.success(request, 'Order added successfully.')
            return redirect('dashboard')
    else:
        form = OrderForm(user=request.user)

    context = {
        'orders': orders,
        'form': form,
        'buying_groups': buying_groups,
        'accounts': accounts,
        'merchants': merchants,
        'cards': cards,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order, user=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'errors': 'Invalid request method'})

@login_required
@csrf_exempt
@require_POST
def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order.delete()
        return JsonResponse({'success': True})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('home')

class CustomSignupView(FormView):
    usable_password = None
    template_name = 'core/signup.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

@login_required
def settings(request):
    accounts = Account.objects.filter(user=request.user)
    merchants = Merchant.objects.filter(user=request.user)
    cards = Card.objects.filter(user=request.user)
    buying_groups = BuyingGroup.objects.filter(user=request.user)
    
    try:
        api_credentials = APICredentials.objects.get(user=request.user)
    except APICredentials.DoesNotExist:
        api_credentials = None

    if request.method == 'POST':
        if 'add_account' in request.POST:
            form = AccountForm(request.POST)
        elif 'add_merchant' in request.POST:
            form = MerchantForm(request.POST)
        elif 'add_card' in request.POST:
            form = CardForm(request.POST)
        elif 'add_buying_group' in request.POST:
            form = BuyingGroupForm(request.POST)
        elif 'update_api_credentials' in request.POST:
            form = APICredentialsForm(request.POST, instance=api_credentials)
        
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()
            messages.success(request, f"{form.instance._meta.verbose_name} added/updated successfully.")
            return redirect('settings')
    else:
        account_form = AccountForm()
        merchant_form = MerchantForm()
        card_form = CardForm()
        buying_group_form = BuyingGroupForm()
        api_credentials_form = APICredentialsForm(instance=api_credentials)

    context = {
        'accounts': accounts,
        'merchants': merchants,
        'cards': cards,
        'buying_groups': buying_groups,
        'account_form': account_form,
        'merchant_form': merchant_form,
        'card_form': card_form,
        'buying_group_form': buying_group_form,
        'api_credentials_form': api_credentials_form,
    }
    return render(request, 'core/settings.html', context)

@login_required
def delete_buying_group(request, pk):
    buying_group = get_object_or_404(BuyingGroup, pk=pk, user=request.user)
    if request.method == 'POST':
        buying_group.delete()
        messages.success(request, 'Buying group deleted successfully.')
    return redirect('settings')

@login_required
def bfmr_deals(request):
    try:
        api_credentials = APICredentials.objects.get(user=request.user)
        if not api_credentials.api_key or not api_credentials.api_secret:
            raise APICredentials.DoesNotExist
    except APICredentials.DoesNotExist:
        messages.warning(request, "Please set up your API credentials in the settings before accessing BFMR deals.")
        return redirect('settings')

    api_url = "https://api.bfmr.com/api/v2/deals"
    
    headers = {
        "API-KEY": api_credentials.api_key,
        "API-SECRET": api_credentials.api_secret
    }
    
    # You can add query parameters as needed
    params = {
        "page_size": 50,  # Adjust as needed
        "page_no": 1,     # Adjust as needed
        # Add other parameters as required
    }
    
    try:
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        deals = data.get('deals', [])
        
        # Process the deals to include price and discount information
        for deal in deals:
            deal['price'] = deal.get('price', 'N/A')
            deal['discount'] = deal.get('discount', 'N/A')
            if deal['price'] != 'N/A' and deal['discount'] != 'N/A':
                deal['discounted_price'] = float(deal['price']) - float(deal['discount'])
            else:
                deal['discounted_price'] = 'N/A'
        
    except requests.RequestException as e:
        deals = []
        messages.error(request, "Failed to fetch deals from BFMR. Please check your API credentials.")
        # Log the error
        logger.error(f"BFMR API request failed: {str(e)}")
        if response:
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response content: {response.text}")
    
    return render(request, 'core/bfmr_deals.html', {'deals': deals})

@require_http_methods(["GET", "POST"])
def deal_calculator(request):
    if request.method == 'POST':
        form = DealCalculatorForm(request.POST)
        if form.is_valid():
            purchase_price = form.cleaned_data['purchase_price']
            reimbursement_price = form.cleaned_data['reimbursement_price']
            cashback_percentage = form.cleaned_data['cashback_percentage']
            
            results = calculate_roc(purchase_price, reimbursement_price, cashback_percentage)
            
            return JsonResponse(results)
        else:
            return JsonResponse({'error': 'Invalid form data'}, status=400)
    else:
        form = DealCalculatorForm()
    
    return render(request, 'core/deal_calculator.html', {'form': form})

def calculate_roc(purchase_price, reimbursement_price, cashback_percentage):
    """Calculates the Return on Cost (ROC) and provides a deal quality assessment."""
    purchase_price = Decimal(str(purchase_price))
    reimbursement_price = Decimal(str(reimbursement_price))
    cashback_percentage = Decimal(str(cashback_percentage))

    cashback = purchase_price * (cashback_percentage / 100)
    difference = purchase_price - reimbursement_price
    profit = cashback - difference
    roc = (profit / purchase_price) * 100

    if roc >= 6:
        result = "Excellent Deal!"
    elif roc >= 3.39 and roc < 6:
        result = "Great Deal!"
    elif roc >= 1 and roc < 3.39:
        result = "Okay Deal."
    elif roc >= 0 and roc < 1:
        result = "Fair Deal."
    else:
        result = "Bad Deal."

    return {
        "profit": float(profit),
        "roc": float(roc),
        "result": result
    }

class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    def get(self, request, *args, **kwargs):
        messages.success(request, "We've emailed you instructions for setting your password. You should receive them shortly.")
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('home')  # Replace 'home' with your home page URL name