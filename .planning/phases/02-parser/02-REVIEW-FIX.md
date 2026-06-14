---
phase: 02-parser
fixed_at: 2026-06-14T12:45:12Z
review_path: .planning/phases/02-parser/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
deferred: 1
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-06-14T12:45:12Z
**Source review:** .planning/phases/02-parser/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (this pass): WR-01, WR-02, WR-03, WR-05
- Fixed: 4
- Skipped: 0
- Deferred (explicit scope override): 1 (WR-04)
- Info findings (IN-01/IN-02/IN-03): out of scope this pass; IN-01 applied opportunistically (see WR-01)

All 161 tests remain green after every fix (150 baseline + 11 new regression tests
added across the four fixes). Each fix was committed atomically together with its
regression test. REVIEW-FIX.md itself is NOT committed by the fixer — the orchestrator
commits it.

## Fixed Issues

### WR-01: Trailing tokens after a complete statement are silently accepted

**Files modified:** `src/atena/parser.py`, `tests/test_parser.py`
**Commit:** 2f0bf78
**Applied fix:** Renamed `_consume_newline` to `_end_statement` and made it strict.
It consumes a trailing NEWLINE, treats DEDENT/EOF as valid block-final/file-final
boundaries (per the Atena invariant), and raises a `_ParseError` — `I didn't expect
"<tok>" after the end of this line.` — for any other leftover token. Because the raise
happens *before* the statement node is returned, no half-parsed node leaks into
`program.statements`; synchronize fires and recovery continues. All 11 call sites were
updated to `_end_statement`. Verified: `x = a b`, `show x y`, `x = 5 garbage` now produce
`stmts == []` plus one plain-English error each (previously they leaked a wrong AST node
and emitted a confusing `I didn't expect "b" here`).
**Opportunistically also applied IN-01:** deleted the stale 16-line comment in `_parse_show`
referencing the non-existent `_parse_primary_with_ask_guard`, replacing it with one accurate
line. This was zero-risk and touched code already being edited for `_end_statement`.
**Regression tests added:** `test_P2_trailing_tokens_after_assignment_rejected`,
`test_P2_trailing_tokens_after_show_rejected` (Layer 2).

### WR-02: Stray block-header keyword produces a cascaded `""` error on the orphaned INDENT

**Files modified:** `src/atena/parser.py`, `tests/test_parser.py`
**Commit:** a774dd3
**Applied fix:** Added `_skip_orphaned_block()` and a guard at the top of
`_dispatch_statement`. When synchronize leaves the cursor on an orphaned INDENT (because the
preceding header errored), the guard swallows the entire balanced INDENT…DEDENT block
silently instead of dispatching on the INDENT token (whose value is `""`). The skip method
consumes the opening INDENT first (guaranteeing >= 1 token of progress per the progress
invariant), tracks nested INDENT/DEDENT pairs by depth, and terminates at EOF if a DEDENT is
missing — it cannot hang. Verified: `else\n    show x`, `notakeyword\n    show x`, nested
orphaned blocks, and a second `else` after a complete if/else now each yield exactly one
error with no `expect "" here` message; a valid statement after an orphaned block is still
recovered.
**Regression tests added:** `test_P2_stray_else_with_block_single_error`,
`test_P2_unknown_header_with_block_single_error`,
`test_P2_second_else_after_complete_if_else_single_error` (Layer 2).

### WR-03: `length` binds only to the immediate primary, mis-parsing `length items[0]`

**Files modified:** `src/atena/parser.py`, `tests/test_parser.py`
**Commit:** f292f6d
**Applied fix:** Adopted the review's option (a): the `length` branch in `_parse_primary`
now parses `self._parse_postfix(self._parse_primary())` so `length` takes the full postfix
chain of its operand. The natural reading now holds: `length items[0]` →
`FunctionCall('length', [IndexAccess(Identifier('items'), NumberLiteral(0), False)])` =
`len(items[0])`; `length student.grades` → `len(student.grades)`; `length f()` → `len(f())`
(previously errored). `length items` is unchanged (`test_P1_length` still passes).
`IndexAccess.index_converted` stays `False` from the parser, per invariant.
**Regression tests added:** `test_P1_length_over_index`, `test_P1_length_over_dot` (Layer 1).

### WR-05: Chained comparisons (`1 < 2 < 3`, `a == b == c`) silently mis-evaluated

**Files modified:** `src/atena/parser.py`, `tests/test_parser.py`
**Commit:** c820939
**Applied fix:** Added a `_COMPARISON_OPS` frozenset and a guard in the Pratt loop of
`_parse_expression`: before building a comparison `BinOp`, if the operator is a comparison
and `left` is already a comparison `BinOp`, raise a plain-English `_ParseError` —
`Compare two things at a time — write "1 < 2 and 2 < 3" instead of "1 < 2 < 3".`. Verified:
`1 < 2 < 3` and `a == b == c` are rejected (no leaked node); legitimate single comparisons of
arithmetic (`a + b == c + d`), two comparisons joined by `and` (`a == b and c == d`), and
`not x == 0` (which is `(not x) == 0`) all still parse cleanly — so
`test_Px_logical_not_in_condition` is preserved.
**Regression tests added:** `test_P2_chained_comparison_rejected`,
`test_P2_chained_equality_rejected`, `test_P2_single_comparison_of_arithmetic_ok`,
`test_P2_two_comparisons_joined_by_and_ok` (Layer 2).

## Deferred Issues

### WR-04: Unary `not` binds tighter than comparison

**File:** `src/atena/parser.py:231-247`
**Disposition:** deferred — design decision required
**Reason:** Per explicit scope override. `not`'s tight binding is a deliberate, tested
decision: `test_Px_logical_not_in_condition` asserts `not x == 0` parses as `(not x) == 0`
with `ec.is_empty()`. The review's preferred fix (give `not` a binding power below comparison)
would break that passing test and silently flip Atena-vs-Python semantics — a design call for
a human, not an automated fix. No edit was made to `parser.py` or any test for WR-04.

## Out of Scope (Info — no `--all` this pass)

- **IN-01** (stale comment in `_parse_show`): applied opportunistically as part of the WR-01
  commit (2f0bf78) since it touched code already being edited.
- **IN-02** (`show`/`return` with no operand reports `I didn't expect "" here`): not addressed
  this pass — Info, out of scope.
- **IN-03** (duplicated/inconsistent dict `=` and unclosed-bracket error strings): not addressed
  this pass — Info, out of scope.

---

_Fixed: 2026-06-14T12:45:12Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
