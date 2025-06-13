import pandas as pd
import datetime
from pathlib import Path
import os

class InventoryContinuityError(Exception):
    pass

def validate_date_range(forecast_df, start_date, end_date):
    forecast_dates = pd.to_datetime(forecast_df['date'])
    if start_date < forecast_dates.min().date() or end_date > forecast_dates.max().date():
        raise ValueError("Simulation dates outside forecast range")

def convert_date_format(date_str):
    return datetime.datetime.strptime(date_str, "%d-%m-%Y").date()

def validate_supplier_product_link(product_id, supplier_id):
    ledger = pd.read_csv(r'D:\middle_ground_inventory\what_if_simulator\data\inventory_ledger.csv')
    match = ledger[
        (ledger['product_id'] == product_id) & 
        (ledger['supplier_id'] == supplier_id)
    ]
    if match.empty:
        raise ValueError("Product-supplier mismatch")

import pandas as pd

class InventoryContinuityError(Exception):
    pass

def validate_opening_stocks(data_dir: str, product_id: str):
    path = os.path.join(data_dir, "inventory_ledger.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["product_id"] == product_id].sort_values("date").reset_index(drop=True)

    for i in range(1, len(df)):
        prev_close = df.loc[i - 1, "closing_stock"]
        current_open = df.loc[i, "opening_stock"]

        if current_open > prev_close:
            # A restock must've happened
            restock = current_open - prev_close
            restock_reported = df.loc[i - 1, "restocked_qty"]
            if abs(restock - restock_reported) > 1:
                mismatch_date = df.loc[i, "date"].date()
                raise InventoryContinuityError(
                    f"❗ Mismatch on {mismatch_date} for {product_id}: "
                    f"Expected restock of ~{restock}, but ledger recorded {restock_reported}."
                )

def validate_date_range(forecast_df, start_date, end_date):
    """
    Ensure the given date range is fully covered by the forecast dataframe.
    
    Args:
        forecast_df (pd.DataFrame): DataFrame with at least a 'date' column.
        start_date (datetime.date): Simulation start date.
        end_date (datetime.date): Simulation end date.

    Raises:
        ValueError: If the date range is outside forecast bounds.
    """
    if forecast_df.empty or 'date' not in forecast_df.columns:
        raise ValueError("Invalid forecast data provided.")

    # Ensure 'date' column is datetime
    forecast_df['date'] = pd.to_datetime(forecast_df['date'])

    min_forecast_date = forecast_df['date'].min().date()
    max_forecast_date = forecast_df['date'].max().date()

    if start_date < min_forecast_date or end_date > max_forecast_date:
        raise ValueError(
            f"Simulation range {start_date} to {end_date} is outside forecast range "
            f"{min_forecast_date} to {max_forecast_date}"
        )



