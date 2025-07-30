# src/app/main.py (FINAL AND COMPLETE VERSION)

import uuid, traceback, io, pandas as pd
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from .models import RFQRequest, Quote
from .parser import parse_rfq_to_lines
from .mapper import sku_mapper
from .pricer import calculate_quote_totals
from .outputs import generate_csv, generate_pdf
from .processor import RfqOCRProcessor

# --- App and Global Instances ---
app = FastAPI(title="Pactle Quote Engine")
ocr_processor = RfqOCRProcessor() # Load the OCR model once

# --- UI Serving ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_ui():
    return FileResponse('static/index.html')

# --- API Endpoints ---
@app.post("/generate-quote")
async def generate_quote(request: RFQRequest, response_format: str = 'json', is_approved: bool = False):
    try:
        rfq_text_to_process = ""
        if request.rfq_text:
            rfq_text_to_process = request.rfq_text
        elif request.chat_payload and 'text' in request.chat_payload:
            rfq_text_to_process = request.chat_payload['text']
        
        if not rfq_text_to_process:
            raise HTTPException(status_code=400, detail="No valid RFQ text or chat_payload provided.")

        parsed_lines = parse_rfq_to_lines(rfq_text_to_process)
        quote_lines = sku_mapper.create_quote_lines(parsed_lines)
        
        if is_approved:
            for i, line in enumerate(quote_lines):
                if not line.resolved and line.explain.candidates:
                    top_candidate_sku = line.explain.candidates[0]['sku']
                    top_item = next((item for item in sku_mapper.price_master if item.sku == top_candidate_sku), None)
                    if top_item:
                        explain = line.explain
                        explain.status = "APPROVED"
                        explain.reason = f"Manually approved from top candidate (Original score: {explain.score:.1f})"
                        quote_lines[i] = sku_mapper._create_matched_quoteline(parsed_lines[i], line.line_no, top_item, explain)
        
        quote = Quote(quote_id=f"Q-TXT-{uuid.uuid4().hex[:4].upper()}", lines=quote_lines, header_discount_pct=request.header_discount_pct, currency=request.target_currency)
        freight_rule = {"threshold": 50000, "charge": 1000}
        quote = calculate_quote_totals(quote=quote, freight_is_taxable=True, freight_amount_rule=freight_rule)
        
        output_dir = Path("outputs_generated"); output_dir.mkdir(exist_ok=True)

        if response_format.lower() == 'pdf':
            file_path = output_dir / f"{quote.quote_id}.pdf"
            generate_pdf(quote, file_path)
            return FileResponse(file_path, media_type='application/pdf', filename=f"{quote.quote_id}.pdf")
        elif response_format.lower() == 'csv':
            file_path = output_dir / f"{quote.quote_id}.csv"
            generate_csv(quote, file_path)
            return FileResponse(file_path, media_type='text/csv', filename=f"{quote.quote_id}.csv")
        else:
            return quote
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# --- THIS IS THE ENDPOINT THAT WAS MISSING ---
@app.post("/process-rfq-image")
async def process_rfq_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'): raise HTTPException(status_code=400, detail="File is not an image.")
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents))
        ocr_result = ocr_processor.process_pil_image(pil_image)
        
        if ocr_result.get("error"): raise HTTPException(status_code=500, detail=f"OCR failed: {ocr_result['error']}")
        
        cleaned_rfq_text = ocr_result.get("final_cleaned_text")
        if not cleaned_rfq_text: raise HTTPException(status_code=400, detail="OCR could not extract text.")
        
        parsed_lines = parse_rfq_to_lines(cleaned_rfq_text)
        quote_lines = sku_mapper.create_quote_lines(parsed_lines)
        quote = Quote(quote_id=f"Q-OCR-{uuid.uuid4().hex[:4].upper()}", lines=quote_lines, header_discount_pct=0.0)
        freight_rule = {"threshold": 50000, "charge": 1000}
        quote = calculate_quote_totals(quote=quote, freight_is_taxable=True, freight_amount_rule=freight_rule)
        
        return {"ocr_summary": ocr_result.get("summary"), "extracted_rfq_text": cleaned_rfq_text, "generated_quote": quote}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# --- THIS IS THE CSV ENDPOINT ---
@app.post("/process-rfq-csv")
async def process_rfq_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'): raise HTTPException(status_code=400, detail="File is not a CSV.")
    try:
        df = pd.read_csv(io.BytesIO(await file.read()))
        desc_col = next((col for col in df.columns if col.lower() in ['desc', 'description', 'item']), None)
        qty_col = next((col for col in df.columns if col.lower() in ['qty', 'quantity']), None)
        uom_col = next((col for col in df.columns if col.lower() in ['uom', 'unit']), None)

        if not all([desc_col, qty_col, uom_col]): raise HTTPException(status_code=400, detail="CSV must contain columns for description, quantity, and UOM.")

        rfq_text = "\n".join([f"{row[desc_col]} {row[qty_col]} {row[uom_col]}" for _, row in df.iterrows()])
        
        parsed_lines = parse_rfq_to_lines(rfq_text)
        quote_lines = sku_mapper.create_quote_lines(parsed_lines)
        quote = Quote(quote_id=f"Q-CSV-{uuid.uuid4().hex[:4].upper()}", lines=quote_lines, header_discount_pct=0.0)
        freight_rule = {"threshold": 50000, "charge": 1000}
        quote = calculate_quote_totals(quote=quote, freight_is_taxable=True, freight_amount_rule=freight_rule)

        return {"original_csv_text": rfq_text, "generated_quote": quote}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")