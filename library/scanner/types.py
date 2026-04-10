from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional, List, Tuple


class TokenKind(Enum):
    RELATIVE_ADVERB = "rel_adverb"
    MONTH_NAME = "month_name"
    WEEKDAY_NAME = "weekday_name"
    NUMERIC_DATE = "numeric_date"
    TEMPORAL_MODIFIER = "modifier"
    ORDINAL = "ordinal"
    RECURRENCE = "recurrence"
    TEMPORAL_UNIT = "temp_unit"
    TARIKH = "tarikh"
    GATE = "gate"
    POSTPOSITION = "postposition"
    NUMBER = "number"
    DIRECTION = "direction"
    REGULAR = "regular"
    PUNCTUATION = "punctuation"


@dataclass(frozen=True)
class Token:
    text: str
    norm: str
    kind: TokenKind
    span: Tuple[int, int]
    value: Optional[int | str] = None


@dataclass
class ScopeLevel:
    unit: str
    ordinal: Optional[int] = None
    modifier: Optional[str] = None
    tarikh_ad: bool = False


@dataclass
class DateExpression:
    tokens: List[Token]
    span: Tuple[int, int]
    trailing_postposition: Optional[str]
    trailing_post_span: Optional[Tuple[int, int]]
    calendar_signal: Literal["BS", "AD"]
    scope_stack: List[ScopeLevel]


@dataclass
class ResolvedDate:
    expression: DateExpression
    calendar: Literal["BS", "AD"]
    type: str
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]
    start: str
    end: str
    iso_replacement: str


@dataclass
class ScanResult:
    original_text: str
    normalized_text: str
    extractions: List[dict]


@dataclass
class ScannerState:
    mode: Literal["IDLE", "COLLECTING"] = "IDLE"
    buffer: List[Token] = field(default_factory=list)
    calendar_signal: Literal["BS", "AD"] = "BS"
    scope_stack: List[ScopeLevel] = field(default_factory=list)

    def reset(self) -> None:
        self.buffer.clear()
        self.calendar_signal = "BS"
        self.scope_stack.clear()
        self.mode = "IDLE"
