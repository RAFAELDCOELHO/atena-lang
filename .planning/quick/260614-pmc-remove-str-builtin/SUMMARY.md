---
id: 260614-pmc
title: Remove str from analyzer _BUILTIN_HELPERS so source-level str() errors
date: 2026-06-14
status: complete
branch: feat/generator
review_ref: WR-01 in .planning/phases/04-code-generator/04-REVIEW.md
commits:
  red:  6048f87
  fix:  6cf6c40
---

# Summary: 260614-pmc Remove str from _BUILTIN_HELPERS

## One-liner

Removed "str" from _BUILTIN_HELPERS (now only {"length"}) and moved the
_coerced idempotency guard before child-visits in visit_BinOp so that
source-level str() errors with a plain-English message while analyzer-injected
coercion is completely unaffected.

## What Changed

### src/atena/analyzer.py

1. Line ~40: _BUILTIN_HELPERS: frozenset[str] = frozenset({"length"}) -- "str" removed.
2. visit_BinOp: Moved the _coerced idempotency guard (CR-01) to BEFORE
   _visit(node.left) / _visit(node.right). This was necessary because after
   coercion the right/left operand is a FunctionCall("str", ...) injected by
   the analyzer. On re-analysis (the test_Ax_coercion_idempotent test), visiting
   that child calls visit_FunctionCall, which -- after removing "str" from
   _BUILTIN_HELPERS -- would report "str" as an undefined function. Short-
   circuiting before visiting children avoids that path entirely, keeping the
   idempotency invariant intact.

### tests/test_analyzer.py

Two new tests added:

- test_A2_source_str_call_errors -- RED gate: str(5) in source (no user
  "function str") must produce a plain-English undefined-function error.
- test_A1_injected_coercion_still_works -- GREEN guard: "v: " + x (x is a
  number) must still inject FunctionCall("str", [x]) with no errors.

## Commits

| Role | Hash    | Message |
|------|---------|---------|
| RED  | 6048f87 | test(quick): RED -- source-level str() should error (str not an Atena builtin) |
| FIX  | 6cf6c40 | fix(quick): remove str from analyzer _BUILTIN_HELPERS so source str() errors |

## Acceptance Criteria Verification

- [x] str(5) in Atena source (no user-defined function str) errors with plain-English message
- [x] Injected coercion ("v: " + x where x is number) still injects str() wrapping, no errors
- [x] test_A2_builtin_function_user_redefined_checked still passes (arity error fires)
- [x] Golden fixture school.expected.py byte-identical (test_G1_golden_school_roundtrip PASSED)
- [x] Full suite: 253 tests, 0 failures

## Deviation from Plan

One deviation: a second change was required in visit_BinOp (moving the _coerced
guard before child-visits). Without it, test_Ax_coercion_idempotent failed because
injected FunctionCall("str",...) nodes were visited on re-analysis and errored.
Auto-fixed per Rule 1 (bug in existing test revealed by the primary change).

## Self-Check: PASSED
