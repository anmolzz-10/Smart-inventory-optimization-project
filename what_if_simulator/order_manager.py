import random 
import pandas as pd
from pandas.tseries.offsets import BusinessDay

class OrderFailedError(Exception):
    pass

class OrderManager:
    def __init__(self, supplier_data, override_supplier_id=None):
        self.lead_time = supplier_data['lead_time']
        self.moq = supplier_data['MOQ']
        self.reliability = supplier_data['reliability']
        self.pending_orders = []
        self.override_supplier_id = override_supplier_id  # Placeholder for future use

    def place_order(self, order_date, needed_qty):
        """MOQ-enforced ordering with reliability check"""
        if random.random() > self.reliability:
            raise OrderFailedError("Supplier reliability check failed")
            
        order_qty = max(needed_qty, self.moq)
        arrival_date = self._calculate_arrival(order_date)
        
        self.pending_orders.append({
            'arrival_date': arrival_date,
            'quantity': order_qty,
            'status': 'pending'
        })

    def _calculate_arrival(self, order_date):
        """Applies lead time with calendar awareness"""
        return order_date + BusinessDay(self.lead_time)
    
    def get_pending_orders(self):
        return self.pending_orders
