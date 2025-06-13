import streamlit as st
import pandas as pd
import os
from pathlib import Path
print("suppliers_tab.py loaded")

# Constants
SUMMARY_CSV = (r"D:\middle_ground_inventory\supplier_comparison\summary_report.csv")
REPORT_DIR = Path("D:/middle_ground_inventory/supplier_comparison/")

def load_data():
    summary_df = pd.read_csv(SUMMARY_CSV)
    return summary_df

def render_supplier_tab():
    st.header("🔍 Supplier Studio")
    st.markdown("Explore supplier rankings, comparisons, and opportunities for cost optimization.")

    summary_df = load_data()

    # --- Select Product for Comparison ---
    st.subheader("📦 Compare Suppliers for a Product")
    selected_product = st.selectbox("Choose a product ID", summary_df["product_id"].unique())

    if selected_product:
        product_row = summary_df[summary_df["product_id"] == selected_product].iloc[0]
        report_csv = REPORT_DIR / f"{selected_product}_report.csv"
        chart_png = REPORT_DIR / product_row["visualization"]

        if report_csv.exists():
            compare_df = pd.read_csv(report_csv)

            st.markdown(f"### 📈 Cost Breakdown — Product `{selected_product}`")
            st.image(str(chart_png), caption="Supplier Cost Comparison Chart", use_column_width=True)

            # Show best vs current
            col1, col2 = st.columns(2)
            with col1:
                st.metric("✅ Best Supplier", product_row["best_supplier"], delta=f"${product_row['best_cost']:.2f}")
            with col2:
                st.metric("📌 Current Supplier", product_row["current_supplier"], delta=f"${product_row['current_cost']:.2f}")

            st.markdown(f"💰 **Potential Monthly Savings:** `${product_row['potential_savings']:.2f}`")

            # Full comparison table
            st.markdown("#### 📋 Supplier Details")
            st.dataframe(
                compare_df[["supplier_id", "total_cost", "unit_cost", "moq", "lead_time", "reliability"]],
                use_container_width=True
            )
        else:
            st.warning(f"No comparison report found for {selected_product}.")
