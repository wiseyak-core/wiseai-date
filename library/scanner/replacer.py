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

def build_scan_result(original_text: str, extractions: List[ResolvedDate]) -> ScanResult:
    """Takes resolved extractions and performs span-based replacement on original text."""
    
    extractions_sorted = sorted(extractions, key=lambda r: r.expression.span[0], reverse=True)
    
    normalized_chars = list(original_text)
    json_extractions = []
    
    for extraction in extractions_sorted:
        expr = extraction.expression
        start, end = expr.span
        
        iso_str = extraction.iso_replacement
        normalized_chars[start:end] = list(iso_str)
        
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
             
        json_dict[_FIELD_NORMALIZED][_FIELD_START] = extraction.start
        json_dict[_FIELD_NORMALIZED][_FIELD_END] = extraction.end
        
        json_extractions.insert(0, json_dict)
        
    normalized_text = "".join(normalized_chars)
    
    return ScanResult(
        original_text=original_text,
        normalized_text=normalized_text,
        extractions=json_extractions
    )
