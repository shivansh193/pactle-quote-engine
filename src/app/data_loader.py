# src/app/data_loader.py (REPLACE THE ENTIRE CLASS)

import pandas as pd
from typing import List, Dict
from pathlib import Path
from .models import PriceMasterItem, TaxItem

class DataLoader:
    def __init__(self, data_path: Path):
        # 1. Read the data, letting Pandas infer missing values as NaN
        self.price_master_df = pd.read_csv(data_path / "price_master.csv")
        self.taxes_df = pd.read_csv(data_path / "taxes.csv")

        # 2. --- DATA CLEANING STEP ---
        #    Replace pandas' NaN/NA representations with Python's None.
        #    Pydantic understands None for Optional fields, but not NaN.
        self.price_master_df = self.price_master_df.replace({pd.NA: None, float('nan'): None})

        # 3. Ensure key columns are the correct type before validation
        self.price_master_df['hsn_code'] = self.price_master_df['hsn_code'].astype(str)
        self.taxes_df['Hsn_code'] = self.taxes_df['Hsn_code'].astype(str)
        
        # 4. Now, with clean data, validate and create Pydantic models
        self.price_master_items: List[PriceMasterItem] = [
            PriceMasterItem(**row) for row in self.price_master_df.to_dict(orient='records')
        ]
        
        self.tax_items: List[TaxItem] = [
            TaxItem(**row) for row in self.taxes_df.to_dict(orient='records')
        ]
        
        self.tax_map: Dict[str, float] = {
            item.hsn_code: item.gst_pct for item in self.tax_items
        }

    def get_price_master(self) -> List[PriceMasterItem]:
        return self.price_master_items

    def get_tax_map(self) -> Dict[str, float]:
        return self.tax_map

# --- Singleton Instance ---
DATA_PATH = Path(__file__).parent.parent / "data"
data_loader = DataLoader(DATA_PATH)

# You can quickly verify the data is loaded by running this file directly
if __name__ == '__main__':
    print(f"Loaded {len(data_loader.get_price_master())} items from Price Master.")
    print(f"Loaded {len(data_loader.get_tax_map())} tax rates.")
    print("\nSample Price Master Item (First):")
    print(data_loader.get_price_master()[0].model_dump_json(indent=2))
    print("\nSample Price Master Item (With missing values):")
    print(data_loader.get_price_master()[6].model_dump_json(indent=2))
    print("\nTax Map:")
    print(data_loader.get_tax_map())