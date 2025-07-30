# src/app/models.py (FINAL CORRECTED VERSION)

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Represents a single row in your price_master.csv
class PriceMasterItem(BaseModel):
    sku: str = Field(..., alias='sku_code')
    family: str = Field(..., alias='product_family')
    item_description: str = Field(..., alias='description')
    hsn_code: str = Field(..., alias='hsn_code')
    uom: str = Field(..., alias='uom')
    coil_length_m: Optional[float] = Field(None, alias='coil_length_m')
    material: str = Field(..., alias='material')
    gauge: Optional[str] = Field(None, alias='gauge')
    size_od_mm: Optional[float] = Field(None, alias='size_od_mm')
    aux_size: Optional[str] = Field(None, alias='aux_size')
    colour: Optional[str] = Field(None, alias='colour')
    moq: Optional[int] = Field(None, alias='moq')
    lead_time_days: Optional[int] = Field(None, alias='lead_time_days')
    rate_pp: Optional[float] = Field(None, alias='rate_inr')
    rate_frpp: Optional[float] = Field(None, alias='rate_alt_inr')
    alt_material: Optional[str] = Field(None, alias='alt_material')

# Represents a single row in your taxes.csv
class TaxItem(BaseModel):
    hsn_code: str = Field(..., alias='Hsn_code')
    gst_pct: float = Field(..., alias='gst_pct')

# A temporary container for info extracted from one line of an RFQ
class ParsedLine(BaseModel):
    raw_text: str
    quantity: Optional[float] = None
    uom: Optional[str] = None
    size: Optional[float] = None
    material_keywords: List[str] = []
    description_keywords: List[str] = []

# Holds the reasoning behind a match decision
class Explainability(BaseModel):
    input_text: str
    status: str
    matched_sku: Optional[str] = None
    score: float = 0.0
    reason: str
    candidates: List[Dict[str, Any]] = []
    assumptions: List[str] = []

# The final, resolved line item in a quote
class QuoteLine(BaseModel):
    line_no: int
    input_text: str
    resolved: bool = False
    sku: Optional[str] = None
    description: Optional[str] = None
    qty: Optional[float] = None
    uom: Optional[str] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    tax_pct: float = 18.0
    hsn_code: Optional[str] = None
    explain: Explainability

# Breakup of taxes by HSN code
class TaxBreakup(BaseModel):
    hsn_code: str
    taxable_amount: float
    gst_pct: float
    gst_amount: float

# The final totals for the quote
class Totals(BaseModel):
    subtotal: float = 0.0
    header_discount_pct: float = 0.0
    discount_amount: float = 0.0
    net_after_discount: float = 0.0
    freight: float = 0.0
    taxable_amount: float = 0.0
    total_tax: float = 0.0
    grand_total: float = 0.0
    tax_breakup: List[TaxBreakup] = []

# The complete Quote object that will be returned as JSON
class Quote(BaseModel):
    quote_id: str
    revision: int = 1
    buyer_id: Optional[str] = "ACME01"
    currency: str = "INR"
    lines: List[QuoteLine] = []
    # THIS IS THE CORRECT LOCATION
    header_discount_pct: float = 0.0
    totals: Totals = Field(default_factory=Totals)
    notes_and_assumptions: List[str] = []

# Input model for the API request
class RFQRequest(BaseModel):
    rfq_text: str
    header_discount_pct: float = 0.0
    freight_is_taxable: bool = True
    target_currency: str = "INR" # ADD THIS LINE