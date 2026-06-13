---
phase: 01-lexer
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/atena/lexer.py
  - tests/test_lexer.py
findings:
  critical: 1
  warning: 4
  info: 4
  total: 9
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the Atena lexer (`src/atena/lexer.py`) and its TDD suite (`tests/test_lexer.py`) against the phase contract: single-pass scanner, balanced INDENT/DEDENT, collect-all-errors (never fail-fast / never raise to the user), and plain-English teaching messages with line + offending source line.

The always-make-progress invariant holds (every dispatch branch consumes at least one character or the loop advances on `\n`), the indent-stack pop loop terminates correctly (stack is seeded with `[0]` and shrinks each iteration), the EOF drain is balanced, and the existing 29 tests pass. However, **passing tests are not evidence of correctness here** — the suite exercises only LF-terminated, ASCII source, leaving three real defect classes untested.

The most serious finding is a direct violation of the project's central promise ("the learner never sees a Python stack trace"): the lexer accepts non-ASCII Unicode digits as `NUMBER` tokens, which are not valid Python integer literals and will surface as a Python `SyntaxError` at codegen. A second correctness defect breaks CRLF files entirely (spurious unexpected-character error on every line). A third weakens the collect-all-errors teaching guarantee (an unclosed brace permanently suppresses the colon off-ramp file-wide).

## Critical Issues

### CR-01: Unicode digits accepted as NUMBER, producing invalid Python (stack trace leak)

**File:** `src/atena/lexer.py:245-281`
**Issue:** The integer scanner gates on `self._current().isdigit()`. Python's `str.isdigit()` returns `True` for non-ASCII digit characters (Arabic-Indic `١٢٣`, etc.). Source like `y = ١٢٣` is tokenized as `NUMBER '١٢٣'`. That value is emitted verbatim and will reach code generation, where `ast.parse("١٢٣")` raises `SyntaxError: invalid character '١' (U+0661)`. This is precisely the failure mode the project forbids — a Python stack trace reaching a learner — and it is a silent acceptance bug (no error collected, scanning reports clean). The decimal off-ramp path (line 248, 260) has the same `isdigit()` weakness, and the off-ramp message even renders `try 3 or 4 instead of ٣.٥` via `int()` coercing the Unicode digits, masking how broken the input is.

Verified:
```
y = ١٢٣  ->  NUMBER '١٢٣', no error
ast.parse('١٢٣')  ->  SyntaxError: invalid character '١' (U+0661)
```

**Fix:** Restrict the integer scanner to ASCII digits explicitly, and route any non-ASCII digit through the unexpected-character path so it is collected as a plain-English error instead of silently passing:
```python
def _is_ascii_digit(c: str | None) -> bool:
    return c is not None and c in '0123456789'

# in the integer branch:
if ch in '0123456789':           # was: ch.isdigit()
    ...
    while _is_ascii_digit(self._current()):   # was: self._current().isdigit()
        ...
```
Apply the same ASCII-only guard to the decimal off-ramp's fractional-digit loop (lines 253-263). A Unicode digit that reaches the bottom dispatch will then be reported by the generic unexpected-character handler (line 448), which is correct collect-and-continue behavior.

## Warnings

### WR-01: CRLF line endings produce a spurious error on every line

**File:** `src/atena/lexer.py:22, 221, 495`
**Issue:** `self._lines = source.splitlines(keepends=True)` keeps `\r\n`. `source_line = raw_line.rstrip('\n')` (line 221) and `raw_line.rstrip('\n')` (line 495) strip only `\n`, leaving a trailing `\r` in the content the scanner walks. The `\r` is not whitespace per the mid-line check (`ch in (' ', '\t')`) and falls through to the generic unexpected-character handler. Result: a Windows-saved `.atena` file reports `I don't know what "\r" means` on every single line, making the tool unusable on CRLF input.

Verified:
```
'show x\r\ny = 1\r\n'  ->  2 errors: I don't know what "\r" means ...
```

**Fix:** Normalize line endings once at construction, or strip `\r` alongside `\n`:
```python
# Option A (cleanest): normalize up front in __init__
self._source = source.replace('\r\n', '\n').replace('\r', '\n')
self._lines = self._source.splitlines(keepends=True)

# Option B: strip both when deriving source_line / scanning content
source_line = raw_line.rstrip('\r\n')   # lines 221 and 495
```
Option A is preferable because `self._source` is also indexed directly by the scanner via `self._pos`, so the `\r` must be removed from the scanned buffer, not just from `source_line`.

### WR-02: Unclosed brace permanently suppresses the colon off-ramp file-wide

**File:** `src/atena/lexer.py:30, 396-408, 421-429`
**Issue:** `_brace_depth` is incremented on `{` and decremented on `}`, and the colon off-ramp at line 423 only fires when `_brace_depth == 0`. `_brace_depth` is never reset per line and an unterminated `{` is never validated. A learner who writes a stray `x = {` (a typo, never closed) silently disables the "Atena doesn't use colons" teaching error for the entire remainder of the file. Because the depth persists across lines with no upper bound on scope, a single unbalanced brace defeats one of the off-ramps the collect-all-errors design depends on.

Verified:
```
'x = {\nif y > 1:\n'  ->  no errors collected (colon off-ramp suppressed)
```

**Fix:** Constrain dict/set-literal colon suppression to a single logical line (a v1.0 dict literal is single-line), e.g. reset `self._brace_depth = 0` at the start of each content line in `tokenize()` before `_scan_line`, and/or emit an "unclosed `{`" error at NEWLINE when `_brace_depth > 0`. Resetting per line also prevents the colon-suppression scope from leaking past the literal.

### WR-03: Decimal off-ramp suggestion mangles leading zeros

**File:** `src/atena/lexer.py:264-271`
**Issue:** The off-ramp computes `low = int(integer_part)` and suggests `try {low} or {high}`. For `007.5`, `int("007")` is `7`, so the learner is told `try 7 or 8 instead of 007.5` — the suggested numbers don't visually match what they typed, which is confusing in a tool whose value proposition is clarity for non-programmers. (This is also the path that silently coerces Unicode digits; see CR-01.)

Verified:
```
'x = 007.5'  ->  try 7 or 8 instead of 007.5
```

**Fix:** Derive the suggestion from the literal text, not from `int()`, or normalize the displayed input consistently:
```python
try:
    low = int(integer_part)
    high = low + 1
    # show the normalized integer the learner should use, consistently:
    self._errors.add(self._line,
        f'Atena works with whole numbers only — try {low} or {high} instead of {low}.{fraction_part}.',
        source_line)
```

### WR-04: Non-ASCII letters silently accepted as identifiers

**File:** `src/atena/lexer.py:233-242`
**Issue:** The identifier scanner gates on `ch.isalpha()` / `self._current().isalnum()`, which accept the full Unicode letter/alphanumeric range. Most map to valid Python identifiers (`café` is fine), so this is lower-severity than CR-01, but it is an undocumented widening of the v1.0 spec (plain-English ASCII keywords/identifiers) and pairs with the Unicode-digit bug: `isalnum()` also admits Unicode digits mid-identifier. For a teaching language, accepting `café`/`ⁿ`/`ª` as identifiers without a deliberate decision is a robustness/spec-drift concern.

**Fix:** Decide and enforce the identifier charset explicitly. If ASCII-only is intended:
```python
def _is_ident_start(c): return c is not None and (c.isascii() and (c.isalpha() or c == '_'))
def _is_ident_cont(c):  return c is not None and (c.isascii() and (c.isalnum() or c == '_'))
```
Non-ASCII starts then route to the unexpected-character handler and are collected as friendly errors.

## Info

### IN-01: Dead parameter `start_col` in `_scan_line`

**File:** `src/atena/lexer.py:209, 503`
**Issue:** `_scan_line(self, raw_line, start_col)` is called with `width` as `start_col` (line 503), but the parameter is never read — every token branch reassigns `start_col = self._col` locally before use. The parameter is misleading dead state.
**Fix:** Drop the `start_col` parameter from the signature and the call site.

### IN-02: `_advance()` and `_peek()` return values rarely used; `_advance` return is dead in most call sites

**File:** `src/atena/lexer.py:49-64`
**Issue:** `_advance()` returns the consumed character, but nearly every call (e.g. lines 229, 237, 257, 287, 307) discards it and re-reads via `self._current()`. The return value contract adds noise. Not a bug, but a readability/consistency smell in a teaching codebase meant to be read.
**Fix:** Either consistently use the returned char (e.g. `buf.append(self._advance())`) or make `_advance()` return `None` and document it as side-effect-only. Pick one pattern and apply it throughout.

### IN-03: Doc/comment count mismatch for keyword set

**File:** `src/atena/tokens.py:94`, `tests/test_lexer.py:194-202`
**Issue:** The `KEYWORDS` comment says "Full set ... (18 keywords)" but the dict (and the test `test_L6_all_19_keywords`) define 19. Stale comment, harmless but confusing for the next maintainer.
**Fix:** Update the comment in `tokens.py:94` to read 19.

### IN-04: Test suite has no coverage for CRLF, Unicode input, or brace-depth leakage

**File:** `tests/test_lexer.py` (whole file)
**Issue:** All 29 tests use LF-terminated ASCII source. The three defects above (CR-01, WR-01, WR-02) are entirely invisible to the current suite, which is why it is green despite the bugs. The collect-all-errors and "never leak a Python error" guarantees are the project's core differentiators and deserve explicit adversarial tests.
**Fix:** Add regression tests: (a) `'show x\r\ny = 1\r\n'` asserts `ec.is_empty()`; (b) `'y = ١٢٣\n'` asserts a collected error (or, post-fix, an unexpected-character error) and that no emitted `NUMBER` value contains non-ASCII; (c) `'x = {\nif y > 1:\n'` asserts the colon off-ramp still fires.

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
