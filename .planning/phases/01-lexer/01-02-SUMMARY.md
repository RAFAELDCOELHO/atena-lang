---
phase: 01-lexer
plan: 02
subsystem: lexer
tags: [tdd, green-phase, lexer, character-scanner, LEX-01, LEX-05, LEX-06, LEX-07, LEX-08]
dependency_graph:
  requires: [Plan 01-01 (RED tests + stub), Phase 00 (tokens.py, errors.py contracts)]
  provides: [src/atena/lexer.py (working core scanner — LEX-01/05/06/07/08 GREEN)]
  affects: [Plan 01-03 (indentation engine wraps this scanner)]
tech_stack:
  added: []
  patterns:
    - Per-character dispatch loop with explicit always-make-progress guarantee
    - Maximal-munch operator resolution (= vs ==, < vs <=, > vs >=)
    - Brace-depth tracking to distinguish block colons from dict-literal colons
    - ErrorCollector.add() for all error paths — no exceptions escape
    - KEYWORDS.get(word, TokenType.IDENTIFIER) for keyword/identifier classification
key_files:
  created: []
  modified:
    - src/atena/lexer.py
decisions:
  - "Brace depth (_brace_depth) added to __init__ to allow colon inside dict/set literals without triggering the colon off-ramp — test_L1_all_token_types uses {\"key\": 1} which requires this"
  - "Decimal off-ramp emits the integer part as a NUMBER token after reporting the error — consistent with collect-and-continue; scanning resumes past the fraction"
  - "Colon inside braces (_brace_depth > 0) is silently consumed without an error — it is valid Atena dict syntax; the off-ramp fires only at depth 0 (block-level colon)"
metrics:
  duration: 8 min
  completed: 2026-06-13
  tasks_completed: 1
  files_created: 1
  files_modified: 1
---

# Phase 1 Plan 2: Core Character Scanner Summary

**One-liner:** Core character scanner with maximal-munch operators, keyword/identifier classification, string/number scanning, four teaching off-ramps, and a brace-depth guard for dict-literal colons — 19 LEX-01/05/06/07/08 tests turned GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement core character scanner in src/atena/lexer.py | 1dadf2c | src/atena/lexer.py (280 lines) |

## What Was Built

**src/atena/lexer.py** — Replaced the `NotImplementedError` stub with a complete per-character scanner:

**Private helpers:**
- `_current()` — returns the character at `self._pos` without consuming it
- `_peek()` — returns the character one position ahead without consuming it
- `_advance()` — consumes one character; increments `self._line` and resets `self._col` on `\n`
- `_emit_token(tok_type, value, col, source_line)` — constructs and appends a frozen `Token`

**`_scan_line(raw_line)`** — main per-line scanner:
- Skips blank and comment-only lines (advances past the line without emitting tokens)
- Skips leading whitespace (indentation stub — Plan 03 replaces with real engine)
- Dispatches on each character until `\n` or end of source
- Every dispatch branch calls `_advance()` at least once (always-make-progress invariant)
- Tracks `_brace_depth` across `{` and `}` to avoid triggering the colon off-ramp inside dict literals

**`tokenize()`** — outer loop iterates `self._lines`, calls `_scan_line()` for each, emits EOF.

**Character dispatch coverage:**
- Whitespace (mid-line space/tab): skip
- Identifiers/keywords: collect alphanumeric+`_`, `KEYWORDS.get(word, IDENTIFIER)`
- Integers: collect digits; decimal off-ramp if digit-dot-digit (collects fraction, emits error, emits integer part)
- Double-quoted strings: collect until closing `"` or `\n`; unterminated-string error on `\n`
- Single-quoted strings: off-ramp error; scan to closing `'` or end of line
- `=` / `==`: maximal-munch → ASSIGN or COMPARISON
- `!=`, `<`, `>`, `<=`, `>=`: COMPARISON tokens
- `+`, `-`, `*`, `/`: OPERATOR tokens
- `(`, `)`, `[`, `]`, `{`, `}`, `,`, `.`: bracket/punctuation tokens
- `:` (at brace depth 0): colon off-ramp; consumed silently inside braces
- `;`: semicolon off-ramp
- `#`: skip to end of line
- Anything else: generic unexpected-character error + `_advance()`

## Verification Results

```
python3 -m pytest tests/test_lexer.py -k "L1 or L5 or L6 or L7 or L8 or Lx" --tb=no -q
  → 19 passed, 10 deselected in 0.01s

python3 -m pytest tests/ --tb=no -q
  → 8 failed (L2/L3-deep/L4 — intentional RED for Plan 03), 79 passed

Phase 0 regression: NONE (58 tests still green)
grep -v "^#" src/atena/lexer.py | grep -c "def _advance"  → 1
grep -v "^#" src/atena/lexer.py | grep -c "_advance()"    → 36 (> 10 required)
```

**Intentionally RED tests (Plan 03 scope):**
- `test_L2_*` — INDENT/DEDENT/EOF drain (indentation engine not yet built)
- `test_L3_deep_comment_no_indent_effect` — requires indentation engine to skip comment-only deeply-indented lines
- `test_L4_*` — mixed tabs/spaces, staircase-dedent, over-indent, ragged width errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Colon off-ramp triggered inside dict literals**
- **Found during:** Task 1 — `test_L1_all_token_types` failed because the test source includes `{"key": 1}` which contains a colon
- **Issue:** The plan's behavior block described colon as an unconditional off-ramp, but `test_L1_all_token_types` asserts `ec.is_empty()` while using a dict literal with a colon. The off-ramp must only fire at block scope (depth 0), not inside `{}`
- **Fix:** Added `self._brace_depth: int = 0` to `__init__`; `{` increments it, `}` decrements it; `:` calls `_errors.add()` only when `_brace_depth == 0`
- **Files modified:** src/atena/lexer.py
- **Commit:** 1dadf2c (included in main task commit)

## Known Stubs

- Leading-whitespace skip in `_scan_line` is a no-op stub — Plan 03 replaces it with the real indentation engine (INDENT/DEDENT/NEWLINE emission)
- `tokenize()` does not emit `NEWLINE` tokens — Plan 03 adds this when processing `\n` at end of non-blank lines

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

Threat mitigations verified:
- **T-01-02-01 (DoS / infinite loop):** 36 `_advance()` calls confirmed; `test_Lx_offramp_no_infinite_loop` passes
- **T-01-02-02 (unterminated string):** `test_L8_unterminated_string` passes — error collected, no exception escapes
- **T-01-02-03 (unexpected char):** generic catch-all calls `_advance()` before looping; `test_L8_unexpected_char` passes
- **T-01-02-04 (decimal off-ramp false positive):** off-ramp fires only on digit-dot-digit; a DOT after an identifier emits DOT token, not an error

## Self-Check: PASSED

- src/atena/lexer.py exists: FOUND
- Commit 1dadf2c exists: FOUND
- 19 target tests GREEN: CONFIRMED
- 58 Phase 0 tests still passing: CONFIRMED (verified with --ignore=tests/test_lexer.py → 58 passed)
- 8 intentional RED tests (L2/L3-deep/L4): CONFIRMED (Plan 03 scope)
- `_advance()` call count > 10: CONFIRMED (36)
