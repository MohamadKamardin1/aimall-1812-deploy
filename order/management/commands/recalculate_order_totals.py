from django.core.management.base import BaseCommand
from order.models import Order
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalculate totals for all orders'

    def handle(self, *args, **options):
        orders = Order.objects.all()
        updated_count = 0
        
        for order in orders:
            try:
                # Store original values
                original_total = order.total_amount
                
                # Calculate totals
                order.calculate_totals()
                order.save(update_fields=['items_total', 'total_amount'])
                
                if original_total != order.total_amount:
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated Order #{order.order_number}: '
                            f'TSh {original_total} -> TSh {order.total_amount}'
                        )
                    )
                else:
                    self.stdout.write(
                        f'Order #{order.order_number}: TSh {order.total_amount} (no change)'
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating Order #{order.order_number}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} orders')
        )
