from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Avg, Count, Value
from django.db.models.functions import Cast, Coalesce, TruncMonth
from .models import Order, APICredentials
from .forms import OrderForm, APICredentialsForm
from datetime import datetime, timedelta
from django.utils import timezone
import requests
from django.conf import settings
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            logger.info(f"Order saved successfully: ID {order.id}, Product: {order.product}")
            messages.success(request, f"Order for '{order.product}' has been added successfully.")
        else:
            if 'order_number' in form.errors:
                messages.error(request, "An order with this order number already exists.")
            else:
                messages.error(request, "There was an error with your submission. Please check the form.")
    else:
        form = OrderForm(user=request.user)

    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Set default date range if not provided (e.g., last 30 days)
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Include orders up to the end of the end_date
    end_date = end_date + timedelta(days=1)

    # Fetch all orders for the current user within the date range
    all_orders = Order.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by('-date')

    # Pagination for all orders
    paginator = Paginator(all_orders, 10)  # Show 10 orders per page
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    # Calculate summary data
    summary = all_orders.aggregate(
        total_cost=Sum('cost'),
        total_reimbursed=Sum('reimbursed'),
        total_profit=Sum(
            ExpressionWrapper(
                F('reimbursed') - F('cost') + (F('cost') * F('cash_back') / 100),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        avg_profit_per_order=Avg(
            ExpressionWrapper(
                F('reimbursed') - F('cost') + (F('cost') * F('cash_back') / 100),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
    )

    # Add this before rendering the template
    logger.info(f"Total orders for user {request.user.username}: {Order.objects.filter(user=request.user).count()}")

    context = {
        'form': OrderForm(user=request.user),
        'orders': orders,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'core/dashboard.html', context)

@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Order updated successfully.')
            return redirect('dashboard')
    else:
        form = OrderForm(instance=order, user=request.user)
    return render(request, 'core/edit_order.html', {'form': form, 'order': order})

@login_required
@require_POST
def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        order.delete()
        return JsonResponse({'status': 'success', 'message': 'Order deleted successfully'})
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('home')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}. You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def settings(request):
    api_credentials, created = APICredentials.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = APICredentialsForm(request.POST, instance=api_credentials)
        if form.is_valid():
            form.save()
            messages.success(request, 'API credentials updated successfully.')
            return redirect('settings')
    else:
        form = APICredentialsForm(instance=api_credentials)
    
    return render(request, 'core/settings.html', {'form': form})

@login_required
def bfmr_deals(request):
    api_url = "https://api.bfmr.com/api/v2/deals"
    
    # Get the user's API credentials
    api_credentials = APICredentials.objects.get(user=request.user)
    
    headers = {
        "API-KEY": api_credentials.bfmr_api_key,
        "API-SECRET": api_credentials.bfmr_api_secret
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
    except requests.RequestException as e:
        deals = []
        messages.error(request, "Failed to fetch deals from BFMR. Please check your API credentials.")
        # Log the error
        print(f"BFMR API request failed: {str(e)}")
        if response:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
    
    return render(request, 'core/bfmr_deals.html', {'deals': deals})