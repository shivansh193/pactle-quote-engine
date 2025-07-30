# Key Decisions & Architecture

## Parsing Strategy
The initial challenge was reliably splitting unstructured RFQ text. After trying several methods based on delimiters, the final, robust strategy implemented was **Iterative Slicing**:
1.  The text is cleaned of headers and separators are standardized.
2.  The algorithm finds all "quantity + unit" pairs, which act as reliable "end-of-item" markers.
3.  The string is sliced up based on the positions of these markers, which correctly isolates each line item.

## SKU Mapping Strategy
The mapping engine uses a multi-stage process to ensure accuracy and prevent incorrect matches:
1.  **Intelligent Filtering:** For items with standard sizes (like pipes), the price list is first hard-filtered by `size_od_mm`. For items without a standard size (like fan boxes), this filter is skipped, and the list is filtered by product family instead.
2.  **Fuzzy Scoring:** The remaining candidates are scored using `rapidfuzz` against a query built from the RFQ line's keywords. The match is performed against a combined string of the candidate's SKU, description, and family for maximum accuracy.
3.  **Heuristic Bonuses:** Scores are boosted for items that also match specific criteria like material (`FRPP`) or gauge (`Medium`), or have matching numbers in their descriptions.
4.  **Decision Thresholds:** A final score must be above **85** to be considered a confident auto-match. It must also be at least **15** points higher than the next-best candidate to avoid ambiguity.