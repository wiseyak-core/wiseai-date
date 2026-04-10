import datetime
from typing import Optional, Union

from library.scanner.lexer import lex
from library.scanner.fsm import FSMScanner
from library.scanner.resolver import resolve
from library.scanner.replacer import build_scan_result
from library.scanner.types import ScanResult

def scan_text(text: str, ref_date: Optional[Union[datetime.date, str]] = None) -> ScanResult:
    if ref_date is None:
        actual_ref = datetime.date.today()
    elif isinstance(ref_date, str):
        actual_ref = datetime.datetime.fromisoformat(ref_date).date()
    else:
        actual_ref = ref_date
        
    tokens = lex(text)
    if not tokens:
        return build_scan_result(text, [])
        
    scanner = FSMScanner()
    date_expressions = scanner.scan(tokens)
    
    resolved_dates = [
        rd for expr in date_expressions
        if (rd := resolve(expr, actual_ref)) is not None
    ]
            
    return build_scan_result(text, resolved_dates)
