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
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.utils.dateparse import parse_date
import calendar

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    # Check if the remove filter button was clicked
    if 'remove_filter' in request.GET:
        return redirect('dashboard')

    # Get the current date
    today = timezone.now().date()

    # Calculate the first and last day of the current month
    first_day_of_month = today.replace(day=1)
    last_day_of_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    # Get the date range from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # If no dates are provided, use the current month
    if not start_date:
        start_date = first_day_of_month
    else:
        start_date = parse_date(start_date) or first_day_of_month

    if not end_date:
        end_date = last_day_of_month
    else:
        end_date = parse_date(end_date) or last_day_of_month

    # Ensure end_date is not before start_date
    if end_date < start_date:
        end_date = start_date

    # Check if a custom date range is being used
    is_filtered = start_date != first_day_of_month or end_date != last_day_of_month

    # Filter orders based on the date range
    orders = Order.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by('-date')

    # Calculate summary statistics
    summary = orders.aggregate(
        total_cost=Sum('cost'),
        total_reimbursed=Sum('reimbursed'),
        total_cash_back=Sum(ExpressionWrapper(
            F('cost') * F('cash_back') / 100,
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )),
        order_count=Count('id')
    )

    # Calculate total profit
    summary['total_profit'] = (
        (summary['total_reimbursed'] or 0) +
        (summary['total_cash_back'] or 0) -
        (summary['total_cost'] or 0)
    )

    # Calculate average profit per order
    if summary['order_count'] > 0:
        summary['avg_profit_per_order'] = summary['total_profit'] / summary['order_count']
    else:
        summary['avg_profit_per_order'] = 0

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            messages.success(request, 'Order created successfully.')
            return redirect('dashboard')
    else:
        form = OrderForm(user=request.user)

    context = {
        'form': form,
        'orders': orders,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
        'is_filtered': is_filtered,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        data = request.POST.dict()
        # Convert date string to datetime object
        if 'date' in data:
            try:
                data['date'] = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'errors': {'date': ['Invalid date format']}})
        
        form = OrderForm(data, instance=order, user=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    # GET request is no longer needed for this approach
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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