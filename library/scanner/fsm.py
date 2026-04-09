import copy
from typing import List, Set

from library.scanner.types import ScannerState, DateExpression, TokenKind, Token
from library.scanner.vocabulary import _NON_TEMPORAL_RIGHT, _RANGE_BRIDGES

# ── FSM Declarative Rules ──
_IMMEDIATE_TRIGGERS = frozenset({
    TokenKind.RELATIVE_ADVERB, TokenKind.MONTH_NAME, 
    TokenKind.WEEKDAY_NAME, TokenKind.NUMERIC_DATE
})

# Maps a triggering TokenKind to a tuple of (lookahead_distance, {valid_target_kinds})
_LOOKAHEAD_TRIGGERS = {
    TokenKind.TEMPORAL_MODIFIER: (3, frozenset({TokenKind.TEMPORAL_UNIT, TokenKind.MONTH_NAME, TokenKind.WEEKDAY_NAME, TokenKind.ORDINAL, TokenKind.TARIKH})),
    TokenKind.ORDINAL: (3, frozenset({TokenKind.TEMPORAL_UNIT, TokenKind.MONTH_NAME})),
    TokenKind.NUMBER: (2, frozenset({TokenKind.TEMPORAL_UNIT, TokenKind.DIRECTION})),
    TokenKind.TEMPORAL_UNIT: (2, frozenset({TokenKind.ORDINAL, TokenKind.TEMPORAL_UNIT, TokenKind.MONTH_NAME, TokenKind.TEMPORAL_MODIFIER, TokenKind.DIRECTION})),
    TokenKind.DIRECTION: (3, frozenset({TokenKind.NUMBER, TokenKind.TEMPORAL_UNIT})),
}

_CONTEXT_BREAKERS = frozenset({TokenKind.REGULAR, TokenKind.PUNCTUATION, TokenKind.RECURRENCE})
_BLOCKLIST_TRIGGERS = frozenset({TokenKind.TEMPORAL_UNIT, TokenKind.TARIKH})


class FSMScanner:
    """A forward-only declarative finite state machine."""
    
    def __init__(self):
        self.state = ScannerState()
        self.extractions: List[DateExpression] = []

    def _emit_current(self):
        """Finalizes the buffer if it holds valid expressions."""
        if not self.state.buffer:
            return
            
        # Postposition shifting
        trailing_postpositions = []
        while self.state.buffer and self.state.buffer[-1].kind == TokenKind.POSTPOSITION:
            trailing_postpositions.insert(0, self.state.buffer.pop())
            
        if self.state.buffer:
            self.extractions.append(DateExpression(
                tokens=copy.copy(self.state.buffer),
                span=(self.state.buffer[0].span[0], self.state.buffer[-1].span[1]),
                trailing_postposition="".join(t.text for t in trailing_postpositions) if trailing_postpositions else None,
                trailing_post_span=(trailing_postpositions[0].span[0], trailing_postpositions[-1].span[1]) if trailing_postpositions else None,
                calendar_signal=self.state.calendar_signal,
                scope_stack=copy.copy(self.state.scope_stack)
            ))
            
        self.state.reset()
        
    def _check_lookahead(self, tokens: List[Token], index: int, lookahead: int, targets: Set[TokenKind]) -> bool:
        """Determines if a target token exists within N lookahead steps without hitting a context break."""
        window = tokens[index + 1 : index + 1 + lookahead]
        return any(t.kind in targets for t in window) and \
               not any(t.kind in _CONTEXT_BREAKERS for t in window[:[t.kind in targets for t in window].index(True) if True in [t.kind in targets for t in window] else 0])

    def scan(self, tokens: List[Token]) -> List[DateExpression]:
        self.state.reset()
        self.extractions.clear()
        
        # State transitions mapping
        def _handle_idle(token: Token, i: int):
            if token.kind in _IMMEDIATE_TRIGGERS:
                return _start_collecting(token)
            if token.kind in _LOOKAHEAD_TRIGGERS:
                distance, targets = _LOOKAHEAD_TRIGGERS[token.kind]
                if self._check_lookahead(tokens, i, distance, targets):
                    return _start_collecting(token)

        def _handle_collecting(token: Token):
            # 1. Guard against blocklists
            last_non_pp = next((t for t in reversed(self.state.buffer) if t.kind != TokenKind.POSTPOSITION), None)
            if last_non_pp and last_non_pp.kind in _BLOCKLIST_TRIGGERS and token.norm in _NON_TEMPORAL_RIGHT:
                return self.state.reset()  # BLOCKED

            # 2. Context Breaks
            if token.kind in _CONTEXT_BREAKERS:
                return self._emit_current()
            
            # 3. Trigger Swaps (New trigger immediately follows previous)
            if token.kind in _IMMEDIATE_TRIGGERS:
                # Bypass swap if the previous token bridges a range
                prev = self.state.buffer[-1] if self.state.buffer else None
                if prev and prev.kind in {TokenKind.POSTPOSITION, TokenKind.TEMPORAL_MODIFIER, TokenKind.PUNCTUATION}:
                    if prev.norm in _RANGE_BRIDGES or prev.text in _RANGE_BRIDGES:
                        self.state.buffer.append(token)
                        return
                        
                self._emit_current()
                return _start_collecting(token)
                
            # 4. Standard Extension
            self.state.buffer.append(token)
            if token.kind == TokenKind.TARIKH:
                self.state.calendar_signal = "AD"

        def _start_collecting(token: Token):
            self.state.mode = "COLLECTING"
            self.state.buffer.append(token)
            if token.kind == TokenKind.TARIKH:
                self.state.calendar_signal = "AD"

        # FSM Execution
        for i, token in enumerate(tokens):
            if self.state.mode == "IDLE":
                _handle_idle(token, i)
            elif self.state.mode == "COLLECTING":
                _handle_collecting(token)

        if self.state.mode == "COLLECTING":
            self._emit_current()
            
        return self.extractions
