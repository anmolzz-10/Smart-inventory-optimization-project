# dashboard/app.py
import streamlit as st
from data_loader import DataLoader

# Initialize FIRST - before any session state access
if 'data_loader' not in st.session_state:
    st.session_state.data_loader = DataLoader()

# Set page config AFTER initialization
st.set_page_config(
    page_title="Smart Inventory Dashboard",
    layout="wide",
    menu_items={
        'Get Help': 'https://example.com',
        'About': "# Inventory Optimization Dashboard"
    }
)

# Import components AFTER initialization
from overview_tab import overview_tab
from inventory_tab import show_inventory
from suppliers_tab import render_supplier_tab
from sim import what_if_tab

# Navigation
tab = st.sidebar.radio("📁 Navigate", [
    "📊 Overview",
    "📦 Inventory",
    "🤝 Supplier Studio",
    "🧪 What-If Simulator",
])

# Tab routing
if tab == "📊 Overview":
    overview_tab()
elif tab == "📦 Inventory":
    show_inventory(st.session_state.data_loader)
elif tab == "🤝 Supplier Studio":
    render_supplier_tab()
elif tab == "🧪 What-If Simulator":
    what_if_tab()


