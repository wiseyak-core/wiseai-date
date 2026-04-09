import datetime
from typing import List, Optional, Callable, Dict

from library.nepali_date import (
    ad_to_bs, bs_to_ad,
    ad_month_to_bs_range, bs_month_to_ad_range,
    DateRange, _PHRASE_RESOLVERS, _resolve_month_relative, _resolve_year_relative,
    current_bs_year
)
from library.scanner.types import DateExpression, ResolvedDate, ScopeLevel, TokenKind, Token
from library.scanner.lexer import _normalize_numeral


_GRANULARITY = {
    "year": 4,
    "quarter": 3.2,
    "month_explicit": 3.5,
    "month": 3,
    "fortnight": 2.5,
    "week": 2,
    "weekday_explicit": 1.5,
    "day": 1
}


def _build_scope_stack(tokens: List[Token]) -> List[ScopeLevel]:
    """Generates the hierarchical scope stack from tokens using a reducer pattern."""
    stack = []
    current_state = {"modifier": None, "ordinal": None, "number": None}

    def _flush_scope(unit_val: str):
        modifier, ordinal, number = current_state["modifier"], current_state["ordinal"], current_state["number"]
        # Default modifier if entirely unconstrained for the root scope
        if not any(current_state.values()) and not stack and token.kind == TokenKind.TEMPORAL_UNIT:
            modifier = "this"
        stack.append(ScopeLevel(unit=unit_val, ordinal=ordinal, modifier=modifier))
        current_state.update(modifier=None, ordinal=None, number=None)

    def _safe_modifier_update(current_mod: str | None, new_mod: str) -> str:
        # Don't let filler articles mapped as 'this' overwrite a structural boundary
        if new_mod == "this" and current_mod in {"middle_of", "first_of", "end_of", "last_of"}:
            return current_mod
        return new_mod

    # State update map
    _STATE_UPDATES = {
        TokenKind.TEMPORAL_MODIFIER: lambda t: current_state.update(modifier=_safe_modifier_update(current_state.get("modifier"), t.value)),
        TokenKind.ORDINAL: lambda t: current_state.update(ordinal=t.value),
        TokenKind.NUMBER: lambda t: current_state.update(number=t.value),
        TokenKind.TEMPORAL_UNIT: lambda t: _flush_scope(t.value),
        TokenKind.MONTH_NAME: lambda t: _flush_scope("month_explicit"),
        TokenKind.WEEKDAY_NAME: lambda t: _flush_scope("weekday_explicit"),
        TokenKind.TARIKH: lambda t: _flush_scope("day")
    }

    for token in tokens:
        if token.kind in _STATE_UPDATES:
            _STATE_UPDATES[token.kind](token)

    # If there's an unflushed state at the end (e.g. modifier without unit), default to day
    if any(current_state.values()):
        _flush_scope("day")

    return stack

# ── Resolvers for Specific Patterns ── #

def _resolve_iso_date(expr: DateExpression, ref_date: datetime.date, token: Token, is_bs: bool) -> ResolvedDate:
    norm_val = _normalize_numeral(token.norm)
    y, m, d = (int(x) for x in norm_val.split('-'))
    start_str = f"{y:04d}-{m:02d}-{d:02d}"
    return ResolvedDate(
        expression=expr, calendar=expr.calendar_signal, type="day",
        year=y, month=m, day=d, start=start_str, end=start_str, iso_replacement=token.text
    )

def _resolve_relative_adverb(expr: DateExpression, ref_date: datetime.date, token: Token, is_bs: bool) -> ResolvedDate:
    if token.value == "day_before_yesterday":
        dr = DateRange(ref_date - datetime.timedelta(days=2), ref_date - datetime.timedelta(days=2))
    elif token.value == "day_after_tomorrow":
        dr = DateRange(ref_date + datetime.timedelta(days=2), ref_date + datetime.timedelta(days=2))
    else:
        dr = _PHRASE_RESOLVERS[token.value](ref_date, is_bs)
    return _build_resolved(expr, dr, is_bs, "day")

def _resolve_directional(expr: DateExpression, ref_date: datetime.date, tokens: List[Token], is_bs: bool) -> Optional[ResolvedDate]:
    num_t = next((t for t in tokens if t.kind == TokenKind.NUMBER), None)
    unit_t = next((t for t in tokens if t.kind == TokenKind.TEMPORAL_UNIT), None)
    dir_t = next((t for t in tokens if t.kind == TokenKind.DIRECTION), None)
    
    if not (unit_t and dir_t): return None
    
    val = num_t.value if num_t else 1
    unit, direction = unit_t.value, dir_t.value
    def get_exact_month(r: datetime.date, n: int, dr: int, bs: bool):
        if bs:
            from library.nepali_date import NepaliDateTime
            target = NepaliDateTime.from_ad(r.year, r.month, r.day).plusMonths(n * dr).toLocalDate()
        else:
            m = r.month + (n * dr)
            y = r.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            day = r.day
            while True:
                try:
                    target = datetime.date(y, m, day)
                    break
                except ValueError:
                    day -= 1
        return DateRange(target, target)

    def get_exact_year(r: datetime.date, n: int, dr: int, bs: bool):
        if bs:
            from library.nepali_date import NepaliDateTime
            target = NepaliDateTime.from_ad(r.year, r.month, r.day).plusYears(n * dr).toLocalDate()
        else:
            try:
                target = r.replace(year=r.year + (n * dr))
            except ValueError:
                target = r.replace(year=r.year + (n * dr), day=28)
        return DateRange(target, target)

    _DIR_EVALUATORS = {
        "day": lambda r, n, dr: DateRange(r + datetime.timedelta(days=n * dr), r + datetime.timedelta(days=n * dr)),
        "week": lambda r, n, dr: DateRange(r + datetime.timedelta(days=n * 7 * dr), r + datetime.timedelta(days=n * 7 * dr)),
        "fortnight": lambda r, n, dr: DateRange(r + datetime.timedelta(days=n * 14 * dr), r + datetime.timedelta(days=n * 14 * dr)),
        "month": lambda r, n, dr: get_exact_month(r, n, dr, is_bs),
        "third": lambda r, n, dr: get_exact_month(r, n * 4, dr, is_bs),
        "quarter": lambda r, n, dr: get_exact_month(r, n * 3, dr, is_bs),
        "half": lambda r, n, dr: get_exact_month(r, n * 6, dr, is_bs),
        "year": lambda r, n, dr: get_exact_year(r, n, dr, is_bs),
    }
    
    if unit in _DIR_EVALUATORS:
        dr = _DIR_EVALUATORS[unit](ref_date, val, direction)
        return _build_resolved(expr, dr, is_bs, unit) 
    return None

# ── Scope Stack Resolution Handlers ── #

def _apply_boundary(dr: DateRange, modifier: Optional[str]) -> Optional[DateRange]:
    match modifier:
        case "first_of": return DateRange(dr.start_ad, dr.start_ad)
        case "end_of": return DateRange(dr.end_ad, dr.end_ad)
        case "middle_of":
            mid_ad = dr.start_ad + datetime.timedelta(days=(dr.end_ad - dr.start_ad).days // 2)
            return DateRange(mid_ad, mid_ad)
        case _: return None

def _eval_root_scope(scope: ScopeLevel, ref_date: datetime.date, is_bs: bool, tokens: List[Token]) -> DateRange:
    _offset_map = {"last": -1, "next": 1, "this": 0}
    offset = _offset_map.get(scope.modifier, 0)

    def get_year():
        if scope.modifier == "middle_of":
            # Middle of year is Kartik (7) or July (7)
            return bs_month_to_ad_range(7, current_bs_year()) if is_bs else ad_month_to_bs_range(7, datetime.date.today().year)
        yr = _resolve_year_relative(ref_date, is_bs, offset)
        return _apply_boundary(yr, scope.modifier) or yr

    def get_month():
        dr = _resolve_month_relative(ref_date, is_bs, offset)
        return _apply_boundary(dr, scope.modifier) or dr

    def get_week():
        mod = scope.modifier if scope.modifier in ["last", "next", "this"] else "this"
        wk = _PHRASE_RESOLVERS[f"{mod}_week"](ref_date, is_bs)
        return _apply_boundary(wk, scope.modifier) or wk

    def get_month_explicit():
        m_token = next((t for t in tokens if t.kind == TokenKind.MONTH_NAME), None)
        if not m_token: return None
        if is_bs:
            from library.nepali_date import ad_to_bs
            yr = ad_to_bs(ref_date)[0]
            dr = bs_month_to_ad_range(m_token.value, yr)
        else:
            dr = ad_month_to_bs_range(m_token.value, ref_date.year)
            
        return _apply_boundary(dr, scope.modifier) or dr

    def get_weekday_explicit():
        w_token = next((t for t in tokens if t.kind == TokenKind.WEEKDAY_NAME), None)
        if not w_token: return None
        target_wd = w_token.value
        mod = scope.modifier if scope.modifier in ["last", "next", "this"] else "this"
        dr_week = _PHRASE_RESOLVERS[f"{mod}_week"](ref_date, is_bs)
        return _get_nth_day(dr_week, target_wd + 1)
        
    _ROOT_HANDLERS = {
        "year": get_year,
        "month": get_month,
        "week": get_week,
        "month_explicit": get_month_explicit,
        "weekday_explicit": get_weekday_explicit,
        "day": lambda: _PHRASE_RESOLVERS["today"](ref_date, is_bs)
    }
    return _ROOT_HANDLERS.get(scope.unit, lambda: None)()

def _eval_narrowing_scope(scope: ScopeLevel, parent_dr: DateRange, is_bs: bool) -> DateRange:
    modifier = "end_of" if scope.modifier == "last" else scope.modifier

    def narrow_day():
        match modifier:
            case "end_of": return DateRange(parent_dr.end_ad, parent_dr.end_ad)
            case "first_of": return DateRange(parent_dr.start_ad, parent_dr.start_ad)
            case "middle_of":
                mid_ad = parent_dr.start_ad + datetime.timedelta(days=(parent_dr.end_ad - parent_dr.start_ad).days // 2)
                return DateRange(mid_ad, mid_ad)
            case _: return _get_nth_day(parent_dr, scope.ordinal) if scope.ordinal else parent_dr

    def narrow_month():
        match modifier:
            case "middle_of": m_num = 7
            case "end_of": m_num = 12
            case "first_of": m_num = 1
            case _: m_num = scope.ordinal if scope.ordinal else parent_dr.start_bs[1]
        return bs_month_to_ad_range(m_num, parent_dr.start_bs[0]) if is_bs else ad_month_to_bs_range(m_num, parent_dr.start_ad.year)

    def narrow_generic(chunks: int):
        dur = (parent_dr.end_ad - parent_dr.start_ad).days + 1
        chunk_days = dur / chunks
        idx = (scope.ordinal or 1) - 1
        match modifier:
            case "end_of": idx = chunks - 1
            case "first_of": idx = 0
            
        if idx >= chunks: return parent_dr
        st = parent_dr.start_ad + datetime.timedelta(days=int(idx * chunk_days))
        en = parent_dr.start_ad + datetime.timedelta(days=int((idx + 1) * chunk_days) - 1)
        if idx == chunks - 1: en = parent_dr.end_ad
        return DateRange(st, en)
        
    def narrow_duration(days: int):
        if modifier == "end_of":
            st = parent_dr.end_ad - datetime.timedelta(days=days - 1)
            return DateRange(st, parent_dr.end_ad)
        idx = (scope.ordinal or 1) - 1
        st = parent_dr.start_ad + datetime.timedelta(days=idx * days)
        en = min(parent_dr.end_ad, st + datetime.timedelta(days=days - 1))
        return DateRange(st, en) if st <= parent_dr.end_ad else parent_dr

    _NARROW_HANDLERS = {
        "month": narrow_month,
        "day": narrow_day,
        "week": lambda: narrow_duration(7),
        "fortnight": lambda: narrow_duration(14),
        "half": lambda: narrow_generic(2),
        "third": lambda: narrow_generic(3),
        "quarter": lambda: narrow_generic(4),
    }
    return _NARROW_HANDLERS.get(scope.unit, lambda: parent_dr)()

def _get_nth_day(dr: DateRange, n: int) -> DateRange:
    target_ad = dr.start_ad + datetime.timedelta(days=(n or 1) - 1)
    return DateRange(target_ad, target_ad) if target_ad <= dr.end_ad else dr

# ── Main Resolver Entrypoint ── #

def _resolve_explicit_range(expr: DateExpression, ref_date: datetime.date, is_bs: bool) -> Optional[ResolvedDate]:
    from library.scanner.vocabulary import _RANGE_BRIDGES
    
    # Look for a bridge token
    bridge_idx = next(
        (i for i, t in enumerate(expr.tokens) if t.norm in _RANGE_BRIDGES or t.text in _RANGE_BRIDGES),
        -1
    )
    
    # Validation filters using pattern matching logic natively
    match bridge_idx:
        case -1 | 0: return None
        case last_idx if last_idx == len(expr.tokens) - 1: return None
        case _: pass
    
    left_expr = DateExpression(
        tokens=expr.tokens[:bridge_idx], 
        calendar_signal=expr.calendar_signal,
        span=expr.span,
        trailing_postposition=expr.trailing_postposition,
        trailing_post_span=expr.trailing_post_span,
        scope_stack=expr.scope_stack
    )
    right_expr = DateExpression(
        tokens=expr.tokens[bridge_idx+1:], 
        calendar_signal=expr.calendar_signal,
        span=expr.span,
        trailing_postposition=expr.trailing_postposition,
        trailing_post_span=expr.trailing_post_span,
        scope_stack=expr.scope_stack
    )
    
    left_resolved, right_resolved = resolve(left_expr, ref_date), resolve(right_expr, ref_date)
    minmax = lambda d1, d2: (d1, d2) if d1 <= d2 else (d2, d1)
    
    match (left_resolved, right_resolved, is_bs):
        case (None, _, _) | (_, None, _):
            return None
        case (left, right, True):
            from library.nepali_date import bs_to_ad
            st_ad, en_ad = minmax(
                bs_to_ad(*[int(x) for x in left.start.split('-')]),
                bs_to_ad(*[int(x) for x in right.end.split('-')])
            )
            return _build_resolved(expr, DateRange(st_ad, en_ad), True, "postposition_range")
        case (left, right, False):
            st_ad, en_ad = minmax(
                datetime.date(*[int(x) for x in left.start.split('-')]),
                datetime.date(*[int(x) for x in right.end.split('-')])
            )
            return _build_resolved(expr, DateRange(st_ad, en_ad), False, "postposition_range")
            
    return None


def resolve(expr: DateExpression, ref_date: datetime.date) -> Optional[ResolvedDate]:
    is_bs = expr.calendar_signal == "BS"
    
    if bridged_range := _resolve_explicit_range(expr, ref_date, is_bs):
        return bridged_range
        
    # Pre-processors for distinct singular patterns
    _PRE_PROCESSORS = [
        (lambda t: t.kind == TokenKind.NUMERIC_DATE, _resolve_iso_date),
        (lambda t: t.kind == TokenKind.RELATIVE_ADVERB, _resolve_relative_adverb)
    ]
    
    for cond, handler in _PRE_PROCESSORS:
        trigger_token = next((t for t in expr.tokens if cond(t)), None)
        if trigger_token:
            return handler(expr, ref_date, trigger_token, is_bs)
            
    if directional := _resolve_directional(expr, ref_date, expr.tokens, is_bs):
        return directional

    # Hierarchical Resolution
    stack = _build_scope_stack(expr.tokens)
    if not stack: return None
    
    # Sort stack so that higher-level units act as parents for lower-level units
    # e.g. "first day of year" -> [year, day(ord=1)]
    sorted_stack = sorted(stack, key=lambda s: _GRANULARITY.get(s.unit, 0), reverse=True)
    
    current_dr = _eval_root_scope(sorted_stack[0], ref_date, is_bs, expr.tokens)
    if not current_dr: return None
    
    for scope in sorted_stack[1:]:
        current_dr = _eval_narrowing_scope(scope, current_dr, is_bs)
        
    return _build_resolved(expr, current_dr, is_bs, sorted_stack[-1].unit)

# ── Result Builder ── #

def _build_resolved(expr: DateExpression, dr: DateRange, is_bs: bool, unit: str) -> ResolvedDate:
    from library.scanner.vocabulary import _DEVANAGARI_DIGIT_MAP
    
    # Extract structural dates
    (y, m, d), (ye, me, de) = (dr.start_bs, dr.end_bs) if is_bs else ((dr.start_ad.year, dr.start_ad.month, dr.start_ad.day), (dr.end_ad.year, dr.end_ad.month, dr.end_ad.day))
    
    # Type mapping
    r_type = "month" if unit == "month_explicit" else ("day" if unit == "weekday_explicit" else unit)
    
    # Infer result type from range duration for root-level modifier overrides
    days_span = (dr.end_ad - dr.start_ad).days + 1
    if days_span == 1 and r_type not in ("range",):
        r_type = "day"
    elif r_type == "year" and 27 <= days_span <= 32: 
        r_type = "month"
    
    if days_span > 1 and r_type == "day": r_type = "range"
    if days_span > 1 and unit == "postposition_range": r_type = "range"
    
    # Format ISO strings
    iso_formats = {
        "month": lambda: f"{y:04d}-{m:02d}",
        "year": lambda: f"{y:04d}",
        "range": lambda: f"{y:04d}-{m:02d}-{d:02d}~{ye:04d}-{me:02d}-{de:02d}",
        "default": lambda: f"{y:04d}-{m:02d}-{d:02d}" if dr.start_ad == dr.end_ad else \
                           (f"{y:04d}-{m:02d}-{d:02d}~{de:02d}" if (m, y) == (me, ye) else f"{y:04d}-{m:02d}-{d:02d}~{ye:04d}-{me:02d}-{de:02d}")
    }
    iso_repl = iso_formats.get(r_type, iso_formats["default"])()
    
    # Devanagari mirroring
    if is_bs and any("\u0900" <= c <= "\u097F" for t in expr.tokens for c in t.text):
        iso_repl = iso_repl.translate(_DEVANAGARI_DIGIT_MAP)

    return ResolvedDate(
        expression=expr, calendar="BS" if is_bs else "AD", type=r_type,
        year=y, month=m, day=d,
        start=f"{y:04d}-{m:02d}-{d:02d}", end=f"{ye:04d}-{me:02d}-{de:02d}",
        iso_replacement=iso_repl
    )
