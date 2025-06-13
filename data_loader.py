##dashboard/data_loader.py
import os
import pandas as pd
import streamlit as st

class DataLoader:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(current_dir, "data")
        
        self.schema = {
            "inventory_ledger.csv": [
                "date", "product_id", "supplier_id", "lead_time_used",
                "opening_stock", "demand", "units_sold", "unmet_demand",
                "restocked_qty", "closing_stock", "next_arrival"
            ],
            "inventory_policy.csv": [
                "product_id", "supplier_id", "eoq", "reorder_point",
                "monthly_demand", "safety_stock", "unit_cost", "total_monthly_cost"
            ],
            "clean_forecast.csv": ["date", "product_id", "predicted_units"],
            "suppliers1.csv": ["supplier_id", "MOQ", "cost", "lead_time", "reliability","products"],
            "products.csv": ["product_id", "release_date", "base_price"],
            "sales_with_pricing_new(1).csv": ["date", "product_id", "current_price"]
        }
        
        self.ledger = None
        self.policies = None
        self.forecast = None
        self.suppliers = None
        self.products = None
        self.sales = None
        
        self._load_all_data()

    def _validate_data_dir(self):
        """Ensure data directory exists"""
        if not os.path.exists(self.data_dir):
            st.error(f"Missing data directory: {self.data_dir}")
            st.stop()

    def _load_all_data(self):
        """Load all datasets with error handling"""
        try:
            self.ledger = self._load_csv("inventory_ledger.csv", parse_dates=["date", "next_arrival"])
            self.policies = self._load_csv("inventory_policy.csv")
            self.forecast = self._load_csv("clean_forecast.csv", parse_dates=["date"])
            self.suppliers = self._load_csv("suppliers1.csv")
            self.products = self._load_csv("products.csv", parse_dates=["release_date"])
            self.sales = self._load_csv("sales_with_pricing_new(1).csv", parse_dates=["date"])
            
            self._post_process_data()
            
        except Exception as e:
            st.error(f"Critical data loading error: {str(e)}")
            st.stop()

    def _post_process_data(self):
        """Data cleaning and transformation"""
        if self.ledger is not None:
            self.ledger["supplier_id"] = self.ledger["supplier_id"].astype(str)
        if self.suppliers is not None:
            self.suppliers["supplier_id"] = self.suppliers["supplier_id"].astype(str)
            self.suppliers["lead_time"] = self.suppliers["lead_time"].clip(1, 30).astype(int)
            self.suppliers["reliability"] = self.suppliers["reliability"].clip(1, 100)

    def _load_csv(self, filename, parse_dates=None):
        """Enhanced CSV loader with validation"""
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            st.error(f"Missing required file: {filename}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(path, parse_dates=parse_dates)
            required_cols = self.schema.get(filename, [])
            
            # Validate columns
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Missing columns in {filename}: {', '.join(missing_cols)}")
                return pd.DataFrame()
                
            return df
            
        except Exception as e:
            st.error(f"Error loading {filename}: {str(e)}")
            return pd.DataFrame()


    def get_product_data(self, product_id):
        """For Inventory and What-If tabs"""
        return {
            'policy': self.policies[self.policies["product_id"] == product_id].iloc[0] if not self.policies.empty else None,
            'suppliers': self.suppliers[self.suppliers["products"] == product_id] if not self.suppliers.empty else None,
            'forecast': self.forecast[self.forecast["product_id"] == product_id] if not self.forecast.empty else None,
            'sales': self.sales[self.sales["product_id"] == product_id] if not self.sales.empty else None
        }

    def load_inventory_ledger(self):
        """Load and preprocess inventory ledger"""
        df = self._load_csv("inventory_ledger.csv")
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df["next_arrival"] = pd.to_datetime(df["next_arrival"])
        return df

    def load_inventory_policy(self):
        """Load and validate inventory policies"""
        return self._load_csv("inventory_policy.csv")

    def load_forecast(self):
        """Load forecast data with date parsing"""
        df = self._load_csv("clean_forecast.csv")
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df

    def load_suppliers(self):
        """Load supplier data with type conversion"""
        df = self._load_csv("suppliers1.csv")
        if not df.empty:
            df["lead_time"] = df["lead_time"].astype(int)
        return df

    def get_merged_ledger(self):
        """Merge ledger with policy and supplier data"""
        if self.ledger.empty or self.policies.empty or self.suppliers.empty:
            return pd.DataFrame()

        # First merge policies
        merged = pd.merge(
            self.ledger,
            self.policies[["product_id", "reorder_point", "safety_stock"]],
            on="product_id",
            how="left"
        )
        
        # Then merge suppliers
        merged = pd.merge(
            merged,
            self.suppliers[["supplier_id", "MOQ", "lead_time", "reliability","products"]],
            on="supplier_id",
            how="left"
        )
        
        # Final validation
        required_cols = ["MOQ", "reliability", "lead_time","products"]
        if not all(col in merged.columns for col in required_cols):
            st.error("Critical columns missing after merge")
            return pd.DataFrame()
            
        return merged