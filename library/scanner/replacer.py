import json
from typing import List
from library.scanner.types import ResolvedDate, ScanResult

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
            "text": original_text[start:end].strip(),
            "normalized": {
                "type": extraction.type,
                "calendar": extraction.calendar,
                "year": extraction.year,
                "month": extraction.month,
            }
        }
        if extraction.day is not None:
             json_dict["normalized"]["day"] = extraction.day
             
        json_dict["normalized"]["start"] = extraction.start
        json_dict["normalized"]["end"] = extraction.end
        
        json_extractions.insert(0, json_dict)
        
    normalized_text = "".join(normalized_chars)
    
    return ScanResult(
        original_text=original_text,
        normalized_text=normalized_text,
        extractions=json_extractions
    )
