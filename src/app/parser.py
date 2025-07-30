# src/app/parser.py (FINAL AND DEFINITIVE VERSION)

import re
from typing import List
from .models import ParsedLine

# --- Definitions ---
UOM_KEYWORDS = { 'm': 'M', 'mtr': 'M', 'meter': 'M', 'meters': 'M', 'pc': 'PC', 'pcs': 'PC', 'nos': 'PC', 'no': 'PC', 'pes': 'PC', 'coil': 'COIL', 'coils': 'COIL', 'pack': 'PACK', 'packs': 'PACK'}
MATERIAL_KEYWORDS = { 'pp': 'PP', 'fr': 'FRPP', 'frpp': 'FRPP', 'fr-pp': 'FRPP', 'pvc': 'PVC', 'gi': 'GI', 'ms': 'MS', 'nylon': 'NYLON'}
NUMBER_PATTERN = re.compile(r'\d+(?:\.\d+)?')
SIZE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(mm|inch|"|\')', re.IGNORECASE)

# --- THE CRITICAL FIX IS HERE ---
# This pattern now finds the quantity, the unit, AND any optional material that follows.
# This makes our "markers" for slicing much more accurate.
material_alternatives = '|'.join(MATERIAL_KEYWORDS.keys())
uom_alternatives = '|'.join(UOM_KEYWORDS.keys())
QTY_UOM_MARKER_PATTERN = re.compile(
    r'\d+\.?\d*\s*(?:' + uom_alternatives + r')\b(?:\s*(?:' + material_alternatives + r'))?', 
    re.IGNORECASE
)

def _clean_line_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower().replace('-', ' ')).strip()

# --- NEW, ROBUST LINE SPLITTER using the "Iterative Slicing" strategy ---
def split_text_by_item_markers(text: str) -> List[str]:
    # 1. Clean up the entire string first.
    clean_text = re.sub(r'.*quotation for:|pls quote|quote for', '', text, flags=re.IGNORECASE)
    clean_text = clean_text.replace(';', ' ').replace(',', ' ').replace('\n', ' ')
    clean_text = re.sub(r'\s+and\s+', ' ', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    # 2. Find all the robust markers.
    markers = list(re.finditer(QTY_UOM_MARKER_PATTERN, clean_text))
    if not markers: return [clean_text] if len(clean_text) > 3 else []

    # 3. Slice the string based on the end position of each marker.
    lines, start_pos = [], 0
    for marker in markers:
        end_pos = marker.end()
        lines.append(clean_text[start_pos:end_pos].strip())
        start_pos = end_pos
    
    return [line for line in lines if line]

# --- The main function uses the new, correct splitter ---
def parse_rfq_to_lines(rfq_text: str) -> List[ParsedLine]:
    raw_lines = split_text_by_item_markers(rfq_text)
    parsed_lines = []
    for line in raw_lines:
        clean_line = _clean_line_text(line)
        parsed_obj = ParsedLine(raw_text=line)
        
        # Extract Quantity and UOM
        qty_uom_extract_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(' + uom_alternatives + r')\b', re.IGNORECASE)
        qty_match = qty_uom_extract_pattern.search(clean_line)
        if qty_match:
            parsed_obj.quantity = float(qty_match.group(1))
            parsed_obj.uom = UOM_KEYWORDS[qty_match.group(2).lower()]
            temp_clean_line = clean_line.replace(qty_match.group(0), '', 1)
        else:
            temp_clean_line = clean_line
            
        # Extract other details from the remaining text
        size_match = SIZE_PATTERN.search(temp_clean_line)
        if size_match:
            size_value = float(size_match.group(1))
            size_unit = size_match.group(2).lower().strip()
            parsed_obj.size = size_value * 25.4 if size_unit in ['inch', '"', "'"] else size_value

        parsed_obj.material_keywords = [norm for key, norm in MATERIAL_KEYWORDS.items() if re.search(r'\b' + key + r'\b', clean_line)]
        
        desc_line = re.sub(QTY_UOM_MARKER_PATTERN, '', clean_line)
        desc_line = re.sub(SIZE_PATTERN, '', desc_line)
        parsed_obj.description_keywords = [word for word in desc_line.split() if word not in MATERIAL_KEYWORDS and not word.isdigit()]
        
        parsed_lines.append(parsed_obj)
        
    return parsed_lines