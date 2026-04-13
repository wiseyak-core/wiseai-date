import json
from typing import List
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

def _build_extraction_json(
    extraction: ResolvedDate, original_text: str
) -> dict:
    """Builds a JSON dictionary for a single resolved date extraction."""
    start, end = extraction.expression.span
    json_dict = {
        _FIELD_TEXT: original_text[start:end].strip(),
        _FIELD_NORMALIZED: {
            _FIELD_TYPE: extraction.type,
            _FIELD_CALENDAR: extraction.calendar,
            _FIELD_YEAR: extraction.year,
            _FIELD_MONTH: extraction.month,
        }
    }
    if extraction.day is not None:
        json_dict[_FIELD_NORMALIZED][_FIELD_DAY] = extraction.day

    if extraction.start == extraction.end:
        json_dict[_FIELD_NORMALIZED][_FIELD_DATE] = extraction.start
    else:
        json_dict[_FIELD_NORMALIZED][_FIELD_START] = extraction.start
        json_dict[_FIELD_NORMALIZED][_FIELD_END] = extraction.end

    return json_dict

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
