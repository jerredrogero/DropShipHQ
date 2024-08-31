from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Avg, Count, Value
from django.db.models.functions import Cast, Coalesce
from .models import Order
from .forms import OrderForm
from datetime import datetime, timedelta
from django.utils import timezone

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
            messages.success(request, 'Order saved successfully.')
            return redirect('dashboard')
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

    # Filter orders based on date range
    orders_list = Order.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by('-date')

    # Calculate summary data
    summary = orders_list.aggregate(
        total_cost=Sum('cost', output_field=DecimalField(max_digits=10, decimal_places=2)),
        total_reimbursed=Sum('reimbursed', output_field=DecimalField(max_digits=10, decimal_places=2)),
        total_profit=Sum(
            ExpressionWrapper(
                F('reimbursed') - F('cost') + (F('cost') * F('cash_back') / 100),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        avg_profit=Avg(
            ExpressionWrapper(
                F('reimbursed') - F('cost') + (F('cost') * F('cash_back') / 100),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        total_orders=Count('id')
    )

    # Handle potential None values
    for key in summary:
        if summary[key] is None:
            summary[key] = 0

    # Calculate average profit per order
    if summary['total_orders'] > 0:
        summary['avg_profit_per_order'] = summary['total_profit'] / summary['total_orders']
    else:
        summary['avg_profit_per_order'] = 0

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(orders_list, 10)  # Show 10 orders per page
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    context = {
        'form': form,
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
@require_http_methods(["POST"])
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.delete()
    messages.success(request, 'Order deleted successfully.')
    return JsonResponse({'status': 'success'})

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