import pandas as pd
from datetime import date, timedelta
from typing import Dict, Optional
from .order_manager import OrderManager
from .order_manager import OrderFailedError
from .data_loader import DataLoader
from .utils import validate_date_range

class CostCalculator:
    """Tracks inventory-related costs"""
    def __init__(self, holding_rate: float, order_cost: float, stockout_penalty: float):
        self.holding_rate = 0.20  # default  # Daily holding cost rate
        self.order_cost = order_cost      # Cost per order
        self.stockout_penalty = stockout_penalty  # Per unit penalty
        
        self.total_holding = 0.0
        self.total_ordering = 0.0
        self.total_stockout = 0.0

    def update_costs(self, closing_stock: int, stockout_qty: int):
        """Update daily costs"""
        self.total_holding += closing_stock * self.holding_rate
        self.total_stockout += stockout_qty * self.stockout_penalty

    def add_order_cost(self):
        """Add cost when placing an order"""
        self.total_ordering += self.order_cost

    def set_holding_rate(self, rate: float):
        self.holding_rate = rate


class InventorySimulator:
    def __init__(self, product_id: str, holding_rate: Optional[float] = None, force_supplier_id: Optional[str] = None):
        self.product_id = product_id
        self.loader = DataLoader()
        self.product_data = self.loader.load_product_data(product_id)

        supplier = self.product_data['supplier']
        policy = self.product_data['policy']
        self.product_data['forecast']['date'] = pd.to_datetime(self.product_data['forecast']['date'])
        self.product_data['ledger']['date'] = pd.to_datetime(self.product_data['ledger']['date'])

        estimated_order_cost = 0.1 * supplier['MOQ'] * supplier['cost']
        self.order_mgr = OrderManager(supplier, override_supplier_id=force_supplier_id)

        self.rop = policy['reorder_point'] + policy['safety_stock']
        self.eoq = policy['eoq']
        annual_rate = holding_rate if holding_rate is not None else 0.25
        holding_cost_per_unit = policy['unit_cost'] * annual_rate

        self.cost_calc = CostCalculator(
            holding_rate=holding_cost_per_unit / 365,
            order_cost=estimated_order_cost,
            stockout_penalty=5.0
        )

    def run(
        self,
        start_date: date,
        end_date: date,
        demand_modifications: Optional[Dict[date, int]] = None,
        enable_risk: Optional[bool] = False,
        holding_rate: Optional[float] = None,
        force_supplier_id: Optional[str] = None
    ) -> Dict:
        # Apply runtime overrides if provided
        if holding_rate is not None:
            self.cost_calc.holding_rate = self.product_data['policy']['unit_cost'] * holding_rate / 365

        if force_supplier_id is not None:
            self._override_supplier(force_supplier_id)

        validate_date_range(self.product_data['forecast'], start_date, end_date)
        timeline = pd.date_range(start_date, end_date)
        results = []
        self._init_stock_state(start_date)

        for day in timeline:
            day_date = day.date()
            self._process_order_arrivals(day_date)
            demand = self._get_daily_demand(day_date, demand_modifications)
            stockout_qty = self._update_inventory(demand)
            self._check_reorder_point(day_date)
            self.cost_calc.update_costs(self.current_stock, stockout_qty)
            results.append(self._record_daily_result(day_date, demand, stockout_qty))

        return self._compile_results(results)
    

    def _override_supplier(self, supplier_id: str):
        supplier_row = self.loader.load_all_suppliers()
        match = supplier_row[supplier_row['supplier_id'] == supplier_id]
        if match.empty:
            raise ValueError(f"Supplier ID {supplier_id} not found.")
        self.order_mgr = OrderManager(match.iloc[0].to_dict())

    
    


    def _init_stock_state(self, start_date):
        """Initialize inventory from ledger"""
        ledger = self.product_data['ledger']
        
        # 🔧 Ensure 'date' is in datetime format
        ledger['date'] = pd.to_datetime(ledger['date'])

        # Get starting stock row
        opening_row = ledger[ledger['date'].dt.date == start_date]
        if opening_row.empty:
            raise ValueError(f"No inventory data for start date: {start_date}")
        
        self.current_stock = int(opening_row['opening_stock'].values[0])


    def _process_order_arrivals(self, current_date: date):
        """Add received orders to stock"""
        arrivals = self.order_mgr.get_pending_orders()
        for order in arrivals:
            if order['arrival_date'].date() == current_date:
                self.current_stock += order['quantity']

    def _get_daily_demand(self, date: date, modifications: Dict) -> int:
        """Get modified or baseline demand"""
        if modifications and date in modifications:
            return modifications[date]
        
        # Get from forecast
        forecast_df = self.product_data['forecast']
        day_match = forecast_df[forecast_df['date'].dt.date == date]
        if day_match.empty:
            raise ValueError(f"No forecast available for date: {date}")
        
        return int(day_match['predicted_units'].iloc[0])


    def _update_inventory(self, demand: int) -> int:
        """Update stock levels and return stockout qty"""
        self.current_stock -= demand
        stockout = max(-self.current_stock, 0)
        self.current_stock = max(self.current_stock, 0)
        return stockout

    def _check_reorder_point(self, date: date):
        """Trigger reorder if needed"""
        if self.current_stock <= self.rop and not self.order_mgr.get_pending_orders():
            try:
                self.order_mgr.place_order(date, self.eoq)
                self.cost_calc.add_order_cost()
            except OrderFailedError:
                pass  # Handle supplier failure

    def _record_daily_result(self, date: date, demand: int, stockout: int) -> Dict:
        return {
            'date': date,
            'demand': demand,
            'stockout': stockout,
            'inventory': self.current_stock,
            'pending_orders': len(self.order_mgr.get_pending_orders())
        }

    def _compile_results(self, daily_records: list) -> Dict:
        """Format final output"""
        df = pd.DataFrame(daily_records)
        df.set_index('date', inplace=True)
        
        return {
            'timeline': df,
            'metrics': {
                'total_holding_cost': round(self.cost_calc.total_holding, 2),
                'total_stockout_cost': round(self.cost_calc.total_stockout, 2),
                'total_ordering_cost': round(self.cost_calc.total_ordering, 2),
                'stockout_days': df['stockout'].gt(0).sum()
            }
        }
    
    