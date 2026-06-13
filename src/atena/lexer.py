"""
Lexer for the Atena transpiler.

Scans Atena source text into a fully-materialised list[Token] with
balanced INDENT/DEDENT tokens, stamped with line, col, and source_line.
Errors are collected through the injected ErrorCollector — the lexer
never raises to the user and never emits a Python traceback.
"""

from __future__ import annotations

from atena.tokens import TokenType, Token, KEYWORDS
from atena.errors import ErrorCollector


class Lexer:
    """Scans Atena source text into a list[Token]."""

    def __init__(self, source: str, errors: ErrorCollector) -> None:
        self._source = source
        self._errors = errors           # injected — never instantiate internally
        self._lines = source.splitlines(keepends=True)
        self._pos = 0
        self._line = 1                  # 1-based (matches Token.line contract)
        self._col = 0                   # 0-based (matches Token.col contract)
        self._indent_stack: list[int] = [0]
        self._indent_char: str | None = None   # ' ' or '\t', pinned on first indent
        self._indent_unit: int | None = None   # width of one step, pinned on first indent
        self._tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        """Scan all source text and return the complete token list.

        RED phase stub — raises NotImplementedError until Plan 01-02 implements
        the full scanning loop.
        """
        raise NotImplementedError("Lexer.tokenize() not yet implemented — RED phase")
