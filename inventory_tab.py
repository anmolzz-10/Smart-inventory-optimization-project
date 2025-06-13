# dashboard/inventory_tab.py
import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import DataLoader

def load_inventory_data(loader):
    """Load and merge required inventory data"""
    try:
        ledger = loader.load_inventory_ledger()
        policies = loader.load_inventory_policy()
        
        if ledger.empty or policies.empty:
            st.error("Missing inventory data!")
            return pd.DataFrame(), pd.DataFrame()
            
        # Merge critical policy columns
        policy_cols = ['product_id', 'reorder_point', 'safety_stock', 'eoq']
        merged = pd.merge(
            ledger,
            policies[policy_cols],
            on='product_id',
            how='left'
        )
        
        return merged, policies
    
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def show_inventory(loader):
    """Main inventory tab display"""
    st.title("📦 Live Inventory Management")
    
    # Load merged data
    merged_ledger, policies = load_inventory_data(loader)
    
    if merged_ledger.empty:
        return
        
    # Product Selection
    product_list = merged_ledger['product_id'].unique()
    selected_product = st.selectbox(
        "Select Product", 
        product_list,
        help="Choose a product to view detailed inventory information"
    )
    
    # Filter data for selected product
    product_data = merged_ledger[merged_ledger['product_id'] == selected_product]
    product_policy = policies[policies['product_id'] == selected_product].iloc[0]
    
    # Section 1: Stock Movement
    st.header(f"📈 {selected_product} Stock Movement")
    
    # Create time series chart
    fig = px.line(
        product_data,
        x='date',
        y=['opening_stock', 'closing_stock'],
        labels={'value': 'Units', 'variable': 'Stock Type'},
        title=f"Daily Stock Levels - {selected_product}"
    )
    fig.add_hline(
        y=product_policy['reorder_point'],
        line_dash="dash",
        line_color="red",
        annotation_text="Reorder Point"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Section 2: Restock History
    st.header("🔄 Restock History")
    restocks = product_data[product_data['restocked_qty'] > 0]
    
    if not restocks.empty:
        st.dataframe(
            restocks[['date', 'restocked_qty', 'supplier_id', 'next_arrival']],
            column_config={
                "next_arrival": st.column_config.DateColumn(
                    "Expected Arrival",
                    format="YYYY-MM-DD"
                )
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No restocks recorded for this product")
    
    # Section 3: Policy Details
    st.header("⚙️ Inventory Policy Details")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Stock", int(product_data['closing_stock'].iloc[-1]))
    with col2:
        st.metric("Reorder Point", product_policy['reorder_point'])
    with col3:
        st.metric("Safety Stock", product_policy['safety_stock'])
    
    # Policy Table
    st.dataframe(
        product_policy[['eoq', 'monthly_demand', 'unit_cost']]
        .reset_index()
        .rename(columns={'index': 'Metric', 0: 'Value'}),
        column_config={
            "Metric": st.column_config.TextColumn("Policy Metric"),
            "Value": st.column_config.NumberColumn(format="%.2f")
        },
        hide_index=True,
        use_container_width=True
    )