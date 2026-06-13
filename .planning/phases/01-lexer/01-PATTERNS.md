# Phase 1: Lexer - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 2 (src/atena/lexer.py, tests/test_lexer.py — both new)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/atena/lexer.py` | service (pipeline phase) | transform (str → list[Token]) | `src/atena/errors.py` | role-match (same: stdlib-only, injected dependency, dataclass-heavy, collect-not-raise) |
| `tests/test_lexer.py` | test | transform / error-path | `tests/test_errors.py` + `tests/test_tokens.py` | exact (same naming convention, same assert style, same RED-phase docstring, same import pattern) |

---

## Pattern Assignments

### `src/atena/lexer.py` (pipeline phase, str → list[Token])

**Primary analog:** `src/atena/errors.py`
**Secondary analog:** `src/atena/tokens.py` (shows how the output contracts are used)

---

#### Imports pattern

Copy from `src/atena/errors.py` lines 1-16 and `src/atena/tokens.py` lines 1-14.

Concrete import block for `lexer.py`:

```python
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
```

**Rules extracted from both analog modules:**
- Always lead with `from __future__ import annotations` (both `tokens.py` line 10, `errors.py` line 12).
- Import only stdlib and sibling `atena.*` modules — zero third-party dependencies.
- Do NOT import `atena.errors` from `tokens.py` or vice versa (circular dependency; `tokens.py` imports nothing sibling at all). `lexer.py` is the first module that imports from both.

---

#### Module-level docstring pattern

**Analog:** `src/atena/errors.py` lines 1-11

```python
"""
Error collection and reporting for the Atena transpiler.

This is the single source of truth for the error format:
  Error on line {N}: {plain English message}
    → {offending source line}

ErrorCollector is injected into each pipeline phase and accumulates
errors across the entire run. The pipeline gates codegen on .is_empty().
"""
```

Mirror this style: opening blank line, one-sentence summary, brief contract note. Do not mention Python internals (no "tokenizer", no "AST") in the module docstring's prose that a learner might accidentally see.

---

#### Class constructor / dependency-injection pattern

**Analog:** `src/atena/errors.py` lines 29-33 (`ErrorCollector.__init__`)

```python
class ErrorCollector:
    """Accumulates plain-English errors across all transpiler phases."""

    def __init__(self) -> None:
        self._records: list[_ErrorRecord] = []
```

For `Lexer`, the constructor takes `(source: str, errors: ErrorCollector)` — the injected `ErrorCollector` goes in as `self._errors`, matching the `_`-prefixed private field convention used throughout `errors.py`.

```python
class Lexer:
    def __init__(self, source: str, errors: ErrorCollector) -> None:
        self._source = source
        self._errors = errors        # injected — never instantiate internally
        self._lines = source.splitlines(keepends=True)
        self._pos = 0
        self._line = 1               # 1-based (matches Token.line contract)
        self._col = 0                # 0-based (matches Token.col contract)
        self._indent_stack: list[int] = [0]
        self._indent_char: str | None = None   # ' ' or '\t', pinned on first indent
        self._indent_unit: int | None = None   # width of one step, pinned on first indent
        self._tokens: list[Token] = []
```

**Key rule:** `ErrorCollector` is ALWAYS injected, never constructed inside the `Lexer`. The Phase 0 architecture boundary is: `Lexer` calls `self._errors.add(...)`, the driver (Phase 5) calls `errors.is_empty()` between phases.

---

#### ErrorCollector.add() call pattern

**Analog:** `src/atena/errors.py` lines 35-37 (the `add()` method signature)

```python
def add(self, line: int, message: str, source_line: str) -> None:
    """Append a new error record (duplicates are collapsed at report time)."""
    self._records.append(_ErrorRecord(line=line, message=message, source_line=source_line))
```

The lexer calls this as:

```python
self._errors.add(
    self._line,
    "Plain-English message here — no Python jargon.",
    source_line,      # the full raw text of the physical line
)
```

**Three invariants (derived from errors.py and CONTEXT.md):**
1. `line` is always `self._line` (1-based integer, advances as the lexer walks source).
2. `message` is plain English — no Python type names, no internal terms like "token", "DEDENT", "lexer".
3. `source_line` is the full text of the offending physical line, not a substring.

---

#### Token construction pattern

**Analog:** `src/atena/tokens.py` lines 63-86 (the `Token` dataclass definition)

```python
@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    col: int
    source_line: str
```

The lexer constructs `Token` objects via keyword arguments (matching the test style in `test_tokens.py` lines 24-30):

```python
Token(
    type=TokenType.NUMBER,
    value="42",
    line=3,
    col=0,
    source_line="x = 42",
)
```

For structural tokens (INDENT, DEDENT, NEWLINE, EOF) where `value` carries no semantic content, use `""` or the structural marker as value:

```python
# Structural token — value is empty string; type is the signal
Token(type=TokenType.INDENT, value="", line=self._line, col=0, source_line=source_line)
Token(type=TokenType.EOF, value="", line=self._line, col=0, source_line="")
```

---

#### KEYWORDS lookup pattern

**Analog:** `src/atena/tokens.py` lines 97-117 (the `KEYWORDS` dict)

The KEYWORDS dict already exists and maps every Atena reserved word to `TokenType.KEYWORD`. The lexer uses it for identifier-vs-keyword resolution:

```python
word = ''.join(buf)
tok_type = KEYWORDS.get(word, TokenType.IDENTIFIER)
self._emit_token(tok_type, word, start_col, source_line)
```

Never re-define KEYWORDS in `lexer.py`. Never write an `if/elif` chain for keywords. Import and use.

---

#### Private helper method style

**Analog:** `src/atena/errors.py` lines 43-85 (internal `report()` method, private `_ErrorRecord`)

The analog shows: all internal state is `_`-prefixed; helper methods are also `_`-prefixed; the public API surface is minimal (`tokenize()` for the lexer, matching `report()` / `is_empty()` / `add()` for the error collector).

For the lexer, the expected method decomposition (following the RESEARCH.md architecture diagram):

```
Lexer.tokenize()               # public — main entry point, returns list[Token]
Lexer._scan_line(raw_line)     # private — handles one physical line
Lexer._handle_indentation(width, source_line)  # private — stack + uniform-step
Lexer._drain_at_eof()          # private — EOF NEWLINE + DEDENT drain + EOF token
Lexer._advance()               # private — move pos/col/line forward by one char
Lexer._current()               # private — current char without advancing
Lexer._peek()                  # private — next char without advancing (for maximal-munch)
Lexer._emit(tok_type, value, col, source_line)  # private — append Token to self._tokens
```

---

### `tests/test_lexer.py` (test file, golden + error-path)

**Primary analog:** `tests/test_errors.py`
**Secondary analog:** `tests/test_tokens.py`

---

#### File header pattern

**Analog:** `tests/test_tokens.py` lines 1-11 and `tests/test_errors.py` lines 1-17

```python
"""Tests for the Token data contract (tokens.py).

Plan 00-03 — RED phase: all tests must FAIL against the stub implementation.
"""

from __future__ import annotations

import sys

import pytest
```

and:

```python
"""
TDD tests for ErrorCollector — the diagnostics spine.

All tests are written BEFORE the implementation (RED phase).
They assert exact string output as specified in PLAN 00-02.
"""

from __future__ import annotations

import inspect
import re

import pytest

from atena.errors import ErrorCollector, suggest, ATENA_KEYWORDS
```

For `test_lexer.py`:

```python
"""
TDD tests for the Atena Lexer — Phase 1.

All tests are written BEFORE the implementation (RED/RED-GREEN cycle).
Layer 1: golden token snapshots (exact list[Token] assertions).
Layer 2: error-path tests (exact message, count, line number order).
"""

from __future__ import annotations

import pytest

from atena.tokens import TokenType, Token, KEYWORDS
from atena.errors import ErrorCollector
from atena.lexer import Lexer
```

**Rules extracted:**
- `from __future__ import annotations` always first.
- Imports from `atena.*` at module level (not inside test functions), EXCEPT where testing import-time behavior specifically.
- `test_tokens.py` imports inside test functions (lines 15, 22, etc.) — that is a style choice for that module's isolation tests. For `test_lexer.py`, since every test needs `Lexer`, import at module level.

---

#### Test function naming convention

**Analog:** `tests/test_tokens.py` lines 13, 20, 37, 46, 53, 66, 75

```
test_T1_token_type_has_19_members
test_T2_token_construction_and_field_access
test_T3_token_equality_via_dataclass
test_T4_keywords_show_and_function
test_T5_keywords_has_19_entries
test_T6_user_identifiers_not_in_keywords
test_T7_token_repr_contains_field_names
```

**Analog:** `tests/test_errors.py` lines 22, 28, 38, 50, 69, 86, 102, 117, 142, 165, 177

```
test_empty_collector_is_empty
test_empty_collector_report_is_empty_string
test_single_error_format
test_multi_error_sort_order
test_all_three_errors_appear
test_dedup_identical_error
...
```

`test_tokens.py` uses `test_T{N}_` prefix tied to requirement numbers. `test_errors.py` uses descriptive names without a prefix. The RESEARCH.md test map specifies:

```
test_L1_all_token_types
test_L1_keyword_recognition
test_L2_indent_dedent_balanced
test_L4_mixed_tabs_spaces_error
test_L8_decimal_offramp
...
```

**Rule:** Use the `test_L{req_id}_{description}` prefix pattern from RESEARCH.md (matching the `test_T{N}_` convention from `test_tokens.py`). The prefix ties each test directly to the requirement ID it covers, which mirrors the `test_T{N}_` convention used in `test_tokens.py`.

---

#### Test function body pattern — golden snapshot

**Analog:** `tests/test_tokens.py` lines 20-34

```python
def test_T2_token_construction_and_field_access():
    """Token constructs without error and fields are readable."""
    from atena.tokens import Token, TokenType

    token = Token(
        type=TokenType.NUMBER,
        value="42",
        line=3,
        col=0,
        source_line="x = 42",
    )
    assert token.line == 3
    assert token.value == "42"
    assert token.col == 0
    assert token.source_line == "x = 42"
```

For `test_lexer.py`, the golden pattern uses a helper that returns `(tokens, errors)`:

```python
def _lex(source: str) -> tuple[list[Token], ErrorCollector]:
    """Helper: lex source and return (tokens, errors) for inspection."""
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    return tokens, ec


def test_L5_assign_token():
    """'=' produces an ASSIGN token (not COMPARISON)."""
    tokens, ec = _lex("x = 10\n")
    assert ec.is_empty()
    assign = [t for t in tokens if t.type == TokenType.ASSIGN]
    assert len(assign) == 1
    assert assign[0].value == "="


def test_L5_eq_comparison_token():
    """'==' produces a COMPARISON token."""
    tokens, ec = _lex("x == 10\n")
    assert ec.is_empty()
    comp = [t for t in tokens if t.type == TokenType.COMPARISON]
    assert len(comp) == 1
    assert comp[0].value == "=="
```

**Rules extracted:**
- One assert-cluster per test. Each test covers one interesting property, not multiple unrelated assertions.
- `ec.is_empty()` is asserted in golden tests to confirm no spurious errors.
- Use plain `assert` (not `self.assert*`). No test classes — all top-level functions.

---

#### Test function body pattern — error-path

**Analog:** `tests/test_errors.py` lines 38-45 (single-error format test)

```python
def test_single_error_format() -> None:
    """Single error produces exact canonical format."""
    ec = ErrorCollector()
    ec.add(4, 'I don\'t know what "score" is yet.', "show score")
    expected = 'Error on line 4: I don\'t know what "score" is yet.\n  → show score'
    assert ec.report() == expected
```

For `test_lexer.py`, the error-path pattern:

```python
def test_L8_decimal_offramp():
    """Decimal literal produces a specific plain-English off-ramp error."""
    _, ec = _lex("x = 3.5\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "whole numbers" in report          # key phrase from D-02 message
    assert "Error on line 1" in report


def test_L4_mixed_tabs_spaces_error():
    """Mixed tabs and spaces in indentation produces a plain-English error."""
    source = "if x\n    show y\n\tshow z\n"   # spaces then tab
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "tabs and spaces" in report
    assert "Error on line 3" in report
```

**Rules extracted from `test_errors.py`:**
- Assert the exact key phrase, not the full sentence — this gives the implementation wording flexibility within the locked voice while still pinning the substance (e.g. `"whole numbers"` from the D-02 draft).
- Assert error count via `ec.is_empty()` first (binary check), then assert presence of `"Error on line {N}"` to pin line attribution.
- Assert error count more precisely when the "collect-all" guarantee is the point of the test (see `test_all_three_errors_appear` pattern, `test_errors.py` lines 69-79).

---

#### conftest.py fixture pattern

**Analog:** `tests/conftest.py` (currently empty scaffold — lines 1-9)

The RESEARCH.md Wave 0 note says a `make_lexer(source)` fixture may be added. The pattern to follow, if added:

```python
# tests/conftest.py  (append to existing scaffold)
import pytest
from atena.errors import ErrorCollector
from atena.lexer import Lexer


@pytest.fixture
def make_lexer():
    """Factory fixture: make_lexer(source) -> (list[Token], ErrorCollector)."""
    def _factory(source: str):
        ec = ErrorCollector()
        tokens = Lexer(source, ec).tokenize()
        return tokens, ec
    return _factory
```

Alternatively, define `_lex()` as a module-level helper in `test_lexer.py` itself (no fixture needed). The analog tests in `test_tokens.py` and `test_errors.py` do not use fixtures — they construct inline. Either approach is consistent with the codebase style; a module-level helper is simpler and closer to the existing analogs.

---

## Shared Patterns

### ErrorCollector injection
**Source:** `src/atena/errors.py` lines 29-37; `src/atena/tokens.py` (tokens.py imports nothing from errors, proving isolation is intentional)
**Apply to:** `src/atena/lexer.py` constructor

The `ErrorCollector` is always injected. The lexer never calls `ErrorCollector()` inside itself. The driver (Phase 5 `pipeline.py`) owns the `ErrorCollector` lifecycle.

```python
# Pattern: injected, stored as private attribute, called via .add()
def __init__(self, source: str, errors: ErrorCollector) -> None:
    self._errors = errors
    # ...

# Usage inside lexer:
self._errors.add(self._line, "message", source_line)
```

### `from __future__ import annotations`
**Source:** `src/atena/tokens.py` line 10; `src/atena/errors.py` line 12; `tests/test_tokens.py` line 7; `tests/test_errors.py` line 8
**Apply to:** Both `src/atena/lexer.py` and `tests/test_lexer.py`

Always first import, before any stdlib or project imports. Present in all four analog files.

### Plain-English error messages with no Python jargon
**Source:** `tests/test_errors.py` lines 177-199 (the `test_no_jargon_in_errors_py` test)

```python
forbidden = ["token", "AST", "DEDENT", "arity", "NoneType"]
```

The same prohibition applies to all string literals in `lexer.py`. Do not use "token", "INDENT", "DEDENT", "lexer", "parser", "TypeError", or any Python internal term in any user-facing message string. Messages are written to learners, not developers.

### `@dataclass(frozen=True)` for output data
**Source:** `src/atena/tokens.py` lines 63-86

`Token` is frozen — the lexer constructs tokens and appends them to `self._tokens`. The lexer must never try to mutate a `Token` after construction (would raise `FrozenInstanceError`). Construct with all five fields in one call.

### Collect-don't-raise error handling
**Source:** `src/atena/errors.py` lines 35-37; `tests/test_errors.py` lines 69-79

```python
def test_all_three_errors_appear() -> None:
    """report() contains all three Error on line headers."""
    ec = ErrorCollector()
    ec.add(9, "error nine", "src nine")
    ec.add(1, "error one", "src one")
    ec.add(4, "error four", "src four")
    report = ec.report()
    assert "Error on line 1" in report
    assert "Error on line 4" in report
    assert "Error on line 9" in report
```

The lexer mirrors this: `self._errors.add(...)` then continue scanning. Never `raise`. Never `return` early from `tokenize()` on first error (except for a catastrophic internal failure that the driver catches).

---

## No Analog Found

No files fall into this category. Both new files (`lexer.py` and `test_lexer.py`) have close analogs in the Phase 0 modules.

However, the following lexer-specific algorithm excerpts have no direct analog in the codebase (because no scanning code exists yet) and must be built from the RESEARCH.md code examples:

| Algorithm | Source for Pattern |
|-----------|--------------------|
| Indentation stack (Pattern 1) | RESEARCH.md §Pattern 1 (lines 247-264 of 01-RESEARCH.md) |
| Uniform-step validation layer (Pattern 2) | RESEARCH.md §Pattern 2 (lines 266-287) |
| Blank/comment skip before stack (Pattern 3) | RESEARCH.md §Pattern 3 (lines 289-301) |
| Maximal-munch `=`/`==` (Pattern 4) | RESEARCH.md §Pattern 4 (lines 303-318) |
| String scanning + unterminated recovery (Pattern 5) | RESEARCH.md §Pattern 5 (lines 320-343) |
| Four teaching off-ramps (Pattern 6) | RESEARCH.md §Pattern 6 (lines 345-367) |
| EOF drain (Pattern 7) | RESEARCH.md §Pattern 7 (lines 369-383) |

---

## Metadata

**Analog search scope:** `src/atena/`, `tests/`
**Files scanned:** 10 (all `.py` files in both directories)
**Pattern extraction date:** 2026-06-13
