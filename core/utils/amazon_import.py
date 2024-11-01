import logging
from decimal import Decimal
from django.apps import apps
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

# Get models dynamically
Merchant = apps.get_model('core', 'Merchant')
Order = apps.get_model('core', 'Order')

def import_amazon_orders(user, email, password, otp=None):
    """Import Amazon orders"""
    logging.getLogger('amazonorders').setLevel(logging.ERROR)
    
    try:
        session = AmazonSession(email, password)
        session.logout()
        session.login()
        
        # Get or create Account for this Amazon email
        Account = apps.get_model('core', 'Account')
        account, _ = Account.objects.get_or_create(
            user=user,
            name=f'{email}'
        )
        
        amazon_orders = AmazonOrders(session)
        orders = amazon_orders.get_order_history()
        
        # Get or create Amazon merchant
        amazon_merchant, _ = Merchant.objects.get_or_create(
            user=user,
            name='Amazon'
        )
        
        imported_count = 0
        skipped_count = 0
        
        # Get existing orders
        existing_orders = set(Order.objects.filter(
            user=user,
            merchant=amazon_merchant
        ).values_list('order_number', flat=True))
        
        for amz_order in orders:
            try:
                if amz_order.order_number in existing_orders:
                    skipped_count += 1
                    continue
                
                # Get the order URL and product title
                order_url = f"https://www.amazon.com/gp/your-account/order-details?orderID={amz_order.order_number}"
                product_title = amz_order.items[0].title if amz_order.items else ''
                
                Order.objects.create(
                    user=user,
                    date=amz_order.order_placed_date,
                    order_number=f"<a href='{order_url}' target='_blank'>{amz_order.order_number}</a>",
                    merchant=amazon_merchant,
                    account=account,
                    cost=Decimal(str(amz_order.grand_total)),
                    product=product_title,
                    reimbursed=Decimal('0.00'),
                    cash_back=Decimal('0.00'),
                    paid=False
                )
                imported_count += 1
                
            except AttributeError as e:
                if 'recipient' in str(e):
                    continue
                raise e
            except Exception as e:
                print(f"Error importing order {getattr(amz_order, 'order_number', 'unknown')}: {str(e)}")
                continue
                
        return {
            'success': True,
            'imported': imported_count,
            'skipped': skipped_count
        }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    result = import_amazon_orders("your_email@example.com", "your_password", otp="your_otp")