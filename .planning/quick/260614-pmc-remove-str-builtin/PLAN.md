---
id: 260614-pmc
title: Remove str from analyzer _BUILTIN_HELPERS so source-level str() errors
date: 2026-06-14
branch: feat/generator
status: in_progress
review_ref: WR-01 in .planning/phases/04-code-generator/04-REVIEW.md
---

# Quick Task 260614-pmc: Remove str from _BUILTIN_HELPERS

## Objective

Remove `"str"` from the analyzer's `_BUILTIN_HELPERS` frozenset so that a
SOURCE-level `str(5)` in an Atena program errors with a plain-English teaching
message, while `length` stays a builtin. Rationale (CLAUDE.md core value):
learners never type Python jargon like `str()` — the analyzer auto-injects
coercion, so `"Average: " + avg` is how they write it.

## Single Task (TDD)

### RED — add failing test

In `tests/test_analyzer.py`, add:
1. `test_A2_source_str_call_errors` — bare `str(5)` (no user `function str`)
   → ErrorCollector NON-empty with the undefined-function message.
2. `test_A1_injected_coercion_still_works` — `x = 5\nshow "v: " + x\n`
   → analyzer injects `str()` coercion on the BinOp right-hand side with no
   errors. (Guard: proves injected coercion is unaffected by the builtin removal.)

Run → test 1 MUST fail (str currently passes through), test 2 MUST pass.

Commit: `test(quick): RED — source-level str() should error (str not an Atena builtin)`

### GREEN — one-line fix + full suite

File: `src/atena/analyzer.py` line ~40.

Change:
```python
_BUILTIN_HELPERS: frozenset[str] = frozenset({"length", "str"})
```
To:
```python
_BUILTIN_HELPERS: frozenset[str] = frozenset({"length"})
```

Run full suite — expect 252 tests, 0 failures.

Commit: `fix(quick): remove str from analyzer _BUILTIN_HELPERS so source str() errors`

## Acceptance Criteria

- [ ] `str(5)` in Atena source (no user-defined `function str`) → analyzer error
      with message containing `"str"` and `"define it above this line first"`
- [ ] Injected coercion (`"v: " + x` where x is number) still injects `str()` 
      wrapping with no errors
- [ ] `test_A2_builtin_function_user_redefined_checked` still passes (user defines
      `function str(x)`, calls `str(5,6)` → arity error fires)
- [ ] Golden fixture `school.expected.py` is byte-identical (no changes)
- [ ] Full suite is GREEN at 252 tests
