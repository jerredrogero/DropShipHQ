from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.conf import settings as django_settings
from django.http import JsonResponse
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, F, DecimalField, Q
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from .models import Order, APICredentials, BuyingGroup, Account, Merchant, Card, Subscription, UserProfile
from .forms import OrderForm, APICredentialsForm, DealCalculatorForm, CustomUserCreationForm, BuyingGroupForm, AccountForm, MerchantForm, CardForm
from datetime import datetime
from django.utils import timezone
import requests
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
import calendar
from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import FormView
from .forms import UserCreationForm
from django.contrib.auth import views as auth_views
import stripe
import json
import os
from django.http import HttpResponse
from django.contrib import messages
import logging
from django.contrib.auth import authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, authenticate
from django.views import View
from django.contrib import messages
from django.views.generic import TemplateView
from .decorators import check_subscription

logger = logging.getLogger(__name__)
stripe.api_key = django_settings.STRIPE_SECRET_KEY


def home(request):
    stripe_key = django_settings.STRIPE_PUBLISHABLE_KEY
    print(f"STRIPE_PUBLISHABLE_KEY from settings: {stripe_key}")
    print(f"STRIPE_PUBLISHABLE_KEY from os.environ: {os.environ.get('STRIPE_PUBLISHABLE_KEY')}")
    return render(request, 'core/home.html', {'stripe_key': stripe_key})

class AuthView(View):
    def get(self, request):
        login_form = AuthenticationForm()
        signup_form = CustomUserCreationForm()
        return render(request, 'registration/auth.html', {
            'login_form': login_form,
            'signup_form': signup_form
        })

    def post(self, request):
        action = request.POST.get('action')
        if action == 'login':
            return self.handle_login(request)
        elif action == 'signup':
            return self.handle_signup(request)
        else:
            messages.error(request, "Invalid action.")
            return redirect('auth')

    def handle_login(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
        login_form = form
        signup_form = CustomUserCreationForm()
        return render(request, 'registration/auth.html', {
            'login_form': login_form,
            'signup_form': signup_form
        })

    def handle_signup(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. You are now logged in.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
        login_form = AuthenticationForm()
        signup_form = form
        return render(request, 'registration/auth.html', {
            'login_form': login_form,
            'signup_form': signup_form
        })

class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'

    def get(self, request, *args, **kwargs):
        messages.success(request, "Your password has been set. You may go ahead and log in now.")
        return super().get(request, *args, **kwargs)

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
    total_cash_back = sum(
        (Decimal(order.cost) if order.cost is not None else Decimal(0)) * 
        (Decimal(order.cash_back) if order.cash_back is not None else Decimal(0)) / Decimal(100) 
        for order in orders
    )
    summary['total_cash_back'] = Decimal(total_cash_back).quantize(Decimal('0.01'))

    # Calculate total profit
    summary['total_profit'] = (
        summary['total_reimbursed'] - summary['total_cost'] + summary['total_cash_back']
    )

    subscription, created = Subscription.objects.get_or_create(user=request.user, defaults={'plan': 'FREE', 'status': 'active'})

    # Handle form submission for adding new order
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            if subscription.can_create_order():
                order = form.save(commit=False)
                order.user = request.user
                order.save()
                messages.success(request, 'Order added successfully.')
                return redirect('dashboard')
            else:
                messages.warning(request, f"You've reached the limit of orders for your {subscription.get_plan_display()} plan. Please upgrade your plan.")
                return redirect('pricing')
    else:
        form = OrderForm(user=request.user)
        if not subscription.can_create_order():
            form = None  # Disable the form if the limit is reached

    # Fetch other necessary data
    buying_groups = BuyingGroup.objects.filter(user=request.user)
    accounts = Account.objects.filter(user=request.user)
    merchants = Merchant.objects.filter(user=request.user)
    cards = Card.objects.filter(user=request.user)

    context = {
        'orders': orders.values(
            'id', 'date', 'buying_group__name', 'account__name', 'order_number', 
            'tracking_number', 'product', 'merchant__name', 'card__name', 
            'cost', 'reimbursed', 'cash_back', 'paid',
            'buying_group_id', 'account_id', 'merchant_id', 'card_id'
        ),
        'summary': summary,
        'form': form,
        'buying_groups': buying_groups,
        'accounts': accounts,
        'merchants': merchants,
        'cards': cards,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'subscription': subscription,
    }

    return render(request, 'core/dashboard.html', context)
@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.save()
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
    
@login_required
@require_POST
def update_paid_status(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    paid = request.POST.get('paid') == 'true'
    order.paid = paid
    order.save()
    return JsonResponse({'success': True})

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
def account_settings(request):
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
        elif 'delete_account' in request.POST:
            # Handle account deletion
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Your account has been deleted successfully.")
            return redirect(reverse('home'))  # Redirect to home page
        
        if 'delete_account' not in request.POST:
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
        'account_form': account_form if not request.method == 'POST' else None,
        'merchant_form': merchant_form if not request.method == 'POST' else None,
        'card_form': card_form if not request.method == 'POST' else None,
        'buying_group_form': buying_group_form if not request.method == 'POST' else None,
        'api_credentials_form': api_credentials_form if not request.method == 'POST' else None,
    }
    return render(request, 'core/settings.html', context)

@login_required
def delete_buying_group(request, buying_group_id):
    buying_group = get_object_or_404(BuyingGroup, id=buying_group_id)
    buying_group.delete()
    messages.success(request, 'Buying group deleted successfully.')
    return redirect('settings')

@csrf_exempt
@login_required
def bfmr_deals(request):
    try:
        api_credentials = APICredentials.objects.get(user=request.user)
        if not api_credentials.api_key or not api_credentials.api_secret:
            raise APICredentials.DoesNotExist
    except APICredentials.DoesNotExist:
        messages.warning(request, "Please set up your API credentials in the settings before accessing BFMR deals.")
        return redirect('settings')

    if request.method == 'POST':
        deal_id = request.POST.get('deal_id')
        item_id = request.POST.get('item_id')
        item_qty = request.POST.get('item_qty')
        
        logger.info(f"Attempting to reserve: deal_id={deal_id}, item_id={item_id}, item_qty={item_qty}")
        
        url = 'https://api.bfmr.com/api/v2/deals/reserve'
        headers = {
            'API-KEY': api_credentials.api_key,
            'API-SECRET': api_credentials.api_secret,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'deal_id': deal_id,
            'item_id': item_id,
            'item_qty': item_qty
        }
        logger.info(f"Sending data to BFMR API: {data}")
        try:
            response = requests.post(url, headers=headers, data=data)
            logger.info(f"BFMR API response: status_code={response.status_code}, content={response.text}")
            
            if response.status_code == 200:
                messages.success(request, 'Quantity reserved successfully.')
                logger.info("Reservation successful")
                return JsonResponse({'status': 'success', 'message': 'Quantity reserved successfully.'})
            else:
                error_message = response.json().get('message', 'Unknown error occurred')
                messages.error(request, f'Failed to reserve quantity. Error: {error_message}')
                logger.error(f"Reservation failed: {error_message}")
                return JsonResponse({'status': 'error', 'message': error_message})
        except requests.RequestException as e:
            messages.error(request, f'Failed to reserve quantity. Error: {str(e)}')
            logger.exception("Exception occurred while making API request")
            return JsonResponse({'status': 'error', 'message': str(e)})

    url = 'https://api.bfmr.com/api/v2/deals'
    headers = {
        'API-KEY': api_credentials.api_key,
        'API-SECRET': api_credentials.api_secret
    }
    params = {
        'page_size': 10,
        'page_no': 1,
        'exclusive_deals_only': '0'
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        deals_data = response.json().get('deals', [])
        
        # Process the deals to include price difference information
        deals = []
        for deal in deals_data:
            retail_price = float(deal.get('retail_price', 0))
            payout_price = float(deal.get('payout_price', 0))
            price_difference = payout_price - retail_price
            difference_percentage = (price_difference / retail_price) * 100 if retail_price > 0 else 0
            
            # Extract the URL from the nested structure
            product_url = ''
            items = deal.get('items', [])
            if items:
                retailer_links = items[0].get('retailer_links', [])
                if retailer_links:
                    product_url = retailer_links[0].get('url', '')
            
            processed_deal = {
                'deal_id': deal.get('deal_id'),
                'title': deal.get('title'),
                'retail_price': '{:.2f}'.format(retail_price),
                'payout_price': '{:.2f}'.format(payout_price),
                'price_difference': '{:.2f}'.format(price_difference),
                'difference_percentage': '{:.2f}'.format(difference_percentage),
                'product_url': product_url,  # Use the extracted URL
                'item_id': items[0].get('id') if items else '',
                'items': items
            }
            deals.append(processed_deal)
        
        # Log the structure of the first deal for debugging
        if deals:
            logger.info(f"First deal structure: {json.dumps(deals[0], indent=2)}")
        else:
            logger.warning("No deals returned from the API")
        
    except requests.RequestException as e:
        deals = []
        messages.error(request, f'Failed to fetch active deals. Error: {str(e)}')
        logger.exception("Exception occurred while fetching deals")
    
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

@csrf_exempt  # Stripe sends POST requests without CSRF tokens
def stripe_webhook(request):
    logger.info("Received Stripe webhook")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = django_settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        logger.info(f"Received event: {event['type']}")

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_checkout_session(session)
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            handle_invoice_payment_succeeded(invoice)
        elif event['type'] == 'customer.subscription.deleted':
            subscription_obj = event['data']['object']
            handle_subscription_deleted(subscription_obj)
        # Handle other event types as needed

        return HttpResponse(status=200)

    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        # Other errors
        logger.error(f"Webhook error: {e}")
        return HttpResponse(status=400)

def handle_checkout_session(session):
    user_id = session['metadata'].get('user_id')
    plan = session['metadata'].get('plan')

    logger.info(f"Handling checkout session for user_id: {user_id}, plan: {plan}")

    if not user_id or not plan:
        logger.error("Missing user_id or plan in session metadata.")
        return

    try:
        user = User.objects.get(id=user_id)
        subscription, created = Subscription.objects.get_or_create(user=user)
        
        logger.info(f"Before update - User: {user.username}, Current plan: {subscription.plan}")

        # Map the Stripe plan to the corresponding Subscription plan
        plan_mapping = {
            'STARTER_MONTHLY': 'STARTER',
            'STARTER_YEARLY': 'STARTER',
            'PRO_MONTHLY': 'PRO',
            'PRO_YEARLY': 'PRO',
            'PREMIUM_MONTHLY': 'PREMIUM',
            'PREMIUM_YEARLY': 'PREMIUM',
            'ENTERPRISE': 'ENTERPRISE'
        }
        
        subscription_plan = plan_mapping.get(plan, 'FREE')
        subscription.plan = subscription_plan
        subscription.stripe_subscription_id = session.get('subscription')
        subscription.status = 'active'
        stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        subscription.end_date = timezone.make_aware(datetime.fromtimestamp(stripe_subscription.current_period_end))
        subscription.save()

        logger.info(f"After update - User: {user.username}, New plan: {subscription.plan}")

        # Verify the update
        updated_subscription = Subscription.objects.get(user=user)
        logger.info(f"Verification - User: {user.username}, Verified plan: {updated_subscription.plan}")

    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist.")
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
    except Exception as e:
        logger.exception(f"Error updating subscription: {e}")

def handle_invoice_payment_succeeded(invoice):
    stripe_subscription_id = invoice['subscription']
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
        subscription.status = 'active'
        subscription.end_date = timezone.make_aware(datetime.fromtimestamp(invoice['current_period_end']))
        subscription.save()
        logger.info(f"Invoice payment succeeded for subscription {stripe_subscription_id}.")
    except Subscription.DoesNotExist:
        logger.error(f"Subscription with ID {stripe_subscription_id} does not exist.")

def handle_subscription_deleted(subscription_obj):
    stripe_subscription_id = subscription_obj['id']
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
        subscription.plan = 'FREE'  # Revert to a free plan or handle accordingly
        subscription.status = 'canceled'
        subscription.save()
        logger.info(f"Subscription {stripe_subscription_id} canceled.")
    except Subscription.DoesNotExist:
        logger.error(f"Subscription with ID {stripe_subscription_id} does not exist.")

def pricing(request):
    context = {
        'STRIPE_PUBLISHABLE_KEY': django_settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'core/pricing.html', context)

@require_POST
def upgrade_plan(request, plan):
    logger.info(f"Upgrade plan request received for plan: {plan}")
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    
    try:
        # Determine if we're in test or live mode
        is_test_mode = django_settings.STRIPE_SECRET_KEY.startswith('sk_test_')
        logger.info(f"Is test mode: {is_test_mode}")
        
        price_id_map = { 
            'STARTER_MONTHLY': 'price_1PziYBCBOzePXFXg12Gae4C9' if is_test_mode else 'price_1PzO0qCBOzePXFXgKJPYibZ2',
            'STARTER_YEARLY': 'price_1PziYVCBOzePXFXgF6lSxldU' if is_test_mode else 'price_1PzO0qCBOzePXFXgwSmjzykE',
            'PRO_MONTHLY': 'price_1PziYhCBOzePXFXggTJr6tvD' if is_test_mode else 'price_1PzO4RCBOzePXFXgCIidB5SY',
            'PRO_YEARLY': 'price_1PziYhCBOzePXFXggTJr6tvD' if is_test_mode else 'price_1PzO53CBOzePXFXgHSia7bMR',
            'PREMIUM_MONTHLY': 'price_1PziYtCBOzePXFXgbKXzXbJk' if is_test_mode else 'price_1PzO7ZCBOzePXFXgk7aY8TC7',
            'PREMIUM_YEARLY': 'price_1PziYtCBOzePXFXgbKXzXbJk' if is_test_mode else 'price_1PzO7ZCBOzePXFXgB2OUmrxI',
            'ENTERPRISE': 'price_1Hh1XYZabcEnterprisePriceID' if is_test_mode else 'price_live_enterprise',
        }

        if plan not in price_id_map:
            return JsonResponse({'error': 'Invalid plan selected.'}, status=400)
        
        price_id = price_id_map[plan]
        logger.info(f"Selected price ID: {price_id}")
        
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            
        if not user_profile.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.username,
            )
            user_profile.stripe_customer_id = customer.id
            user_profile.save()
            logger.info(f"Created new Stripe customer: {customer.id}")
        else:
            customer = stripe.Customer.retrieve(user_profile.stripe_customer_id)
            logger.info(f"Retrieved existing Stripe customer: {customer.id}")
        
        logger.info(f"Creating checkout session with price_id: {price_id}")
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri(reverse('upgrade_success')) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse('pricing')),
            metadata={
                'user_id': request.user.id,
                'plan': plan,
            },
        )
        logger.info(f"Created checkout session: {checkout_session.id}")
        
        return JsonResponse({'sessionId': checkout_session.id})
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error in upgrade_plan: {e}")
        return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)


@login_required
def upgrade_success(request):
    session_id = request.GET.get('session_id')
    logger.info(f"Upgrade success called with session_id: {session_id}")
    
    if not session_id:
        logger.error('No session ID provided.')
        messages.error(request, 'No session ID provided.')
        return redirect('dashboard')
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        logger.info(f"Retrieved session: {session.id}, mode: {session.mode}")
        
        customer = stripe.Customer.retrieve(session.customer)
        logger.info(f"Retrieved customer: {customer.id}")
        
        # Update user's Stripe customer ID if not already set
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not user_profile.stripe_customer_id:
            user_profile.stripe_customer_id = customer.id
            user_profile.save()
            logger.info(f"Updated user profile with Stripe customer ID: {customer.id}")
        
        # Update the user's subscription
        subscription, created = Subscription.objects.get_or_create(user=request.user)
        subscription.stripe_subscription_id = session.subscription
        subscription.status = 'active'
        
        # Map the plan from the session metadata to your Subscription model's plan choices
        plan_mapping = {
            'STARTER_MONTHLY': 'STARTER',
            'STARTER_YEARLY': 'STARTER',
            'PRO_MONTHLY': 'PRO',
            'PRO_YEARLY': 'PRO',
            'PREMIUM_MONTHLY': 'PREMIUM',
            'PREMIUM_YEARLY': 'PREMIUM',
            'ENTERPRISE': 'ENTERPRISE'
        }
        session_plan = session.metadata.get('plan')
        subscription.plan = plan_mapping.get(session_plan, 'FREE')
        
        subscription.save()
        logger.info(f"Updated subscription: plan={subscription.plan}, status={subscription.status}")
        
        messages.success(request, 'Your subscription has been successfully upgraded!')
        return redirect('dashboard')
    
    except Exception as e:
        logger.exception(f"An error occurred during upgrade_success: {str(e)}")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('dashboard')

@login_required
def get_item_id(request):
    deal_id = request.GET.get('deal_id')
    logger.info(f"Attempting to get item_id for deal_id: {deal_id}")

    try:
        api_credentials = APICredentials.objects.get(user=request.user)
    except APICredentials.DoesNotExist:
        logger.error("API credentials not found for user")
        return JsonResponse({'error': 'API credentials not set up'}, status=400)

    url = f'https://api.bfmr.com/api/v2/deals/{deal_id}'
    headers = {
        'API-KEY': api_credentials.api_key,
        'API-SECRET': api_credentials.api_secret
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        deal_data = response.json()
        logger.info(f"API response for deal {deal_id}: {json.dumps(deal_data, indent=2)}")

        items = deal_data.get('items', [])
        if items and len(items) > 0:
            item_id = items[0].get('id')
            if item_id:
                logger.info(f"Found item_id: {item_id} for deal_id: {deal_id}")
                return JsonResponse({'item_id': item_id})
            else:
                logger.warning(f"No 'id' found in first item for deal_id: {deal_id}")
                return JsonResponse({'error': 'No item id found in deal data'}, status=404)
        else:
            logger.warning(f"No items found for deal_id: {deal_id}")
            return JsonResponse({'error': 'No items found for this deal'}, status=404)
    except requests.RequestException as e:
        logger.exception(f"Error fetching deal data: {str(e)}")
        return JsonResponse({'error': f'Error fetching deal data: {str(e)}'}, status=500)
    except json.JSONDecodeError as e:
        logger.exception(f"Error decoding JSON response: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON response from API'}, status=500)
    except Exception as e:
        logger.exception(f"Unexpected error in get_item_id: {str(e)}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

class TermsOfServiceView(TemplateView):
    template_name = 'core/terms_of_service.html'

class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html'
