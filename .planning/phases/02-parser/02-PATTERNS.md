# Phase 2: Parser - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 2 (src/atena/parser.py, tests/test_parser.py)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/atena/parser.py` | service (phase transformer) | transform (token list → AST) | `src/atena/lexer.py` | role-match — same pipeline phase shape: injected ErrorCollector, single public entry point, private helpers, collect-don't-fail-fast |
| `tests/test_parser.py` | test | N/A | `tests/test_lexer.py` | exact — identical three-layer convention, helper function pattern, error-path assertion style |

---

## Pattern Assignments

### `src/atena/parser.py` (phase transformer, token-list → AST)

**Analog:** `src/atena/lexer.py`

**Imports pattern** (`lexer.py` lines 10–13):
```python
from __future__ import annotations

from atena.tokens import TokenType, Token, KEYWORDS
from atena.errors import ErrorCollector
```

For the parser, the import block becomes:
```python
from __future__ import annotations

from atena.tokens import TokenType, Token
from atena.errors import ErrorCollector
from atena.ast_nodes import (
    Program, Assign, Show, Ask, If, While, Repeat,
    FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
    ListLiteral, DictLiteral, IndexAccess, DotAccess,
    ListAdd, ListRemove, Identifier, NumberLiteral,
    StringLiteral, BoolLiteral,
)
```

Key constraint carried from CONTEXT.md §code_context "Established Patterns": pure data modules (`tokens.py`, `ast_nodes.py`) import nothing sibling; `parser.py` imports `tokens` + `ast_nodes` + `errors` only — no other sibling imports.

---

**Constructor injection pattern** (`lexer.py` lines 19–33):
```python
class Lexer:
    """Scans Atena source text into a list[Token]."""

    def __init__(self, source: str, errors: ErrorCollector) -> None:
        self._source = source.replace('\r\n', '\n').replace('\r', '\n')
        self._errors = errors           # injected — never instantiate internally
        self._lines = self._source.splitlines(keepends=True)
        self._pos = 0
        self._line = 1
        self._col = 0
        self._indent_stack: list[int] = [0]
        self._tokens: list[Token] = []
```

Parser equivalent — copy the injection shape; state fields will differ:
```python
class Parser:
    """Parses a list[Token] into a Program AST."""

    def __init__(self, tokens: list[Token], errors: ErrorCollector) -> None:
        self._tokens = tokens           # fully-materialised list from the Lexer
        self._errors = errors           # injected — never instantiate internally
        self._pos = 0                   # index into self._tokens
        self._fn_depth = 0              # tracks function nesting for top-level return check (D-04 item 3)
```

The `_errors` comment ("injected — never instantiate internally") is the signal that the module must not create its own `ErrorCollector`. The planner should copy this convention exactly.

---

**Private cursor helper pattern** (`lexer.py` lines 39–67):
```python
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
    """Consume and return the current character..."""
    ch = self._current()
    if ch is None:
        return None
    self._pos += 1
    ...
    return ch
```

Parser equivalent cursor helpers — same pattern applied to `list[Token]`:
```python
def _current(self) -> Token:
    """Return the token at the current position (never None — returns EOF sentinel)."""
    if self._pos < len(self._tokens):
        return self._tokens[self._pos]
    return self._tokens[-1]   # EOF token is always the last element

def _peek(self) -> Token:
    """Return the token one position ahead (returns EOF if past end)."""
    pos = self._pos + 1
    if pos < len(self._tokens):
        return self._tokens[pos]
    return self._tokens[-1]

def _advance(self) -> Token:
    """Consume and return the current token; advance the position."""
    tok = self._current()
    if tok.type != TokenType.EOF:
        self._pos += 1
    return tok

def _check(self, *types: TokenType) -> bool:
    """Return True if the current token's type is one of the given types."""
    return self._current().type in types

def _match(self, *types: TokenType) -> Token | None:
    """Consume and return the current token if its type matches; else return None."""
    if self._check(*types):
        return self._advance()
    return None

def _expect(self, tok_type: TokenType, message: str) -> Token:
    """Consume a token of the given type; raise _ParseError if not found."""
    if self._check(tok_type):
        return self._advance()
    tok = self._current()
    raise _ParseError(tok.line, message, tok.source_line)

def _at_end(self) -> bool:
    """Return True when at the EOF token."""
    return self._current().type == TokenType.EOF
```

`ARCHITECTURE.md` §Component Responsibilities specifies exactly `current`/`peek`/`advance`/`expect`/`match` as the parser's helper set.

---

**Internal error / ParseError pattern** (`lexer.py` does NOT raise; ARCHITECTURE.md Pattern 7):

The lexer never uses internal exception control flow. The parser does — with a narrow internal exception that never escapes to the user:

```python
class _ParseError(Exception):
    """Internal control-flow exception — caught only at statement boundaries.

    Never surfaced to the user. The parser catches this inside parse_statement()
    and calls self._errors.add() before synchronizing.
    """

    def __init__(self, line: int, message: str, source_line: str) -> None:
        self.line = line
        self.message = message
        self.source_line = source_line
```

Rule from ARCHITECTURE.md Pattern 7: `_ParseError` is an internal tool raised by `_expect()` and caught *only* at the `parse_statement()` boundary. The design mirrors how the lexer's `_errors.add()` calls are terminal per-character handler invocations — both approaches guarantee the exception/error never reaches the user.

---

**Error collection pattern — never format, just add** (`lexer.py` lines 112–119, 271–275):
```python
self._errors.add(
    self._line,
    "Don't mix tabs and spaces for indentation — pick one and use it everywhere.",
    source_line,
)
```

Parser mirrors this exactly — supply `line`, `message`, `source_line`; never format `"Error on line …"` (that is `errors.py`'s responsibility):
```python
self._errors.add(
    tok.line,
    'Atena uses "function", not "def" — try: function greet(name).',
    tok.source_line,
)
```

The `source_line` field is available on every `Token` — copy it from the triggering token (`tok.source_line`).

---

**Public entry point pattern** (`lexer.py` lines 471–520):
```python
def tokenize(self) -> list[Token]:
    """Scan all source text and return the complete token list."""
    abs_pos = 0
    for line_index, raw_line in enumerate(self._lines):
        ...
    self._drain_at_eof()
    return self._tokens
```

Parser equivalent — single public method returning the root AST node:
```python
def parse(self) -> Program:
    """Parse all tokens and return the Program root node.

    Returns a (potentially partial) Program even when errors were collected.
    The driver gates later phases on errors.is_empty(); it is the driver's
    responsibility to check, not the parser's.
    """
    program = Program(line=1, source_line="")
    while not self._at_end():
        stmt = self._parse_statement()
        if stmt is not None:
            program.statements.append(stmt)
    return program
```

---

**Error-recovery and synchronize pattern** (`ARCHITECTURE.md` Pattern 7, `PITFALLS.md` §12/13):
```python
def _synchronize(self) -> None:
    """Discard tokens until a safe statement-restart point.

    Sync tokens: NEWLINE and DEDENT — the statement/block boundaries.
    Progress invariant: always consumes ≥1 token (PITFALLS.md §13).
    """
    while not self._at_end():
        if self._current().type in (TokenType.NEWLINE, TokenType.DEDENT):
            self._advance()   # consume the sync token itself
            return
        self._advance()

def _parse_statement(self) -> Node | None:
    """Parse one statement; catch _ParseError and synchronize.

    Loop guard: track position before dispatch; force-advance if position
    did not change after a full iteration (progress invariant backstop,
    PITFALLS.md §13).
    """
    pos_before = self._pos
    try:
        return self._dispatch_statement()
    except _ParseError as e:
        self._errors.add(e.line, e.message, e.source_line)
        self._synchronize()
        return None
    finally:
        # Backstop: if position did not advance, force-advance one token.
        if self._pos == pos_before:
            self._advance()
```

---

**Block parsing pattern** (`ARCHITECTURE.md` Pattern 6):
```python
def _parse_block(self) -> list[Node]:
    """Parse an INDENT … DEDENT block; return the list of body statements."""
    self._expect(TokenType.INDENT, 'Expected an indented block here.')
    body: list[Node] = []
    while not self._check(TokenType.DEDENT) and not self._at_end():
        stmt = self._parse_statement()
        if stmt is not None:
            body.append(stmt)
    self._expect(TokenType.DEDENT, 'Expected the end of the indented block.')
    return body
```

---

**Pratt expression parser pattern** (`ARCHITECTURE.md` Pattern 5, `PITFALLS.md` §7/8/9):
```python
# Binding power table — single source of truth for precedence (PITFALLS.md §8).
# Higher number = tighter binding. Left-associative: right operand parsed with bp+1.
_BINARY_BP: dict[str, int] = {
    "or":  1,
    "and": 2,
    # "not" is unary — handled in _parse_unary, not here
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+":  4, "-":  4,
    "*":  5, "/":  5,
    # Postfix [] . () are handled as a tight loop in _parse_postfix, not here.
}

def _parse_expression(self, min_bp: int = 0) -> Node:
    """Pratt expression parser entry point."""
    left = self._parse_unary()
    while True:
        op_tok = self._current()
        # Determine the operator string: OPERATOR/COMPARISON tokens carry the
        # value directly; KEYWORD tokens for "and"/"or" use their value too.
        op_str = op_tok.value
        bp = _BINARY_BP.get(op_str, 0)
        if bp <= min_bp:
            break
        self._advance()                       # consume operator
        right = self._parse_expression(bp)    # left-assoc: same bp, right sees bp (not bp-1)
        left = BinOp(op=op_str, left=left, right=right,
                     line=op_tok.line, source_line=op_tok.source_line)
    return left

def _parse_unary(self) -> Node:
    """Parse unary 'not' and unary '-', then fall through to postfix loop."""
    tok = self._current()
    if tok.value == "not":
        self._advance()
        operand = self._parse_unary()         # right-recursive: 'not not x' is valid
        return UnaryOp(op="not", operand=operand,
                       line=tok.line, source_line=tok.source_line)
    if tok.type == TokenType.OPERATOR and tok.value == "-":
        self._advance()
        # Unary minus binds tighter than any binary op — parse primary+postfix only.
        operand = self._parse_postfix(self._parse_primary())
        return UnaryOp(op="-", operand=operand,
                       line=tok.line, source_line=tok.source_line)
    return self._parse_postfix(self._parse_primary())

def _parse_postfix(self, node: Node) -> Node:
    """Tight postfix loop for [] . () — left-associative, highest binding (PITFALLS.md §9)."""
    while True:
        tok = self._current()
        if tok.type == TokenType.LBRACKET:
            self._advance()
            index = self._parse_expression()
            self._expect(TokenType.RBRACKET, 'I reached the end of the line still waiting for a "]".')
            node = IndexAccess(target=node, index=index, index_converted=False,
                               line=tok.line, source_line=tok.source_line)
        elif tok.type == TokenType.DOT:
            self._advance()
            name_tok = self._expect(TokenType.IDENTIFIER, 'Expected a field name after ".".')
            node = DotAccess(target=node, name=name_tok.value,
                             line=tok.line, source_line=tok.source_line)
        elif tok.type == TokenType.LPAREN:
            self._advance()
            args: list[Node] = []
            if not self._check(TokenType.RPAREN):
                args.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expression())
            self._expect(TokenType.RPAREN, 'I reached the end of the line still waiting for a ")".')
            # Wrap as FunctionCall only if the node is an Identifier.
            if isinstance(node, Identifier):
                node = FunctionCall(name=node.name, args=args,
                                    line=tok.line, source_line=tok.source_line)
            else:
                raise _ParseError(tok.line, 'Only named functions can be called.', tok.source_line)
        else:
            break
    return node
```

---

**AST node construction pattern** — copy line + source_line from the triggering token (CONTEXT.md §code_context, `ARCHITECTURE.md` §Data Flow):
```python
# Triggering token's position fields are threaded onto every AST node.
kw = self._expect(TokenType.KEYWORD, ...)
node = Show(value=expr, line=kw.line, source_line=kw.source_line)
```

Every `@dataclass` node in `ast_nodes.py` inherits `line: int = 0` and `source_line: str = ""` from `Node`. Always supply both from the relevant token at construction — never leave them at default `0`/`""` on a real parsed node.

---

**Python-ism redirect pattern — collected + recover-and-continue** (`CONTEXT.md` D-04/D-06, mirroring lexer off-ramps `lexer.py` lines 426–444):

The lexer off-ramp for colon (lines 426–434) is the direct analog:
```python
# Colon off-ramp (only outside dict/set literals).
if ch == ':':
    self._advance()  # consume ':' first (always makes progress)
    if self._brace_depth == 0:
        self._errors.add(
            self._line,
            "Atena doesn't use colons — just indent the next line to start the block.",
            source_line,
        )
    continue
```

Parser redirect for `def` keyword (same shape — collect error, then synchronize so parsing continues):
```python
# Inside _dispatch_statement(), check for Python keyword identifiers:
if tok.type == TokenType.IDENTIFIER and tok.value == "def":
    raise _ParseError(
        tok.line,
        'Atena uses "function", not "def" — try: function greet(name).',
        tok.source_line,
    )
# _parse_statement() catches _ParseError, calls errors.add(), then synchronizes.
# Equivalent to: collect + recover-and-continue.
```

All six redirect cases from CONTEXT.md D-04 (`def`, `elif`, `for`, `class`, `import`, `==`-as-assignment, top-level `return`) follow this same shape.

---

**`fn_depth` tracking for top-level `return` redirect** (CONTEXT.md D-04 item 3, ARCHITECTURE.md Pattern 7):
```python
def _parse_function_def(self) -> FunctionDef:
    kw = self._advance()   # consume 'function'
    self._fn_depth += 1
    try:
        ...
        body = self._parse_block()
        return FunctionDef(name=name, params=params, body=body,
                           line=kw.line, source_line=kw.source_line)
    finally:
        self._fn_depth -= 1

def _parse_return(self) -> Return:
    kw = self._advance()   # consume 'return'
    if self._fn_depth == 0:
        raise _ParseError(
            kw.line,
            '"return" only works inside a function.',
            kw.source_line,
        )
    ...
```

---

**Module docstring pattern** (`lexer.py` lines 1–8):
```python
"""
Lexer for the Atena transpiler.

Scans Atena source text into a fully-materialised list[Token] with
balanced INDENT/DEDENT tokens, stamped with line, col, and source_line.
Errors are collected through the injected ErrorCollector — the lexer
never raises to the user and never emits a Python traceback.
"""
```

Parser equivalent:
```python
"""
Parser for the Atena transpiler.

Converts a fully-materialised list[Token] (contract A) into a Program AST
(contract B). Implements recursive descent for statements and Pratt
precedence-climbing for expressions. Syntax errors are collected through
the injected ErrorCollector and recovered via synchronization on NEWLINE/
DEDENT boundaries — the parser never raises to the user and never emits a
Python traceback.
"""
```

---

### `tests/test_parser.py` (test file)

**Analog:** `tests/test_lexer.py`

**Module docstring + import block** (`test_lexer.py` lines 1–18):
```python
"""
TDD tests for the Atena Lexer — Phase 1 / Wave 0 RED phase.

Layer 1: golden token snapshots — assert exact token types/values, no errors.
Layer 2: error-path tests — assert key phrase in report(), error line number, no crash.
...
"""

from __future__ import annotations

import pytest

from atena.tokens import TokenType, Token, KEYWORDS
from atena.errors import ErrorCollector
from atena.lexer import Lexer
```

Parser test equivalent:
```python
"""
TDD tests for the Atena Parser — Phase 2 RED phase.

Layer 1 (golden AST snapshots): parse a valid snippet, assert produced node
    equals the expected node literal using @dataclass __eq__.
Layer 2 (error-path tests): feed malformed source, assert exact key phrase in
    ec.report(), error count, and line numbers — no crash, no hang.
Layer 3 (cross-requirement tests): multiple errors collected in one run, no
    infinite loop on malformed input, progress invariant holds.
"""

from __future__ import annotations

import pytest

from atena.tokens import TokenType, Token
from atena.errors import ErrorCollector
from atena.ast_nodes import (
    Program, Assign, Show, Ask, If, While, Repeat,
    FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
    ListLiteral, DictLiteral, IndexAccess, DotAccess,
    ListAdd, ListRemove, Identifier, NumberLiteral,
    StringLiteral, BoolLiteral,
)
from atena.lexer import Lexer
from atena.parser import Parser
```

---

**Helper function pattern** (`test_lexer.py` lines 21–25):
```python
def _lex(source: str) -> tuple[list[Token], ErrorCollector]:
    """Helper: lex source and return (tokens, errors) for inspection."""
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    return tokens, ec
```

Parser test helper — chains through the lexer (parser consumes real tokens):
```python
def _parse(source: str) -> tuple[Program, ErrorCollector]:
    """Helper: lex + parse source and return (program_ast, errors) for inspection."""
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    program = Parser(tokens, ec).parse()
    return program, ec
```

Chaining through the lexer is correct: the parser's input contract is a `list[Token]` produced by the lexer. Tests that need to verify the parser in isolation from the lexer can construct `list[Token]` directly; integration tests through `_parse()` are the primary pattern.

---

**Layer 1 — Golden AST snapshot pattern** (`test_lexer.py` lines 33–67, adapted):

Lexer uses type-set membership assertions:
```python
def test_L1_all_token_types():
    tokens, ec = _lex(source)
    types_found = {t.type for t in tokens}
    assert TokenType.STRING in types_found
    assert ec.is_empty()
```

Parser Layer 1 uses `@dataclass` `__eq__` for node equality — the entire point of using `@dataclass` nodes (ARCHITECTURE.md Pattern 8):
```python
def test_P1_assign_simple():
    """'x = 5' produces Assign(name='x', value=NumberLiteral(value=5)) on line 1."""
    program, ec = _parse("x = 5\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert stmt.name == "x"
    assert isinstance(stmt.value, NumberLiteral)
    assert stmt.value.value == 5
    assert stmt.line == 1
```

For compound nodes the complete equality assertion works because `@dataclass` `__eq__` recurses:
```python
def test_P1_binop_precedence():
    """'2 + 3 * 4' produces BinOp('+', NumberLiteral(2), BinOp('*', ...)) — * binds tighter."""
    program, ec = _parse("x = 2 + 3 * 4\n")
    assert ec.is_empty()
    assign = program.statements[0]
    assert isinstance(assign.value, BinOp)
    assert assign.value.op == "+"
    assert isinstance(assign.value.right, BinOp)
    assert assign.value.right.op == "*"
```

---

**Layer 2 — Error-path pattern** (`test_lexer.py` lines 238–327):
```python
def test_L8_unterminated_string():
    """An unterminated string literal produces an error on line 1 without crashing."""
    _, ec = _lex('"hello\n')
    assert not ec.is_empty()
    report = ec.report()
    assert "Error on line 1" in report

def test_L8_colon_offramp():
    """A trailing colon produces the 'colons' off-ramp error on line 1."""
    _, ec = _lex("if x > 1:\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "colons" in report
    assert "Error on line 1" in report
```

Parser equivalent Layer 2 — assert key phrase in `ec.report()` + line number:
```python
def test_P2_def_redirect():
    """'def greet()' produces the 'function' redirect error on line 1."""
    _, ec = _parse("def greet()\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "function" in report
    assert "Error on line 1" in report

def test_P2_top_level_return():
    """'return x' at top level produces the 'inside a function' error on line 1."""
    _, ec = _parse("return x\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "inside a function" in report
    assert "Error on line 1" in report

def test_P2_eq_as_assignment_redirect():
    """'x == 5' as a statement produces the '=' vs '==' redirect error."""
    _, ec = _parse("x == 5\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "==" in report or "save a value" in report
```

---

**Layer 3 — Cross-requirement / collect-all tests** (`test_lexer.py` lines 332–402):
```python
def test_Lx_multiple_errors_collected():
    """An unterminated string on line 1 and a decimal on line 2 are both collected."""
    source = '"hello\nx = 3.5\n'
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "Error on line 1" in report
    assert "Error on line 2" in report

def test_Lx_offramp_no_infinite_loop():
    """A single-quote and decimal together return without hanging and collect errors."""
    source = "x = 'abc'; y = 3.5\n"
    _, ec = _lex(source)
    assert not ec.is_empty()
```

Parser equivalent Layer 3 — error count assertion + progress invariant:
```python
def test_Px_three_bad_statements_three_errors():
    """Three syntactically bad statements produce exactly 3 errors (one per bad line), not per-token spam."""
    source = "def foo()\nelif x\nfor i in items\n"
    _, ec = _parse(source)
    # Exactly 3 errors collected: one per bad statement (sync recovery).
    report = ec.report()
    error_count = report.count("Error on line")
    assert error_count == 3

def test_Px_no_infinite_loop_on_malformed():
    """Heavily malformed source terminates and returns without hanging."""
    source = "== == ==\n!= !=\n"
    program, ec = _parse(source)
    # If we reach here, no infinite loop. The progress invariant held.
    assert not ec.is_empty()
```

---

## Shared Patterns

### ErrorCollector injection (apply to `parser.py`)

**Source:** `src/atena/lexer.py` lines 19–24
**Apply to:** `Parser.__init__`
```python
def __init__(self, source: str, errors: ErrorCollector) -> None:
    ...
    self._errors = errors           # injected — never instantiate internally
```
The parser constructor must accept `errors: ErrorCollector` as its second parameter and store it as `self._errors`. The planner must never write `ErrorCollector()` inside `parser.py`.

---

### Error reporting — add only, never format envelope (apply to `parser.py`)

**Source:** `src/atena/lexer.py` lines 112–119 (representative)
**Apply to:** every error-reporting site in `parser.py`
```python
self._errors.add(
    self._line,          # parser uses: tok.line (from triggering token)
    "plain English message without 'Error on line N:' prefix",
    source_line,         # parser uses: tok.source_line
)
```
The `"Error on line {N}: … → {source_line}"` envelope is `errors.py`'s responsibility. The parser supplies only `line`, `message`, `source_line`.

---

### `from __future__ import annotations` (apply to all new files)

**Source:** `src/atena/lexer.py` line 10, `tests/test_lexer.py` line 14
**Apply to:** `src/atena/parser.py` and `tests/test_parser.py`
```python
from __future__ import annotations
```
All existing source and test files use this. It enables PEP 563 postponed evaluation of annotations, required for forward references in type hints (e.g., `Node | None` return types in methods that call each other).

---

### Collect-don't-fail-fast invariant (apply to `parser.py`)

**Source:** `ARCHITECTURE.md` Anti-Pattern 3, `PITFALLS.md` §12/13
**Apply to:** `_parse_statement()` and `_synchronize()`

The lexer implements this by never raising — it calls `self._errors.add()` and `continue`s. The parser uses a narrow internal `_ParseError` exception caught *only* at the statement boundary, then recovers. In both cases the invariant is: **every error-recovery path must consume at least one token** (or reach a sync point that does). A `finally` backstop in `_parse_statement()` enforces this.

---

### Dataclass node equality for test assertions (apply to `tests/test_parser.py`)

**Source:** `src/atena/ast_nodes.py` — all nodes are mutable `@dataclass`, giving free `__eq__` and `__repr__` (ARCHITECTURE.md Pattern 8)
**Apply to:** all Layer 1 golden AST tests

`@dataclass` `__eq__` is recursive. Tests should assert structural equality either field-by-field (more readable for simple nodes) or by direct `==` comparison for small expected trees:
```python
expected = Assign(
    name="x",
    value=NumberLiteral(value=5, line=1, source_line="x = 5"),
    line=1,
    source_line="x = 5",
)
assert program.statements[0] == expected
```
Both assertion styles are valid; field-by-field is more maintainable for large nested nodes.

---

### Pure-data module boundary (apply to `parser.py`)

**Source:** `src/atena/tokens.py` lines 1–7, `src/atena/ast_nodes.py` lines 1–18 (module docstrings)
**Apply to:** `src/atena/parser.py`

`tokens.py` and `ast_nodes.py` import nothing from siblings. `parser.py` may import `tokens`, `ast_nodes`, and `errors` — but must not import `lexer`, `analyzer`, or `codegen`. This keeps the phase boundary clean and prevents circular imports.

---

## No Analog Found

No files in Phase 2 are without a match. Both files have strong analogs in the codebase:

| File | Analog Quality | Note |
|------|---------------|-------|
| `src/atena/parser.py` | role-match | Lexer is same pipeline-phase shape; key difference is internal `_ParseError` control flow (absent in lexer) and Pratt expression table (new pattern not in lexer). Planner should reference ARCHITECTURE.md Pattern 5/6/7 for the Pratt and block-parsing sub-patterns that have no lexer equivalent. |
| `tests/test_parser.py` | exact | Three-layer convention, helper pattern, assertion style all carry over directly from `test_lexer.py`. |

---

## Sub-patterns Without Codebase Analog (use ARCHITECTURE.md / PITFALLS.md instead)

These patterns are required by Phase 2 but do not exist anywhere in the current codebase. The planner must source them from the research docs rather than existing code:

| Sub-pattern | Source | Where in Research |
|-------------|--------|-------------------|
| Pratt expression loop with `_BINARY_BP` table | `ARCHITECTURE.md` Pattern 5 | Pattern 5 code example (lines 213–229) |
| `_parse_block()` INDENT…DEDENT consumption | `ARCHITECTURE.md` Pattern 6 | Pattern 6 code example (lines 236–246) |
| `_synchronize()` on NEWLINE/DEDENT | `ARCHITECTURE.md` Pattern 7 | Pattern 7 code example (lines 258–274) |
| `_parse_postfix()` tight loop for `[]`/`.`/`()` | `PITFALLS.md` §9 | Pitfall 9 "How to avoid" section |
| Unary `-` vs binary `-` nud/led split | `PITFALLS.md` §7 | Pitfall 7 "How to avoid" section |
| Progress-invariant backstop (loop guard) | `PITFALLS.md` §13 | Pitfall 13 "How to avoid" section |

---

## Metadata

**Analog search scope:** `src/atena/` (lexer.py, errors.py, tokens.py, ast_nodes.py), `tests/` (test_lexer.py, test_tokens.py, conftest.py)
**Files scanned:** 7
**Pattern extraction date:** 2026-06-14
