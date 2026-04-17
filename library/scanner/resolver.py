import datetime
from typing import List, Optional

from library.nepali_date import (
    ad_to_bs, bs_to_ad,
    ad_month_to_bs_range, bs_month_to_ad_range,
    DateRange, _PHRASE_RESOLVERS, _resolve_month_relative, _resolve_year_relative,
    current_bs_year, NepaliDateTime
)
from library.scanner.types import (
    DateExpression, 
    ResolvedDate, 
    ScopeLevel, 
    TokenKind, 
    Token
)
from library.scanner.lexer import _normalize_numeral
from library.scanner.vocabulary import _RANGE_BRIDGES, _DEVANAGARI_DIGIT_MAP

# ── Unit Constants ──
_UNIT_YEAR = "year"
_UNIT_QUARTER = "quarter"
_UNIT_MONTH_EXPLICIT = "month_explicit"
_UNIT_MONTH = "month"
_UNIT_FORTNIGHT = "fortnight"
_UNIT_WEEK = "week"
_UNIT_WEEKDAY_EXPLICIT = "weekday_explicit"
_UNIT_DAY = "day"
_UNIT_HALF = "half"
_UNIT_THIRD = "third"

# ── Result Type Constants ──
_TYPE_DAY = "day"
_TYPE_MONTH = "month"
_TYPE_YEAR = "year"
_TYPE_WEEK = "week"
_TYPE_RANGE = "range"
_TYPE_POSTPOSITION_RANGE = "postposition_range"

# ── Modifier Constants ──
_MOD_THIS = "this"
_MOD_LAST = "last"
_MOD_NEXT = "next"
_MOD_MIDDLE_OF = "middle_of"
_MOD_FIRST_OF = "first_of"
_MOD_END_OF = "end_of"
_MOD_LAST_OF = "last_of"

# Set of structural boundary modifiers that should not be overwritten by filler articles
_BOUNDARY_MODIFIERS = frozenset({
    _MOD_MIDDLE_OF, _MOD_FIRST_OF,
    _MOD_END_OF, _MOD_LAST_OF,
})

# Valid modifiers for week resolution
_WEEK_MODIFIERS = frozenset({
    _MOD_LAST, _MOD_NEXT, _MOD_THIS,
})

_GRANULARITY = {
    _UNIT_DAY: 1,
    _UNIT_WEEKDAY_EXPLICIT: 2,
    _UNIT_WEEK: 3,
    _UNIT_FORTNIGHT: 4,
    _UNIT_MONTH: 5,
    _UNIT_MONTH_EXPLICIT: 6,
    _UNIT_QUARTER: 7,
    _UNIT_YEAR: 8,
}

# ── Narrowing Month Positions ──
# Maps boundary modifiers to the month number they resolve to inside a parent year scope.
_NARROW_MONTH_FIRST = 1
_NARROW_MONTH_MIDDLE = 7
_NARROW_MONTH_LAST = 12

def _build_scope_stack(tokens: List[Token]) -> List[ScopeLevel]:
    """Generates the hierarchical scope stack from tokens using a reducer pattern."""
    stack = []
    current_state = {"modifier": None, "ordinal": None, "number": None}

    def _flush_scope(unit_val: str):
        modifier = current_state["modifier"]
        # Prefer ordinal if set, otherwise use current number (e.g. for Day in "Jan 12")
        ordinal = current_state["ordinal"] if current_state["ordinal"] is not None else current_state["number"]
        number = current_state["number"]
        # Default modifier if entirely unconstrained for the root scope
        if not any(current_state.values()) and not stack and token.kind == TokenKind.TEMPORAL_UNIT:
            modifier = _MOD_THIS
        stack.append(ScopeLevel(unit=unit_val, ordinal=ordinal, modifier=modifier))
        current_state.update(modifier=None, ordinal=None, number=None)

    def _safe_modifier_update(current_mod: str | None, new_mod: str) -> str:
        # Don't let filler articles mapped as 'this' overwrite a structural boundary
        if new_mod == _MOD_THIS and current_mod in _BOUNDARY_MODIFIERS:
            return current_mod
        return new_mod

    # State update map
    _STATE_UPDATES = {
        TokenKind.TEMPORAL_MODIFIER: lambda t: current_state.update(
                modifier=_safe_modifier_update(
                    current_state.get("modifier"), t.value
                )
        ),
        TokenKind.ORDINAL: lambda t: current_state.update(ordinal=t.value),
        # Only capture numbers <= 32 as potential days (ignores years like 2024)
        TokenKind.NUMBER: lambda t: current_state.update(number=t.value) if (isinstance(t.value, int) and t.value <= 32) else None,
        TokenKind.TEMPORAL_UNIT: lambda t: _flush_scope(t.value),
        # Flush a DAY scope if a number is pending before processing the month
        TokenKind.MONTH_NAME: lambda t: (
            _flush_scope(_UNIT_DAY) if (current_state["number"] is not None or current_state["ordinal"] is not None) else None,
            _flush_scope(_UNIT_MONTH_EXPLICIT)
        )[-1],
        TokenKind.WEEKDAY_NAME: lambda t: _flush_scope(_UNIT_WEEKDAY_EXPLICIT),
        TokenKind.TARIKH: lambda t: _flush_scope(_UNIT_DAY)
    }

    for token in tokens:
        if token.kind in _STATE_UPDATES:
            _STATE_UPDATES[token.kind](token)

    # If there's an unflushed state at the end (e.g. modifier without unit), default to day
    if any(current_state.values()):
        _flush_scope(_UNIT_DAY)

    return stack

# ── Resolvers for Specific Patterns ── #

def _resolve_iso_date(
    expr: DateExpression, 
    ref_date: datetime.date, 
    token: Token, 
    is_bs: bool
) -> ResolvedDate:
    norm_val = _normalize_numeral(token.norm)
    y, m, d = (int(x) for x in norm_val.split('-'))
    ad_date = bs_to_ad(y, m, d) if is_bs else datetime.date(y, m, d)
    return _build_resolved(expr, DateRange(ad_date, ad_date), is_bs, _TYPE_DAY)

def _resolve_relative_adverb(
    expr: DateExpression, 
    ref_date: datetime.date, 
    token: Token, 
    is_bs: bool
) -> ResolvedDate:
    if token.value == "day_before_yesterday":
        dr = DateRange(ref_date - datetime.timedelta(days=2), ref_date - datetime.timedelta(days=2))
    elif token.value == "day_after_tomorrow":
        dr = DateRange(ref_date + datetime.timedelta(days=2), ref_date + datetime.timedelta(days=2))
    else:
        dr = _PHRASE_RESOLVERS[token.value](ref_date, is_bs)
    return _build_resolved(expr, dr, is_bs, _TYPE_DAY)

def _resolve_directional(
    expr: DateExpression, 
    ref_date: datetime.date, 
    tokens: List[Token], 
    is_bs: bool
) -> Optional[ResolvedDate]:
    num_t = next((t for t in tokens if t.kind == TokenKind.NUMBER), None)
    unit_t = next((t for t in tokens if t.kind == TokenKind.TEMPORAL_UNIT), None)
    dir_t = next((t for t in tokens if t.kind == TokenKind.DIRECTION), None)
    
    if not (unit_t and dir_t): return None
    
    val = num_t.value if num_t else 1
    unit, direction = unit_t.value, dir_t.value
    def get_exact_month(ref: datetime.date, count: int, sign: int, bs: bool):
        if bs:
            target = (
                NepaliDateTime.from_ad(ref.year, ref.month, ref.day)
                .plus_months(count * sign).to_local_date()
            )
        else:
            raw_month = ref.month + (count * sign)
            year = ref.year + (raw_month - 1) // 12
            month = (raw_month - 1) % 12 + 1
            day = ref.day
            # Clamp day to valid range for target month
            max_attempts = ref.day
            for attempt in range(max_attempts):
                try:
                    target = datetime.date(
                        year, month, day
                    )
                    break
                except ValueError:
                    day -= 1
            else:
                target = datetime.date(
                    year, month, 1
                )
        return DateRange(target, target)

    def get_exact_year(ref: datetime.date, count: int, sign: int, bs: bool):
        if bs:
            target = (
                NepaliDateTime.from_ad(ref.year, ref.month, ref.day)
                .plus_years(count * sign).to_local_date()
            )
        else:
            try:
                target = ref.replace(year=ref.year + (count * sign))
            except ValueError:
                target = ref.replace(year=ref.year + (count * sign), day=28)
        return DateRange(target, target)

    _DIR_EVALUATORS = {
        _UNIT_DAY: lambda r, n, dr: DateRange(
            r + datetime.timedelta(days=n * dr), 
            r + datetime.timedelta(days=n * dr)
        ),
        _UNIT_WEEK: lambda r, n, dr: DateRange(
            r + datetime.timedelta(days=n * 7 * dr), 
            r + datetime.timedelta(days=n * 7 * dr)
        ),
        _UNIT_FORTNIGHT: lambda r, n, dr: DateRange(
            r + datetime.timedelta(days=n * 14 * dr), 
            r + datetime.timedelta(days=n * 14 * dr)
        ),
        _UNIT_MONTH: lambda r, n, dr: get_exact_month(r, n, dr, is_bs),
        _UNIT_THIRD: lambda r, n, dr: get_exact_month(r, n * 4, dr, is_bs),
        _UNIT_QUARTER: lambda r, n, dr: get_exact_month(r, n * 3, dr, is_bs),
        _UNIT_HALF: lambda r, n, dr: get_exact_month(r, n * 6, dr, is_bs),
        _UNIT_YEAR: lambda r, n, dr: get_exact_year(r, n, dr, is_bs),
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
    _offset_map = {_MOD_LAST: -1, _MOD_NEXT: 1, _MOD_THIS: 0}
    offset = _offset_map.get(scope.modifier, 0)

    def get_year():
        if scope.modifier == _MOD_MIDDLE_OF:
            # Middle of year is Kartik (7) or July (7)
            if is_bs:
                return bs_month_to_ad_range(
                    _NARROW_MONTH_MIDDLE, ad_to_bs(ref_date)[0]
                )
            return ad_month_to_bs_range(
                _NARROW_MONTH_MIDDLE, ref_date.year
            )
        yr = _resolve_year_relative(ref_date, is_bs, offset)
        return _apply_boundary(yr, scope.modifier) or yr

    def get_month():
        dr = _resolve_month_relative(ref_date, is_bs, offset)
        return _apply_boundary(dr, scope.modifier) or dr

    def get_week():
        mod = scope.modifier if scope.modifier in _WEEK_MODIFIERS else _MOD_THIS
        wk = _PHRASE_RESOLVERS[f"{mod}_week"](ref_date, is_bs)
        return _apply_boundary(wk, scope.modifier) or wk

    def get_month_explicit():
        m_token = next((t for t in tokens if t.kind == TokenKind.MONTH_NAME), None)
        if not m_token: return None
        
        # Look for a 4-digit year token
        year_token = next((t for t in tokens if t.kind == TokenKind.NUMBER and isinstance(t.value, int) and 1900 <= t.value <= 2200), None)
        year_val_bs = year_token.value if year_token else None
        year_val_ad = year_token.value if year_token else ref_date.year
        
        if is_bs:
            yr = year_val_bs if year_val_bs else ad_to_bs(ref_date)[0]
            dr = bs_month_to_ad_range(m_token.value, yr)
        else:
            dr = ad_month_to_bs_range(m_token.value, year_val_ad)
            
        return _apply_boundary(dr, scope.modifier) or dr

    def get_weekday_explicit():
        w_token = next((t for t in tokens if t.kind == TokenKind.WEEKDAY_NAME), None)
        if not w_token: return None
        target_wd = w_token.value
        mod = scope.modifier if scope.modifier in _WEEK_MODIFIERS else _MOD_THIS
        dr_week = _PHRASE_RESOLVERS[f"{mod}_week"](ref_date, is_bs)
        return _get_nth_day(dr_week, target_wd + 1)
        
    _ROOT_HANDLERS = {
        _UNIT_YEAR: get_year,
        _UNIT_MONTH: get_month,
        _UNIT_WEEK: get_week,
        _UNIT_MONTH_EXPLICIT: get_month_explicit,
        _UNIT_WEEKDAY_EXPLICIT: get_weekday_explicit,
        _UNIT_DAY: lambda: _PHRASE_RESOLVERS["today"](ref_date, is_bs)
    }
    return _ROOT_HANDLERS.get(scope.unit, lambda: None)()

def _eval_narrowing_scope(scope: ScopeLevel, parent_dr: DateRange, is_bs: bool) -> DateRange:
    modifier = _MOD_END_OF if scope.modifier == _MOD_LAST else scope.modifier

    def narrow_day():
        match modifier:
            case "end_of": return DateRange(parent_dr.end_ad, parent_dr.end_ad)
            case "first_of": return DateRange(parent_dr.start_ad, parent_dr.start_ad)
            case "middle_of":
                mid_ad = parent_dr.start_ad + datetime.timedelta(
                    days=(parent_dr.end_ad - parent_dr.start_ad).days // 2
                )
                return DateRange(mid_ad, mid_ad)
            case _: return _get_nth_day(parent_dr, scope.ordinal) if scope.ordinal else parent_dr

    def narrow_month():
        match modifier:
            case "middle_of": m_num = _NARROW_MONTH_MIDDLE
            case "end_of": m_num = _NARROW_MONTH_LAST
            case "first_of": m_num = _NARROW_MONTH_FIRST
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
        _UNIT_MONTH: narrow_month,
        _UNIT_DAY: narrow_day,
        _UNIT_WEEK: lambda: narrow_duration(7),
        _UNIT_FORTNIGHT: lambda: narrow_duration(14),
        _UNIT_HALF: lambda: narrow_generic(2),
        _UNIT_THIRD: lambda: narrow_generic(3),
        _UNIT_QUARTER: lambda: narrow_generic(4),
    }
    return _NARROW_HANDLERS.get(scope.unit, lambda: parent_dr)()

def _get_nth_day(dr: DateRange, n: int) -> DateRange:
    target_ad = dr.start_ad + datetime.timedelta(days=(n or 1) - 1)
    return DateRange(target_ad, target_ad) if target_ad <= dr.end_ad else dr

# ── Main Resolver Entrypoint ── #

def _resolve_explicit_range(expr: DateExpression, ref_date: datetime.date, is_bs: bool) -> Optional[ResolvedDate]:
    
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
            st_ad, en_ad = minmax(
                bs_to_ad(*[int(x) for x in left.start.split('-')]),
                bs_to_ad(*[int(x) for x in right.end.split('-')])
            )
            return _build_resolved(expr, DateRange(st_ad, en_ad), True, _TYPE_POSTPOSITION_RANGE)
        case (left, right, False):
            st_ad, en_ad = minmax(
                datetime.date(*[int(x) for x in left.start.split('-')]),
                datetime.date(*[int(x) for x in right.end.split('-')])
            )
            return _build_resolved(expr, DateRange(st_ad, en_ad), False, _TYPE_POSTPOSITION_RANGE)
            
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
    
    # Extract structural dates
    if is_bs:
        (year, month, day) = dr.start_bs
        (year_end, month_end, day_end) = dr.end_bs
    else:
        year = dr.start_ad.year
        month = dr.start_ad.month
        day = dr.start_ad.day
        year_end = dr.end_ad.year
        month_end = dr.end_ad.month
        day_end = dr.end_ad.day

    # Type mapping
    result_type = _TYPE_MONTH if unit == _UNIT_MONTH_EXPLICIT else (_TYPE_DAY if unit == _UNIT_WEEKDAY_EXPLICIT else unit)
    
    # Infer result type from range duration for root-level modifier overrides
    days_span = (dr.end_ad - dr.start_ad).days + 1
    if days_span == 1 and result_type != _TYPE_RANGE:
        result_type = _TYPE_DAY
    elif result_type == _TYPE_YEAR and 27 <= days_span <= 32: 
        result_type = _TYPE_MONTH
    
    if days_span > 1 and result_type == _TYPE_DAY: result_type = _TYPE_RANGE
    if days_span > 1 and unit == _TYPE_POSTPOSITION_RANGE: result_type = _TYPE_RANGE
    
    # Format ISO strings
    iso_formats = {
        _TYPE_MONTH: lambda: f"{year:04d}-{month:02d}",
        _TYPE_YEAR: lambda: f"{year:04d}",
        _TYPE_RANGE: lambda: f"{year:04d}-{month:02d}-{day:02d}~{year_end:04d}-{month_end:02d}-{day_end:02d}",
        "default": lambda: f"{year:04d}-{month:02d}-{day:02d}" if dr.start_ad == dr.end_ad else \
                           (f"{year:04d}-{month:02d}-{day:02d}~{day_end:02d}" if (month, year) == (month_end, year_end) else f"{year:04d}-{month:02d}-{day:02d}~{year_end:04d}-{month_end:02d}-{day_end:02d}")
    }
    iso_repl = iso_formats.get(result_type, iso_formats["default"])()
    
    # Devanagari mirroring
    if is_bs and any("\u0900" <= c <= "\u097F" for t in expr.tokens for c in t.text):
        iso_repl = iso_repl.translate(_DEVANAGARI_DIGIT_MAP)

    # Wrap BS dates in <BS> tag for calendar identification; AD stays plain ISO
    if is_bs:
        iso_repl = f"<BS>{iso_repl}</BS>"

    return ResolvedDate(
        expression=expr, calendar="BS" if is_bs else "AD", type=result_type,
        year=year, month=month, day=day,
        start=f"{year:04d}-{month:02d}-{day:02d}", 
        end=f"{year_end:04d}-{month_end:02d}-{day_end:02d}",
        iso_replacement=iso_repl
    )
