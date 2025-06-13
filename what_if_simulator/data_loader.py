from pathlib import Path
import pandas as pd
from typing import Dict, Any
REQUIRED_COLUMNS = {
    "clean_forecast.csv": ["date", "product_id", "predicted_units"],
    "inventory_ledger.csv": ["date", "product_id", "opening_stock", "supplier_id"],
    "inventory_policy.csv": ["product_id", "eoq", "reorder_point", "safety_stock"],
    "suppliers1.csv": ["supplier_id", "lead_time", "MOQ", "reliability", "cost"]
}

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self._validate_schemas()
        
    def _validate_schemas(self):
        for file, cols in REQUIRED_COLUMNS.items():
            df = pd.read_csv(self.data_dir/file, encoding='utf-8', engine='python')
            missing = set(cols) - set(df.columns)
            if missing:
                raise ValueError(f"{file} missing columns: {missing}")

    def load_product_data(self, product_id: str) -> Dict[str, Any]:
        """Returns unified product-supplier data"""
        data = {}

        files = {
            'policy': 'inventory_policy.csv',
            'ledger': 'inventory_ledger.csv',
            'forecast': 'clean_forecast.csv',
            'supplier': 'suppliers1.csv'
        }

        for key, file in files.items():
            path = self.data_dir / file

            if key in ['ledger', 'forecast']:  # Only these have a 'date' column
                df = pd.read_csv(path, parse_dates=['date'], dayfirst=True)
            else:
                df = pd.read_csv(path)

            # Handle each case
            if key == 'supplier':
                supplier_id = self._get_product_supplier(product_id)
                filtered = df[df['supplier_id'] == supplier_id]
            else:
                filtered = df[df['product_id'] == product_id]

            # Validation for unique entries where expected
            if key in ['policy', 'supplier']:
                if len(filtered) > 1:
                    raise ValueError(f"Multiple {key} entries for {product_id}")
                elif len(filtered) == 0:
                    raise ValueError(f"No {key} entry found for {product_id}")
                data[key] = filtered.iloc[0].to_dict()
            else:
                data[key] = filtered

        return data


    def _get_product_supplier(self, product_id):
        ledger = pd.read_csv(self.data_dir / "inventory_ledger.csv")
        match = ledger[ledger['product_id'] == product_id]
        if match.empty:
            raise ValueError("Product not found in ledger")
        return match['supplier_id'].iloc[0]
    
    def load_all_suppliers(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "suppliers1.csv")

