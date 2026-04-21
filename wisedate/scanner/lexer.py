import re
from typing import List, Callable, Dict, Any, Tuple

from wisedate.nepali_date import (
    _BS_MONTH_ALIASES, 
    _AD_MONTH_ALIASES, 
    _WEEKDAY_ALIASES
)
from wisedate.scanner.types import Token, TokenKind
from wisedate.scanner.vocabulary import (
    _TEMPORAL_UNITS, 
    _TEMPORAL_MODIFIERS, 
    _ORDINALS, 
    _POSTPOSITIONS,
    _RECURRENCE_WORDS, 
    _RELATIVE_ADVERBS, 
    _DIRECTION_WORDS,
    _KEYWORD_TARIKH, 
    _KEYWORD_GATE, 
    _PUNCTUATIONS, 
    _DEVANAGARI_DIGIT_REVERSE,
    _WORD_NUMBERS
)

_ISO_DATE_PATTERN = re.compile(r"^([0-9०-९]{4})-([0-9०-९]{2})-([0-9०-९]{2})$")
_NUMBER_PATTERN = re.compile(r"^[0-9०-९]+$")

# Multiword phrases
_MULTIWORD_PHRASES = [
    "day after tomorrow",
    "day before yesterday",
    "start of",
    "end of",
    "middle of",
    "beginning of",
    "close of",
    "half year",
    "fiscal year",
    "आर्थिक वर्ष",
]

def _normalize_numeral(word: str) -> str:
    return "".join(_DEVANAGARI_DIGIT_REVERSE.get(ch, ch) for ch in word)

# Dictionary mapping lookup tables to their TokenKind and an optional mapper function
_VOCAB_CLASSIFIERS: List[Tuple[Dict[str, Any] | set, TokenKind, Callable[[str], Any] | None]] = [
    (_RELATIVE_ADVERBS, TokenKind.RELATIVE_ADVERB, lambda n: _RELATIVE_ADVERBS[n]),
    ({**_BS_MONTH_ALIASES, **_AD_MONTH_ALIASES}, TokenKind.MONTH_NAME, lambda n: {**_BS_MONTH_ALIASES, **_AD_MONTH_ALIASES}[n]),
    (_WEEKDAY_ALIASES, TokenKind.WEEKDAY_NAME, lambda n: _WEEKDAY_ALIASES[n]),
    (_TEMPORAL_MODIFIERS, TokenKind.TEMPORAL_MODIFIER, lambda n: _TEMPORAL_MODIFIERS[n]),
    (_ORDINALS, TokenKind.ORDINAL, lambda n: _ORDINALS[n]),
    (_WORD_NUMBERS, TokenKind.NUMBER, lambda n: _WORD_NUMBERS[n]),
    (_RECURRENCE_WORDS, TokenKind.RECURRENCE, None),
    (_TEMPORAL_UNITS, TokenKind.TEMPORAL_UNIT, lambda n: _TEMPORAL_UNITS[n]),
    (_DIRECTION_WORDS, TokenKind.DIRECTION, lambda n: _DIRECTION_WORDS[n]),
    (_KEYWORD_TARIKH, TokenKind.TARIKH, None),
    (_KEYWORD_GATE, TokenKind.GATE, None),
    (_POSTPOSITIONS, TokenKind.POSTPOSITION, None),
]

def _classify_word(word: str, start: int, end: int) -> Token:
    norm = word.lower()
    
    # 1. Check Regex patterns
    if _ISO_DATE_PATTERN.match(norm):
        return Token(word, norm, TokenKind.NUMERIC_DATE, (start, end))
    if _NUMBER_PATTERN.match(norm):
        return Token(word, norm, TokenKind.NUMBER, (start, end), int(_normalize_numeral(norm)))

    # 2. Check Vocabulary Matchers using generator
    match = next(
        (Token(word, norm, kind, (start, end), mapper(norm) if mapper else None)
         for vocab, kind, mapper in _VOCAB_CLASSIFIERS if norm in vocab),
        None
    )
    
    return match or Token(word, norm, TokenKind.REGULAR, (start, end))

def lex(text: str) -> List[Token]:
    """Tokenizes raw text into Tokens, dynamically extracting postposition suffixes."""
    # Pre-process multi-word English relative adverbs to avoid them being split,
    # mapping spaces to underscores to perfectly preserve index span lengths
    text_lower = text.lower()
    for phrase in _MULTIWORD_PHRASES:
        idx = text_lower.find(phrase)
        while idx != -1:
            end_idx = idx + len(phrase)
            chunk = text[idx:end_idx].replace(" ", "_")
            text = text[:idx] + chunk + text[end_idx:]
            text_lower = text.lower()
            idx = text_lower.find(phrase)

    # Split by spaces and punctuation, retaining all parts for accurate offset counting
    pieces = re.split(r"(\s+|[.,!?;:|।])", text)
    
    # Sorted length-descending postpositions for aggressive suffix stripping
    sorted_postpositions = sorted(_POSTPOSITIONS, key=len, reverse=True)
    
    # Known temporal vocabularies that can have suffixes stuck to them
    temporal_roots = {
        *_TEMPORAL_UNITS.keys(), *_RELATIVE_ADVERBS.keys(),
        *_BS_MONTH_ALIASES.keys(), *_AD_MONTH_ALIASES.keys(),
        *_WEEKDAY_ALIASES.keys(), *_ORDINALS.keys(),
        *_KEYWORD_TARIKH, *_KEYWORD_GATE, *_DIRECTION_WORDS.keys()
    }

    def _process_piece(piece: str, start_char: int, end_char: int) -> List[Token]:
        if piece.isspace():
            return []
        if piece in _PUNCTUATIONS:
            return [Token(piece, piece, TokenKind.PUNCTUATION, (start_char, end_char))]
        
        # Suffix matching logic using generator to find the first valid agglutinate
        agglutinate = next(
            ([
                _classify_word(
                    piece[:-len(pp)], start_char, 
                    start_char + len(piece[:-len(pp)])
                ),
                Token(
                    pp, pp, TokenKind.POSTPOSITION, 
                    (start_char + len(piece[:-len(pp)]), end_char)
                )
            ] 
            for pp in sorted_postpositions 
            if piece.endswith(pp) 
            and len(piece) > len(pp) 
            and piece[:-len(pp)].lower() in temporal_roots),
            None
        )
        
        return agglutinate or [_classify_word(piece, start_char, end_char)]

    # Collector style flattening
    offsets = [0] + [len(p) for p in pieces]
    accumulated_offsets = [sum(offsets[:i+1]) for i in range(len(offsets))]
    
    return [
        token 
        for i, piece in enumerate(pieces) if piece 
        for token in _process_piece(
            piece, 
            accumulated_offsets[i], 
            accumulated_offsets[i+1]
        )
    ]
