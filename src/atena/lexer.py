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
        self._brace_depth: int = 0             # tracks open { } — colon inside dict is not an off-ramp

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _current(self) -> str | None:
        """Return the character at the current position, or None at end."""
        if self._pos < len(self._source):
            return self._source[self._pos]
        return None

    def _peek(self) -> str | None:
        """Return the character one position ahead, or None if past end."""
        next_pos = self._pos + 1
        if next_pos < len(self._source):
            return self._source[next_pos]
        return None

    def _advance(self) -> str | None:
        """Consume and return the current character; update line/col tracking."""
        ch = self._current()
        if ch is None:
            return None
        self._pos += 1
        if ch == '\n':
            self._line += 1
            self._col = 0
        else:
            self._col += 1
        return ch

    def _emit_token(self, tok_type: TokenType, value: str, col: int, source_line: str) -> None:
        """Append a Token to the output list."""
        self._tokens.append(
            Token(type=tok_type, value=value, line=self._line, col=col, source_line=source_line)
        )

    # ------------------------------------------------------------------
    # Line scanning
    # ------------------------------------------------------------------

    def _scan_line(self, raw_line: str) -> None:
        """Scan one physical line from the source."""
        source_line = raw_line.rstrip('\n')

        # Skip blank and comment-only lines before any other processing.
        stripped = raw_line.lstrip()
        if not stripped or stripped.startswith('#'):
            # Advance past the entire line including the trailing newline.
            while self._current() is not None and self._current() != '\n':
                self._advance()
            if self._current() == '\n':
                self._advance()
            return

        # Skip leading whitespace (indentation) — Plan 03 replaces with real engine.
        while self._current() in (' ', '\t'):
            self._advance()

        # Scan remaining characters on the line until newline or end.
        while self._current() is not None and self._current() != '\n':
            ch = self._current()

            # Mid-line whitespace.
            if ch in (' ', '\t'):
                self._advance()
                continue

            # Identifier or keyword.
            if ch.isalpha() or ch == '_':
                start_col = self._col
                buf: list[str] = []
                while self._current() is not None and (self._current().isalnum() or self._current() == '_'):
                    buf.append(self._current())
                    self._advance()
                word = ''.join(buf)
                tok_type = KEYWORDS.get(word, TokenType.IDENTIFIER)
                self._emit_token(tok_type, word, start_col, source_line)
                continue

            # Integer (and decimal off-ramp).
            if ch.isdigit():
                start_col = self._col
                int_buf: list[str] = []
                while self._current() is not None and self._current().isdigit():
                    int_buf.append(self._current())
                    self._advance()
                integer_part = ''.join(int_buf)
                # Decimal off-ramp: digit-dot-digit triggers friendly error.
                if (self._current() == '.'
                        and self._peek() is not None
                        and self._peek().isdigit()):
                    # Consume the dot.
                    self._advance()
                    # Collect fractional digits.
                    frac_buf: list[str] = []
                    while self._current() is not None and self._current().isdigit():
                        frac_buf.append(self._current())
                        self._advance()
                    fraction_part = ''.join(frac_buf)
                    try:
                        low = int(integer_part)
                        high = low + 1
                        self._errors.add(
                            self._line,
                            f'Atena works with whole numbers only — try {low} or {high} instead of {integer_part}.{fraction_part}.',
                            source_line,
                        )
                    except Exception:
                        self._errors.add(
                            self._line,
                            'Atena works with whole numbers only — use a whole number instead.',
                            source_line,
                        )
                    # Still emit the integer part so scanning can continue.
                    self._emit_token(TokenType.NUMBER, integer_part, start_col, source_line)
                else:
                    self._emit_token(TokenType.NUMBER, integer_part, start_col, source_line)
                continue

            # Double-quoted string literal.
            if ch == '"':
                start_col = self._col
                self._advance()  # consume opening '"'
                str_buf: list[str] = []
                while self._current() is not None and self._current() not in ('"', '\n'):
                    str_buf.append(self._current())
                    self._advance()
                if self._current() == '"':
                    self._advance()  # consume closing '"'
                    self._emit_token(TokenType.STRING, ''.join(str_buf), start_col, source_line)
                else:
                    # Unterminated string — no token emitted.
                    self._errors.add(
                        self._line,
                        'I found a piece of text that was never closed — make sure every " has a matching ".',
                        source_line,
                    )
                continue

            # Single-quoted string off-ramp.
            if ch == "'":
                start_col = self._col
                self._advance()  # consume the opening single-quote (always makes progress)
                # Scan to closing single-quote or end of line.
                while self._current() is not None and self._current() not in ("'", '\n'):
                    self._advance()
                if self._current() == "'":
                    self._advance()  # consume closing single-quote
                self._errors.add(
                    self._line,
                    'Atena text goes inside double quotes — try using "..." instead.',
                    source_line,
                )
                continue

            # Assignment vs equality comparison (maximal-munch).
            if ch == '=':
                start_col = self._col
                self._advance()  # consume first '='
                if self._current() == '=':
                    self._advance()  # consume second '='
                    self._emit_token(TokenType.COMPARISON, '==', start_col, source_line)
                else:
                    self._emit_token(TokenType.ASSIGN, '=', start_col, source_line)
                continue

            # Not-equal comparison.
            if ch == '!':
                start_col = self._col
                self._advance()  # consume '!'
                if self._current() == '=':
                    self._advance()  # consume '='
                    self._emit_token(TokenType.COMPARISON, '!=', start_col, source_line)
                else:
                    self._errors.add(
                        self._line,
                        f'I don\'t know what "!" means — check for a typo or an unsupported character.',
                        source_line,
                    )
                continue

            # Less-than (or less-than-or-equal).
            if ch == '<':
                start_col = self._col
                self._advance()  # consume '<'
                if self._current() == '=':
                    self._advance()  # consume '='
                    self._emit_token(TokenType.COMPARISON, '<=', start_col, source_line)
                else:
                    self._emit_token(TokenType.COMPARISON, '<', start_col, source_line)
                continue

            # Greater-than (or greater-than-or-equal).
            if ch == '>':
                start_col = self._col
                self._advance()  # consume '>'
                if self._current() == '=':
                    self._advance()  # consume '='
                    self._emit_token(TokenType.COMPARISON, '>=', start_col, source_line)
                else:
                    self._emit_token(TokenType.COMPARISON, '>', start_col, source_line)
                continue

            # Arithmetic operators.
            if ch in ('+', '-', '*', '/'):
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.OPERATOR, ch, start_col, source_line)
                continue

            # Brackets and punctuation.
            if ch == '(':
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.LPAREN, '(', start_col, source_line)
                continue
            if ch == ')':
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.RPAREN, ')', start_col, source_line)
                continue
            if ch == '[':
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.LBRACKET, '[', start_col, source_line)
                continue
            if ch == ']':
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.RBRACKET, ']', start_col, source_line)
                continue
            if ch == '{':
                start_col = self._col
                self._advance()
                self._brace_depth += 1
                self._emit_token(TokenType.LBRACE, '{', start_col, source_line)
                continue
            if ch == '}':
                start_col = self._col
                self._advance()
                if self._brace_depth > 0:
                    self._brace_depth -= 1
                self._emit_token(TokenType.RBRACE, '}', start_col, source_line)
                continue
            if ch == ',':
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.COMMA, ',', start_col, source_line)
                continue
            if ch == '.':
                start_col = self._col
                self._advance()
                self._emit_token(TokenType.DOT, '.', start_col, source_line)
                continue

            # Colon off-ramp (only outside dict/set literals — inside braces, colon is valid syntax).
            if ch == ':':
                self._advance()  # consume ':' first (always makes progress)
                if self._brace_depth == 0:
                    self._errors.add(
                        self._line,
                        "Atena doesn't use colons — just indent the next line to start the block.",
                        source_line,
                    )
                continue

            # Semicolon off-ramp.
            if ch == ';':
                self._errors.add(
                    self._line,
                    'Put each step on its own line.',
                    source_line,
                )
                self._advance()  # consume ';' and continue
                continue

            # Comment: skip to end of line.
            if ch == '#':
                while self._current() is not None and self._current() != '\n':
                    self._advance()
                continue

            # Generic unexpected character (always-make-progress guaranteed).
            self._errors.add(
                self._line,
                f'I don\'t know what "{ch}" means — check for a typo or an unsupported character.',
                source_line,
            )
            self._advance()  # consume unexpected char; always makes progress

        # Consume the trailing newline (Plan 03 will emit NEWLINE here instead).
        if self._current() == '\n':
            self._advance()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Scan all source text and return the complete token list."""
        for raw_line in self._lines:
            self._scan_line(raw_line)

        # Handle source with no trailing newline — pos may not be at end yet,
        # but _scan_line handles that. Emit EOF.
        self._emit_token(TokenType.EOF, '', 0, '')
        return self._tokens
