from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, F, DecimalField, Q
from django.db.models.functions import Coalesce
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
from django.conf import settings as django_settings
import stripe
import json
import os

logger = logging.getLogger(__name__)

def home(request):
    stripe_key = django_settings.STRIPE_PUBLISHABLE_KEY
    print(f"STRIPE_PUBLISHABLE_KEY from settings: {stripe_key}")
    print(f"STRIPE_PUBLISHABLE_KEY from os.environ: {os.environ.get('STRIPE_PUBLISHABLE_KEY')}")
    return render(request, 'core/home.html', {'stripe_key': stripe_key})


@login_required
def dashboard(request):
    # Get date range and search query from request parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('search', '')

    # Base queryset
    orders = Order.objects.filter(user=request.user)

    # Apply date filtering if dates are provided
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        orders = orders.filter(date__range=[start_date, end_date])

    # Apply search filtering
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(tracking_number__icontains=search_query) |
            Q(product__icontains=search_query)
        )

    # Order the queryset
    orders = orders.order_by('-date')

    # Calculate summary statistics
    summary = orders.aggregate(
        total_cost=Coalesce(Sum('cost'), Decimal('0')),
        total_reimbursed=Coalesce(Sum('reimbursed'), Decimal('0')),
    )
    
    # Calculate total cash back
    total_cash_back = sum(order.cost * order.cash_back / 100 for order in orders)
    summary['total_cash_back'] = Decimal(total_cash_back).quantize(Decimal('0.01'))

    # Calculate total profit
    summary['total_profit'] = (
        summary['total_reimbursed'] - summary['total_cost'] + summary['total_cash_back']
    )

    # Handle form submission for adding new order
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

    # Fetch other necessary data
    buying_groups = BuyingGroup.objects.filter(user=request.user)
    accounts = Account.objects.filter(user=request.user)
    merchants = Merchant.objects.filter(user=request.user)
    cards = Card.objects.filter(user=request.user)

    context = {
        'orders': orders,
        'summary': summary,
        'form': form,
        'buying_groups': buying_groups,
        'accounts': accounts,
        'merchants': merchants,
        'cards': cards,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
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

@csrf_exempt
def stripe_donation(request):
    if request.method == 'POST':
        stripe_secret_key = django_settings.STRIPE_SECRET_KEY
        if not stripe_secret_key:
            return JsonResponse({'error': 'Stripe secret key is not set'}, status=500)
        
        stripe.api_key = stripe_secret_key
        try:
            data = json.loads(request.body)
            amount = int(float(data['amount']) * 100)  # Convert to cents
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                payment_method_types=['card'],
            )
            return JsonResponse({'clientSecret': intent.client_secret})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=400)
