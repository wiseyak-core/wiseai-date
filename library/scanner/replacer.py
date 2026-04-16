import json
from typing import List
from dataclasses import asdict
from library.scanner.types import ResolvedDate, ScanResult

# JSON field name constants 
_FIELD_TEXT = "text"
_FIELD_NORMALIZED = "normalized"
_FIELD_TYPE = "type"
_FIELD_CALENDAR = "calendar"
_FIELD_YEAR = "year"
_FIELD_MONTH = "month"
_FIELD_DAY = "day"
_FIELD_START = "start"
_FIELD_END = "end"
_FIELD_DATE = "date"

def _build_extraction_json(extraction: ResolvedDate, original_text: str) -> dict:
    """Builds a JSON dictionary for a single resolved date extraction generically."""
    start, end = extraction.expression.span
    
    data = asdict(extraction)
    
    for key in ["expression", "iso_replacement"]:
        data.pop(key, None)
    
    start_val, end_val = data.pop("start"), data.pop("end")

    if start_val == end_val:
        data["date"] = start_val
    else:
        data["start"], data["end"] = start_val, end_val
        
    return {
        "text": original_text[start:end].strip(),
        "normalized": {k: v for k, v in data.items() if v is not None}
    }

def build_scan_result(original_text: str, extractions: List[ResolvedDate]) -> ScanResult:
    """Takes resolved extractions and performs span-based replacement on original text."""
    
    extractions_sorted = sorted(extractions, key=lambda r: r.expression.span[0], reverse=True)
    
    normalized_chars = list(original_text)
    
    for extraction in extractions_sorted:
        expr = extraction.expression
        start, end = expr.span
        normalized_chars[start:end] = list(extraction.iso_replacement)

    json_extractions = [
        _build_extraction_json(extraction, original_text)
        for extraction in reversed(extractions_sorted)
    ]
        
    normalized_text = "".join(normalized_chars)
    
    return ScanResult(
        original_text=original_text,
        normalized_text=normalized_text,
        extractions=json_extractions
    )
