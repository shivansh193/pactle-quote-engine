# src/app/outputs.py (FINAL ROBUST VERSION)

import csv
from fpdf import FPDF
from pathlib import Path
from .models import Quote

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Quotation', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_csv(quote: Quote, file_path: Path):
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Line No', 'SKU', 'Description', 'Qty', 'UOM', 'Unit Price', 'Amount', 'Status', 'Reason'])
        for line in quote.lines:
            writer.writerow([
                line.line_no,
                line.sku or 'N/A',
                line.description or line.input_text,
                line.qty if line.qty is not None else 'N/A',
                line.uom or 'N/A',
                f'{line.unit_price:.2f}' if line.unit_price is not None else 'N/A',
                f'{line.amount:.2f}' if line.amount is not None else 'N/A',
                line.explain.status,
                line.explain.reason
            ])

def generate_pdf(quote: Quote, file_path: Path):
    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(40, 10, f'Quote ID: {quote.quote_id}')
    pdf.ln(5)
    pdf.cell(40, 10, f'Buyer: {quote.buyer_id}')
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(10, 10, 'Sr', 1)
    pdf.cell(30, 10, 'SKU', 1)
    pdf.cell(75, 10, 'Description', 1)
    pdf.cell(15, 10, 'Qty', 1)
    pdf.cell(20, 10, 'Unit Price', 1)
    pdf.cell(30, 10, 'Amount', 1)
    pdf.ln()

    pdf.set_font('Arial', '', 10)
    for line in quote.lines:
        # ** FIX: Only draw resolved lines with prices in the main table **
        if line.resolved:
            pdf.cell(10, 10, str(line.line_no), 1)
            pdf.cell(30, 10, str(line.sku), 1)
            pdf.cell(75, 10, str(line.description), 1)
            pdf.cell(15, 10, str(line.qty), 1)
            # ** FIX: Check for None before formatting **
            unit_price_str = f'{line.unit_price:,.2f}' if line.unit_price is not None else 'N/A'
            amount_str = f'{line.amount:,.2f}' if line.amount is not None else 'N/A'
            pdf.cell(20, 10, unit_price_str, 1, 0, 'R')
            pdf.cell(30, 10, amount_str, 1, 0, 'R')
            pdf.ln()
    
    pdf.ln(10)
    totals = quote.totals
    
    def add_total_line(label, value):
        pdf.set_font('Arial', '', 10)
        pdf.cell(130)
        pdf.cell(30, 8, label, 1)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(30, 8, f'{value:,.2f}', 1, 1, 'R')

    add_total_line('Subtotal', totals.subtotal)
    if totals.discount_amount > 0:
        add_total_line(f'Discount ({totals.header_discount_pct}%)', -totals.discount_amount)
    add_total_line('Freight', totals.freight)
    add_total_line('Total Tax (GST)', totals.total_tax)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(130)
    pdf.cell(30, 10, 'Grand Total', 1)
    pdf.cell(30, 10, f'{totals.grand_total:,.2f}', 1, 1, 'R')
    
    pdf.output(str(file_path))