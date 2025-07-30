# debug_parser.py

import re
from typing import List

# --- This is your code, copied exactly ---
UOM_KEYWORDS = {
    'm': 'M', 'mtr': 'M', 'meter': 'M', 'meters': 'M', 'metres': 'M',
    'pc': 'PC', 'pcs': 'PC', 'piece': 'PC', 'pieces': 'PC', 'nos': 'PC', 'no': 'PC',
    'coil': 'COIL', 'coils': 'COIL',
    'pack': 'PACK', 'packs': 'PACK', 'packet': 'PACK', 'pkts': 'PACK',
    'set': 'SET', 'sets': 'SET',
    'roll': 'ROLL', 'rolls': 'ROLL',
    'length': 'M', 'lengths': 'M'
}
HEADER_PATTERNS = [
    r'.*?(?:pls\s+)?quote(?:\s+for)?:?\s*', r'.*?quotation\s+for:?\s*', r'.*?please\s+quote:?\s*',
    r'.*?kindly\s+quote:?\s*', r'.*?quote\s+request:?\s*', r'.*?rfq:?\s*',
    r'.*?request\s+for\s+quotation:?\s*', r'dear\s+sir[,/]?\s*', r'hello[,]?\s*', r'hi[,]?\s*'
]
def create_qty_uom_pattern():
    uom_alternatives = '|'.join(re.escape(uom) for uom in UOM_KEYWORDS.keys())
    return re.compile(r'\b(\d+(?:\.\d+)?)\s*(' + uom_alternatives + r')\b', re.IGNORECASE)
QTY_UOM_PATTERN = create_qty_uom_pattern()
# --- End of copied code ---


def remove_headers(text: str) -> str:
    text = text.strip()
    for pattern in HEADER_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        text = text.strip()
    return text

# --- THIS IS THE FUNCTION WE WILL DEBUG ---
def split_text_by_item_markers(text: str) -> List[str]:
    print("--- STARTING PARSER DEBUG ---")
    print(f"1. Initial Input Text:\n   '{text}'")
    
    clean_text = remove_headers(text)
    print(f"\n2. Text after removing headers:\n   '{clean_text}'")
    
    clean_text = clean_text.replace(';', ' ').replace(',', ' ').replace('\n', ' ').replace('\t', ' ')
    clean_text = re.sub(r'\s+and\s+(?=\d)', ' ', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    print(f"\n3. Text after cleaning separators:\n   '{clean_text}'")

    markers = list(QTY_UOM_PATTERN.finditer(clean_text))
    print(f"\n4. Found {len(markers)} markers (qty+uom):")
    if not markers:
        print("   !!! CRITICAL: NO MARKERS WERE FOUND. The regex pattern failed. !!!")
    else:
        for i, marker in enumerate(markers):
            print(f"   - Marker {i+1}: '{marker.group(0)}' found at position {marker.start()}-{marker.end()}")

    if not markers:
        return [clean_text] if len(clean_text.strip()) > 3 else []
    
    lines = []
    for i, marker in enumerate(markers):
        start_pos = markers[i-1].end() if i > 0 else 0
        end_pos = marker.end()
        line = clean_text[start_pos:end_pos].strip()
        if line:
            lines.append(line)
            
    print("\n5. Extracted Lines:")
    for i, line in enumerate(lines):
        print(f"   - Line {i+1}: '{line}'")
    
    print("\n--- DEBUG FINISHED ---")
    return [line for line in lines if line and len(line.strip()) > 3]

# --- Main test block ---
if __name__ == "__main__":
    test_input = 'pls quote 20mm flex conduit 600m, 40mm corr pipe 150m FRPP, and 3" heavy hex fan box cpwd 25 nos'
    split_text_by_item_markers(test_input)