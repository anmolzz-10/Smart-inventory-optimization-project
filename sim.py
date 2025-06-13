# dashboard/what_if_simulator.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px

class InventorySimulator:
    def __init__(self, data_loader):
        self.loader = data_loader
        self.HOLDING_RATE_DAILY = 0.20 / 365
        self.ORDER_COST = 500

    def simulate_product(self, product_id, scenario_params=None):
        """Run simulation with customizable business parameters"""
        try:
            # Load base data
            base_policy = self.loader.policies.query(f"product_id == '{product_id}'").iloc[0].copy()
            suppliers = self.loader.suppliers.query(f"products == '{product_id}'")
            forecast = self.loader.forecast.query(f"product_id == '{product_id}'").copy()
            
            # Apply scenario overrides
            if scenario_params:
                supplier = suppliers[
                    suppliers["supplier_id"] == scenario_params.get('supplier_id', base_policy['supplier_id'])
                ].iloc[0].copy()
                
                policy = base_policy.copy()
                policy.update({
                    'eoq': scenario_params.get('eoq', base_policy['eoq']),
                    'reorder_point': scenario_params.get('reorder_point', base_policy['reorder_point']),
                    'safety_stock': scenario_params.get('safety_stock', base_policy['safety_stock'])
                })
                buffer_days = scenario_params.get('buffer_days', 7)
            else:
                supplier = suppliers[
                    suppliers["supplier_id"] == base_policy['supplier_id']
                ].iloc[0].copy()
                policy = base_policy.copy()
                buffer_days = 7

            # Convert dates
            forecast["date"] = pd.to_datetime(forecast["date"])
            start_date = pd.to_datetime("2025-04-01")
            end_date = start_date + timedelta(days=30 + self._adjusted_lead_time(supplier))

            # Initialize simulation
            current_stock = self._calculate_initial_stock(policy, supplier, forecast, buffer_days)
            pending_orders = []
            ledger = []

            for date in pd.date_range(start_date, end_date):
                # Process order arrivals
                arrived = sum(qty for d, qty in pending_orders if d == date)
                current_stock += arrived
                pending_orders = [(d, qty) for d, qty in pending_orders if d > date]

                # Get daily demand
                try:
                    demand = forecast.loc[forecast["date"] == date, "predicted_units"].values[0]
                except IndexError:
                    demand = 0

                # Calculate transactions
                sold = min(current_stock, demand)
                unmet = max(0, demand - sold)
                closing_stock = current_stock - sold

                # Order placement logic
                restock_qty = 0
                if closing_stock < policy["reorder_point"] and not pending_orders:
                    order_qty = max(policy["eoq"], supplier["MOQ"])
                    lead_time = self._adjusted_lead_time(supplier)
                    arrival_date = date + timedelta(days=lead_time)
                    pending_orders.append((arrival_date, int(order_qty)))
                    restock_qty = int(order_qty)

                # Calculate costs
                holding_cost = closing_stock * policy["unit_cost"] * self.HOLDING_RATE_DAILY
                ordering_cost = self.ORDER_COST if restock_qty > 0 else 0

                ledger.append({
                    "date": date.date(),
                    "opening_stock": int(current_stock),
                    "demand": int(demand),
                    "sold": int(sold),
                    "unmet_demand": int(unmet),
                    "closing_stock": int(closing_stock),
                    "restock_qty": restock_qty,
                    "holding_cost": float(holding_cost),
                    "ordering_cost": int(ordering_cost),
                    "supplier": str(supplier["supplier_id"])
                })
                current_stock = closing_stock

            return pd.DataFrame(ledger)
        
        except Exception as e:
            st.error(f"Simulation failed: {str(e)}")
            return pd.DataFrame()

    def _adjusted_lead_time(self, supplier):
        """Apply reliability penalty to lead time"""
        lead_time = int(supplier["lead_time"].item())
        reliability_factor = (100 - supplier["reliability"].item()) / 100
        return int(lead_time * (1 + reliability_factor))

    def _calculate_initial_stock(self, policy, supplier, forecast, buffer_days):
        """Calculate safety stock with customizable buffer"""
        adjusted_lt = self._adjusted_lead_time(supplier)
        start_date = pd.to_datetime("2025-04-01")
        
        # Lead time demand calculation
        lt_demand = forecast[
            forecast["date"].between(start_date, start_date + timedelta(days=adjusted_lt))
        ]["predicted_units"].sum()
        
        # Safety stock with configurable buffer
        daily_std = forecast["predicted_units"].std()
        safety_stock = np.ceil(1.65 * daily_std * np.sqrt(adjusted_lt + buffer_days))
        
        return max(policy["reorder_point"], int(lt_demand + safety_stock))

def what_if_tab():
    """Interactive scenario analysis with comparison capabilities"""
    st.header("🧪 Strategic Inventory Scenario Analyzer")
    
    if 'data_loader' not in st.session_state:
        st.error("Data not loaded!")
        return
    
    loader = st.session_state.data_loader
    simulator = InventorySimulator(loader)
    
    # Product selection
    product = st.selectbox(
        "Select Product", 
        loader.policies["product_id"].unique(),
        help="Choose a product to analyze different inventory strategies"
    )
    
    # Scenario controls
    with st.expander("⚙️ Scenario Parameters", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Supplier selection
            suppliers = loader.suppliers.query(f"products == '{product}'")
            current_supplier = loader.policies.query(
                f"product_id == '{product}'")["supplier_id"].iloc[0]
            selected_supplier = st.selectbox(
                "Supplier",
                suppliers["supplier_id"].tolist(),
                index=suppliers["supplier_id"].tolist().index(current_supplier),
                help="Choose alternative supplier for comparison"
            )
            
            # EOQ configuration
            current_eoq = loader.policies.query(
                f"product_id == '{product}'")["eoq"].iloc[0]
            new_eoq = st.number_input(
                "Economic Order Quantity (EOQ)", 
                min_value=int(suppliers["MOQ"].min()),
                value=int(current_eoq),
                help="Optimal order quantity to minimize costs"
            )
            
        with col2:
            # Reorder point configuration
            current_rop = loader.policies.query(
                f"product_id == '{product}'")["reorder_point"].iloc[0]
            new_rop = st.number_input(
                "Reorder Point (ROP)",
                min_value=0,
                value=int(current_rop),
                help="Inventory level triggering new orders"
            )
            
            # Safety stock buffer
            buffer_days = st.slider(
                "Safety Buffer Days",
                0, 14, 7,
                help="Additional days buffer for safety stock calculation"
            )
    
    # Scenario comparison
    if st.button("▶️ Compare Scenarios", type="primary"):
        with st.spinner("Analyzing scenarios..."):
            # Base scenario
            base_results = simulator.simulate_product(product)
            
            # Custom scenario
            scenario_params = {
                'supplier_id': selected_supplier,
                'eoq': new_eoq,
                'reorder_point': new_rop,
                'buffer_days': buffer_days
            }
            scenario_results = simulator.simulate_product(product, scenario_params)
            
            if not base_results.empty and not scenario_results.empty:
                # Metrics calculation
                base_cost = base_results["holding_cost"].sum() + base_results["ordering_cost"].sum()
                scenario_cost = scenario_results["holding_cost"].sum() + scenario_results["ordering_cost"].sum()
                service_base = base_results["sold"].sum() / base_results["demand"].sum()
                service_scenario = scenario_results["sold"].sum() / scenario_results["demand"].sum()
                
                # Key metrics display
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Cost", f"${base_cost:,.2f}")
                col2.metric("Scenario Cost", f"${scenario_cost:,.2f}", 
                           delta=f"${scenario_cost - base_cost:,.2f}")
                col3.metric("Potential Savings", f"${base_cost - scenario_cost:,.2f}",
                           help="Estimated monthly savings")
                
                # Inventory comparison visual
                st.subheader("Inventory Level Projections")
                comparison_df = pd.concat([
                    base_results.assign(Scenario="Current"),
                    scenario_results.assign(Scenario="Proposed")
                ])
                
                fig = px.line(
                    comparison_df,
                    x="date",
                    y="closing_stock",
                    color="Scenario",
                    line_dash="Scenario",
                    labels={"closing_stock": "Inventory Level"},
                    title=f"Inventory Profile Comparison - {product}"
                )
                fig.add_hline(
                    y=new_rop,
                    line_dash="dot",
                    line_color="green",
                    annotation_text="New Reorder Point"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Cost breakdown analysis
                st.subheader("Cost Component Analysis")
                cost_data = pd.DataFrame({
                    "Current": [
                        base_results["holding_cost"].sum(),
                        base_results["ordering_cost"].sum()
                    ],
                    "Proposed": [
                        scenario_results["holding_cost"].sum(),
                        scenario_results["ordering_cost"].sum()
                    ]
                }, index=["Holding Costs", "Ordering Costs"])
                
                fig = px.bar(
                    cost_data.T,
                    barmode="group",
                    labels={"value": "Amount", "variable": "Cost Type"},
                    title="Cost Structure Comparison"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Supplier comparison matrix
                st.subheader("Supplier Comparison")
                current_supplier_data = suppliers.query(f"supplier_id == '{current_supplier}'").iloc[0]
                scenario_supplier_data = suppliers.query(f"supplier_id == '{selected_supplier}'").iloc[0]
                
                comparison_df = pd.DataFrame({
                    "Metric": ["Supplier ID", "Lead Time", "MOQ", "Reliability", "Unit Cost"],
                    "Current": [
                        current_supplier,
                        current_supplier_data["lead_time"],
                        current_supplier_data["MOQ"],
                        f"{current_supplier_data['reliability']}%",
                        f"${current_supplier_data['cost']:.2f}"
                    ],
                    "Proposed": [
                        selected_supplier,
                        scenario_supplier_data["lead_time"],
                        scenario_supplier_data["MOQ"],
                        f"{scenario_supplier_data['reliability']}%",
                        f"${scenario_supplier_data['cost']:.2f}"
                    ]
                })
                
                st.dataframe(
                    comparison_df,
                    column_config={
                        "Metric": st.column_config.TextColumn("Parameter"),
                        "Current": st.column_config.TextColumn("Current Supplier"),
                        "Proposed": st.column_config.TextColumn("Proposed Supplier")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Service level comparison
                st.subheader("Service Level Impact")
                col1, col2 = st.columns(2)
                col1.metric("Current Service Level", f"{service_base:.1%}")
                col2.metric("Projected Service Level", f"{service_scenario:.1%}",
                           delta=f"{(service_scenario - service_base):.1%}")
                
            else:
                st.warning("Simulation failed to generate comparable results")