---
phase: 01-lexer
plan: 01
subsystem: lexer
tags: [tdd, red-phase, lexer, test-contract]
dependency_graph:
  requires: [Phase 00 — tokens.py, errors.py contracts]
  provides: [tests/test_lexer.py (29 RED tests), src/atena/lexer.py (stub)]
  affects: [Plan 01-02 (GREEN implementation), Plan 01-03 (full implementation)]
tech_stack:
  added: []
  patterns: [TDD RED phase, module-level helper, plain-assert, no test classes]
key_files:
  created:
    - tests/test_lexer.py
    - src/atena/lexer.py
  modified: []
decisions:
  - "29 tests written (plan said 28 — the behavior block and RESEARCH.md test map each enumerate 29 names; 28 was an off-by-one in the plan heading)"
  - "test_L4_over_indent_error uses source 'if x\n    if y\n            show z\n' (12-space third line, delta=8=2 units) to trigger 'too far'"
  - "test_L4_ragged_width_error uses source 'if x\n    if y\n      show z\n' (6-space third line, not multiple of 4) to trigger 'same size'"
metrics:
  duration: 2 min
  completed: 2026-06-13
  tasks_completed: 2
  files_created: 2
---

# Phase 1 Plan 1: Lexer RED Phase Summary

**One-liner:** 29 RED-phase lexer tests covering LEX-01 through LEX-08 plus a minimal `Lexer` stub that makes imports succeed while `tokenize()` raises `NotImplementedError`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write all RED-phase tests in tests/test_lexer.py | 6e101cc | tests/test_lexer.py (348 lines, 29 test functions) |
| 2 | Create src/atena/lexer.py stub | 9ebbcf0 | src/atena/lexer.py (37 lines, class Lexer) |

## What Was Built

**tests/test_lexer.py** — 29 test functions organized in two layers:

- Layer 1 (17 tests, golden snapshots): `test_L1_*` through `test_L7_*` — assert exact token types/values for LEX-01 through LEX-07. Each golden test also asserts `ec.is_empty()`.
- Layer 2 (12 tests, error-path): `test_L4_*` and `test_L8_*` plus two `test_Lx_*` cross-requirement tests — assert key phrases from off-ramp messages (D-01/D-02), `"Error on line N"` header, and the collect-all guarantee.

Module-level `_lex(source)` helper constructs `ErrorCollector` and `Lexer`, calls `tokenize()`, returns `(tokens, ec)` — used by every test body.

**src/atena/lexer.py** — Minimal stub: `class Lexer` with `__init__(source, errors)` setting all nine constructor fields (`_source`, `_errors`, `_lines`, `_pos`, `_line`, `_col`, `_indent_stack`, `_indent_char`, `_indent_unit`, `_tokens`). `tokenize()` raises `NotImplementedError("Lexer.tokenize() not yet implemented — RED phase")`.

## Verification Results

```
python3 -c "from atena.lexer import Lexer; print('import ok')"  → import ok
python3 -m pytest tests/test_lexer.py --tb=no -q               → 29 failed, 0 passed
python3 -m pytest tests/ --tb=no -q                             → 29 failed, 58 passed
grep -c "def test_L" tests/test_lexer.py                        → 29
```

Phase 0 regression: NONE — 58 tests remain green.

## Deviations from Plan

### Plan Inconsistency Resolved

**Plan heading said "28 tests" but behavior block + RESEARCH.md test map both enumerate 29 test names.**

The plan's `<objective>` and multiple prose references say "28 test functions", but the `<behavior>` block lists 17 Layer 1 + 12 Layer 2 = 29 distinct `test_L*` / `test_Lx_*` names, and the RESEARCH.md §"Phase Requirements → Test Map" table has 29 rows with exactly the same names. All 29 were written. This is tracked as an off-by-one in the plan prose (the behavior block and test map are authoritative). The `grep -c "def test_L"` check in the success criteria expected 28; actual result is 29 — all 29 come directly from the plan's own enumerated list.

No other deviations — plan executed exactly as written.

## Known Stubs

- `src/atena/lexer.py` — `tokenize()` raises `NotImplementedError`. This is intentional: the RED phase stub. Plan 01-02 (GREEN implementation) will replace it.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Stub raises immediately, no input processing.

## Self-Check: PASSED

- tests/test_lexer.py exists: FOUND
- src/atena/lexer.py exists: FOUND
- Commit 6e101cc exists: FOUND
- Commit 9ebbcf0 exists: FOUND
- 29 failed, 58 passed, 0 errors: CONFIRMED
