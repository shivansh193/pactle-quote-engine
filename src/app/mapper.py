# src/app/mapper.py (FINAL AND DEFINITIVE VERSION)

import re
from typing import List
from rapidfuzz import process, fuzz
from .models import ParsedLine, QuoteLine, PriceMasterItem, Explainability
from .data_loader import data_loader

# --- Configuration ---
SCORE_THRESHOLD_AUTO_MAP = 85
SCORE_DELTA_AUTO_MAP = 15
FAMILIES_WITHOUT_SIZE_FILTER = ["GI Fan Box", "Junction Box", "Modular Box", "Cable Tie", "Gland", "Saddle Clamp"]

class SkuMapper:
    def __init__(self, price_master: List[PriceMasterItem]):
        self.price_master = price_master

    def create_quote_lines(self, parsed_lines: List[ParsedLine]) -> List[QuoteLine]:
        quote_lines = []
        for i, line in enumerate(parsed_lines):
            quote_line = self._map_line_to_sku(line, line_no=i + 1)
            quote_lines.append(quote_line)
        return quote_lines

    def _map_line_to_sku(self, parsed_line: ParsedLine, line_no: int) -> QuoteLine:
        
        candidates = self.price_master
        search_query = " ".join(parsed_line.description_keywords + parsed_line.material_keywords)

        # --- Intelligent Filtering ---
        initial_candidates = self.price_master
        
        # Determine if this item type should skip the size filter
        should_skip_size_filter = False
        for family_keyword in ['fan box', 'junction', 'gland', 'tie', 'clamp', 'modular', 'box']:
            if family_keyword in parsed_line.raw_text.lower():
                should_skip_size_filter = True
                # Pre-filter by the likely family
                initial_candidates = [c for c in self.price_master if c.family in FAMILIES_WITHOUT_SIZE_FILTER]
                break
        
        if not should_skip_size_filter and parsed_line.size:
            TOLERANCE_MM = 1.0
            size_candidates = [item for item in initial_candidates if item.size_od_mm and abs(item.size_od_mm - parsed_line.size) < TOLERANCE_MM]
            
            if not size_candidates:
                # Handle "33mm" case by suggesting alternatives
                sorted_by_size = sorted([item for item in self.price_master if item.size_od_mm], key=lambda x: abs(x.size_od_mm - parsed_line.size))
                reason = f"No item found with size {parsed_line.size:.1f}mm. Closest available sizes are shown."
                explain = Explainability(input_text=parsed_line.raw_text, status="NEEDS_REVIEW", reason=reason, candidates=[{"sku": c.sku, "desc": c.item_description} for c in sorted_by_size[:3]])
                return self._create_unmatched_quoteline(parsed_line, line_no, reason, explain)
            candidates = size_candidates
        else:
            candidates = initial_candidates

        # --- Scoring ---
        candidate_choices = {f"{c.item_description} {c.family}": c for c in candidates}
        top_matches = process.extract(search_query, candidate_choices.keys(), scorer=fuzz.WRatio, limit=5)

        if not top_matches:
            return self._create_unmatched_quoteline(parsed_line, line_no, "No items matched after filtering.")

        # Re-score top candidates with bonuses
        scored_candidates = []
        for key, score, _ in top_matches:
            item = candidate_choices[key]
            final_score = score
            
            if parsed_line.material_keywords:
                user_material = parsed_line.material_keywords[0]
                if user_material == item.material or user_material == item.alt_material:
                    final_score += 15
            
            if item.gauge and item.gauge.lower() in parsed_line.raw_text.lower():
                final_score += 30 
            
            numbers_in_text = re.findall(r'\d+\.?\d*', parsed_line.raw_text)
            numbers_in_desc = re.findall(r'\d+\.?\d*', item.item_description)
            if set(numbers_in_text) & set(numbers_in_desc):
                final_score += 20

            scored_candidates.append({'item': item, 'score': final_score})
        
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        best_candidate, best_item, best_score = scored_candidates[0], scored_candidates[0]['item'], scored_candidates[0]['score']

        # --- Decision Logic ---
        is_confident_match = (best_score >= SCORE_THRESHOLD_AUTO_MAP)
        if len(scored_candidates) > 1 and (best_score - scored_candidates[1]['score'] < SCORE_DELTA_AUTO_MAP):
            is_confident_match = False

        status = "MATCHED" if is_confident_match else "NEEDS_REVIEW"
        reason = f"High confidence match (score: {best_score:.1f})" if is_confident_match else f"Top score {best_score:.1f} is below threshold or too close to next best."
        
        explain = Explainability(input_text=parsed_line.raw_text, status=status, reason=reason, score=best_score,
                                 candidates=[{"sku": m['item'].sku, "desc": m['item'].item_description, "score": round(m['score'], 1)} for m in scored_candidates[:3]])

        if is_confident_match:
            explain.matched_sku = best_item.sku
            return self._create_matched_quoteline(parsed_line, line_no, best_item, explain)
        else:
            return self._create_unmatched_quoteline(parsed_line, line_no, reason, explain)

    def _create_matched_quoteline(self, parsed_line: ParsedLine, line_no: int, matched_item: PriceMasterItem, explain: Explainability) -> QuoteLine:
        unit_price = matched_item.rate_pp
        if parsed_line.material_keywords and matched_item.alt_material and parsed_line.material_keywords[0] in matched_item.alt_material:
            unit_price = matched_item.rate_frpp
        final_qty = parsed_line.quantity
        if parsed_line.uom == 'COIL' and matched_item.coil_length_m:
            final_qty = parsed_line.quantity * matched_item.coil_length_m
            explain.assumptions.append(f"Converted {parsed_line.quantity} COILs to {final_qty} M based on coil length of {matched_item.coil_length_m}m.")
        return QuoteLine(line_no=line_no, input_text=parsed_line.raw_text, resolved=True, sku=matched_item.sku, description=matched_item.item_description, qty=final_qty, uom=matched_item.uom, unit_price=unit_price, hsn_code=matched_item.hsn_code, explain=explain)

    def _create_unmatched_quoteline(self, parsed_line: ParsedLine, line_no: int, reason: str, explain: Explainability = None) -> QuoteLine:
        if not explain:
            explain = Explainability(input_text=parsed_line.raw_text, status="NOT_FOUND", reason=reason)
        return QuoteLine(line_no=line_no, input_text=parsed_line.raw_text, resolved=False, qty=parsed_line.quantity, uom=parsed_line.uom, explain=explain)
# --- Singleton instance for use in the main app ---
sku_mapper = SkuMapper(data_loader.get_price_master())