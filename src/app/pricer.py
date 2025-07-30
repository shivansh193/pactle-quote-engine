# src/app/pricer.py

from .models import Quote, TaxBreakup, Totals
import json # ADD THIS

def calculate_quote_totals(quote: Quote, freight_is_taxable: bool, freight_amount_rule: dict) -> Quote:
    """
    Calculates all totals for the quote object.
    This function modifies the quote object in place.
    """
    subtotal = 0.0
    tax_map = {} # To group items by HSN code for tax calculation

    for line in quote.lines:
        if line.resolved and line.unit_price is not None and line.qty is not None:
            # Calculate line amount
            line.amount = round(line.unit_price * line.qty, 2)
            subtotal += line.amount
            
            # Group taxable amounts by HSN code
            if line.hsn_code not in tax_map:
                tax_map[line.hsn_code] = {'taxable_amount': 0.0, 'gst_pct': line.tax_pct}
            tax_map[line.hsn_code]['taxable_amount'] += line.amount
    
    # --- Calculate Totals ---
    totals = Totals()
    totals.subtotal = round(subtotal, 2)
    
    # Apply header discount
    totals.header_discount_pct = quote.header_discount_pct
    totals.discount_amount = round(totals.subtotal * (totals.header_discount_pct / 100), 2)
    totals.net_after_discount = totals.subtotal - totals.discount_amount
    
    # Apply freight rule
    # Example rule: {"threshold": 50000, "charge": 1000, "free_if_above": True}
    if totals.net_after_discount < freight_amount_rule.get("threshold", 50000):
        totals.freight = freight_amount_rule.get("charge", 1000)
    else:
        totals.freight = 0.0

    # Calculate final taxable amount
    taxable_base = totals.net_after_discount
    if freight_is_taxable:
        taxable_base += totals.freight
    
    totals.taxable_amount = taxable_base
    
    # Calculate taxes
    total_tax = 0.0
    tax_breakup_list = []

    # This is a bit complex. We need to distribute the discount proportionally
    # across the HSN groups before calculating tax.
    if totals.subtotal > 0:
        discount_ratio = totals.discount_amount / totals.subtotal
    else:
        discount_ratio = 0

    for hsn, data in tax_map.items():
        original_hsn_total = data['taxable_amount']
        discount_for_hsn = original_hsn_total * discount_ratio
        net_hsn_total = original_hsn_total - discount_for_hsn
        
        # Now calculate tax on the net amount for this HSN group
        gst_pct = data['gst_pct']
        gst_amount = round(net_hsn_total * (gst_pct / 100), 2)
        total_tax += gst_amount
        
        tax_breakup_list.append(TaxBreakup(
            hsn_code=hsn,
            taxable_amount=round(net_hsn_total, 2),
            gst_pct=gst_pct,
            gst_amount=gst_amount
        ))

    totals.tax_breakup = tax_breakup_list
    totals.total_tax = round(total_tax, 2)
    
    # Calculate Grand Total
    totals.grand_total = totals.net_after_discount + totals.total_tax + totals.freight
    
    # --- ADD THIS CURRENCY CONVERSION BLOCK AT THE END ---
    target_currency = quote.currency # Comes from the request, stored on the quote
    if target_currency != "INR":
        with open("src/data/fx_rates.json") as f:
            rates = json.load(f)
        rate = rates.get(target_currency)
        if rate:
            note = f"Converted to {target_currency} at a rate of 1 INR = {1/rate:.4f} {target_currency}. Original Grand Total: {totals.grand_total:,.2f} INR"
            quote.notes_and_assumptions.append(note)
            totals.grand_total = round(totals.grand_total / rate, 2)
            quote.currency = target_currency
    
    quote.totals = totals
    return quote