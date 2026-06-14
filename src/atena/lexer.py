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
        # Normalize line endings up front so Windows (CRLF) and legacy (lone CR)
        # files lex identically to LF. Without this, a trailing '\r' survives
        # rstrip('\n') and hits the unexpected-character handler on every line.
        self._source = source.replace('\r\n', '\n').replace('\r', '\n')
        self._errors = errors           # injected — never instantiate internally
        self._lines = self._source.splitlines(keepends=True)
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
        """Consume and return the current character; update col tracking only.

        Note: self._line is managed by the outer loop in tokenize() (set to
        line_index + 1 at the start of each iteration). _advance() updates
        self._pos and self._col only — it does NOT increment self._line.
        """
        ch = self._current()
        if ch is None:
            return None
        self._pos += 1
        if ch == '\n':
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
    # Indentation engine
    # ------------------------------------------------------------------

    def _measure_indent(self, raw_line: str) -> tuple[int, str]:
        """Count leading whitespace and return (width, indent_chars).

        width       = number of leading whitespace characters (char-count, not column-count;
                      a tab counts as 1 just like a space)
        indent_chars = the raw leading whitespace substring (raw_line[:width])
        """
        i = 0
        while i < len(raw_line) and raw_line[i] in (' ', '\t'):
            i += 1
        return i, raw_line[:i]

    def _handle_indentation(self, width: int, indent_chars: str, source_line: str) -> None:
        """Emit INDENT/DEDENT tokens and validate uniform-step indentation.

        Implements the standard stack algorithm (D-08) plus the uniform-step
        validation layer (D-05/D-06/D-07). Errors are collected and scanning
        always continues (D-04 recover-and-continue).

        Arguments:
            width        -- number of leading whitespace characters
            indent_chars -- the raw leading whitespace (raw_line[:width])
            source_line  -- the line without its trailing newline, for error stamps
        """
        top = self._indent_stack[-1]

        # Tab/space mixing check: runs first, regardless of indent/dedent/same direction.
        # The check compares leading characters against the pinned indent character.
        mixing_error = False
        if width > 0:
            if self._indent_char is not None:
                # Check that every character in the leading whitespace matches the pinned char.
                for ch in indent_chars:
                    if ch != self._indent_char:
                        self._errors.add(
                            self._line,
                            "Don't mix tabs and spaces for indentation — pick one and use it everywhere.",
                            source_line,
                        )
                        mixing_error = True
                        break
            else:
                # Pin the indent character on first indented line.
                if indent_chars:
                    self._indent_char = indent_chars[0]

        if width == top:
            # Same level — no structural change, no further validation needed.
            return

        if width > top:
            # INDENT branch.

            # Uniform-step unit check (only when no mixing error on this line).
            if not mixing_error:
                delta = width - top
                if self._indent_unit is None:
                    # First indent sets the unit.
                    self._indent_unit = delta
                else:
                    if delta > self._indent_unit:
                        self._errors.add(
                            self._line,
                            "This line is indented too far — keep each step the same size.",
                            source_line,
                        )
                    elif delta != self._indent_unit:
                        self._errors.add(
                            self._line,
                            "Keep your indentation the same size as the rest of the file.",
                            source_line,
                        )

            # Push and emit INDENT (always — D-04 recover-and-continue keeps stream parseable).
            self._indent_stack.append(width)
            self._emit_token(TokenType.INDENT, "", 0, source_line)
            return

        # DEDENT branch (width < top).
        # Pop until stack top <= width (the pop loop always terminates because
        # the stack shrinks on each iteration and is initialised with [0]).
        while self._indent_stack[-1] > width:
            self._indent_stack.pop()
            self._emit_token(TokenType.DEDENT, "", 0, source_line)

        # After popping, check that the stack landed exactly on `width`.
        if self._indent_stack[-1] != width:
            self._errors.add(
                self._line,
                "This line's indentation doesn't match any block above it.",
                source_line,
            )
            # Do not push or pop further — error reported, scanning continues (D-04).
            return

        # Stack matched exactly. Validate dedent width against uniform-step unit
        # (only when the dedented level is non-zero — zero means back at base).
        if self._indent_unit is not None and width != 0:
            if width % self._indent_unit != 0:
                self._errors.add(
                    self._line,
                    "Keep your indentation the same size as the rest of the file.",
                    source_line,
                )

    def _drain_at_eof(self) -> None:
        """Drain all open blocks at EOF and emit the final EOF token.

        Emits a trailing NEWLINE if the last token was not already a structural
        token, then pops all remaining indent stack entries (except the base 0),
        and finally emits EOF.
        """
        last = self._tokens[-1] if self._tokens else None
        if last is not None and last.type not in (
            TokenType.NEWLINE,
            TokenType.DEDENT,
            TokenType.INDENT,
            TokenType.EOF,
        ):
            self._emit_token(TokenType.NEWLINE, "", 0, "")

        # Drain all open blocks.
        while len(self._indent_stack) > 1:
            self._indent_stack.pop()
            self._emit_token(TokenType.DEDENT, "", 0, "")

        # Emit EOF.
        self._emit_token(TokenType.EOF, "", 0, "")

    # ------------------------------------------------------------------
    # Line scanning
    # ------------------------------------------------------------------

    def _scan_line(self, raw_line: str, start_col: int) -> None:
        """Scan the content portion of one physical line (after indentation is handled).

        The outer loop in tokenize() has already:
          - set self._line to the correct 1-based line number
          - called _handle_indentation() for this line
          - set self._col = start_col (first content character column)
          - set self._pos to the absolute offset of the first content character

        This method scans from that point through the end of the content (stopping
        before '\n' or at end of source), then emits NEWLINE.
        """
        source_line = raw_line.rstrip('\n')

        # Scan content characters until newline or end of source.
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

            # Integer (and decimal off-ramp). Guard with isascii() so non-ASCII
            # Unicode digits (e.g. Arabic-Indic ١٢٣) are not accepted as numbers —
            # they would otherwise slip through to codegen and crash ast.parse (CR-01).
            if ch.isdigit() and ch.isascii():
                start_col = self._col
                int_buf: list[str] = []
                while self._current() is not None and self._current().isdigit() and self._current().isascii():
                    int_buf.append(self._current())
                    self._advance()
                integer_part = ''.join(int_buf)
                # Decimal off-ramp: digit-dot-digit triggers friendly error.
                if (self._current() == '.'
                        and self._peek() is not None
                        and self._peek().isdigit() and self._peek().isascii()):
                    # Consume the dot.
                    self._advance()
                    # Collect fractional digits.
                    frac_buf: list[str] = []
                    while self._current() is not None and self._current().isdigit() and self._current().isascii():
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

        # Emit NEWLINE at end of content line.
        self._emit_token(TokenType.NEWLINE, "", 0, source_line)

        # Consume the trailing newline character (advances self._pos past it).
        if self._current() == '\n':
            self._advance()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Scan all source text and return the complete token list.

        Outer loop strategy:
          - Iterate over lines by index so self._line is set explicitly per
            iteration (self._line = line_index + 1). _advance() does NOT
            increment self._line.
          - Skip blank lines and comment-only lines BEFORE touching the indent
            stack (Pattern 3 — blank/comment lines must not affect indentation).
          - For content lines: measure indent, handle indentation (INDENT/DEDENT),
            then scan the content, then emit NEWLINE.
          - Track the absolute source position (abs_pos) so self._pos points to
            the first content character before calling the scanner.
        """
        abs_pos = 0  # running byte offset into self._source

        for line_index, raw_line in enumerate(self._lines):
            self._line = line_index + 1

            # Skip blank lines and comment-only lines before touching the stack.
            stripped = raw_line.lstrip()
            if not stripped or stripped.startswith('#'):
                abs_pos += len(raw_line)
                continue

            # Measure indentation.
            width, indent_chars = self._measure_indent(raw_line)

            # Handle INDENT/DEDENT emission and validate uniform-step.
            source_line = raw_line.rstrip('\n')
            self._handle_indentation(width, indent_chars, source_line)

            # Set up cursor for content scanning: skip past the indent characters.
            self._pos = abs_pos + width
            self._col = width

            # Scan the content characters and emit NEWLINE at end.
            self._scan_line(raw_line, width)

            abs_pos += len(raw_line)

        # Drain all open blocks and emit EOF.
        self._drain_at_eof()

        return self._tokens
