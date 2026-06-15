---
phase: 02-parser
plan: "02"
subsystem: parser
tags: ["pratt", "expression-parser", "precedence", "ast", "tdd"]

requires:
  - phase: 02-01
    provides: "Parser skeleton with _BINARY_BP table, cursor helpers, _ParseError, _parse_block, _synchronize, stub _dispatch_statement"

provides:
  - "_parse_expression() Pratt loop with left-associativity via same-bp right recursion"
  - "_parse_unary() for unary 'not' (right-recursive) and unary '-' (tightest binding)"
  - "_parse_postfix() tight loop for [] . () — left-associative, highest precedence"
  - "_parse_primary() dispatching on all literal/atom types"
  - "_parse_list_literal() and _parse_dict_literal() with = key-value separator"
  - "Minimal _dispatch_statement() for IDENTIFIER=expr (Assign) and bare FunctionCall stmts"

affects: ["02-03", "02-04", "02-05"]

tech-stack:
  added: []
  patterns:
    - "Pratt-binding-power-table: _BINARY_BP as single source of truth for binary precedence (or=1, and=2, comparisons=3, +/-=4, *//=5)"
    - "left-assoc via same-bp: right operand parsed with min_bp=bp (not bp-1) so same-precedence ops on right are rejected"
    - "postfix-tight-loop: _parse_postfix runs after _parse_primary, consuming [] . () before any binary op sees the node"
    - "unary-nud-led-split: unary '-' is only nud (prefix); binary '-' is only led (infix) — position disambiguates"
    - "IndexAccess-always-False: parser always sets index_converted=False; only Phase-3 analyzer sets True (T-02-08)"

key-files:
  created: []
  modified:
    - "src/atena/parser.py"

key-decisions:
  - "Left-associativity uses min_bp=bp (not bp-1) on right parse call — equal-precedence ops on right are rejected, giving left-assoc"
  - "Unary '-' in _parse_unary only consumes the immediately following primary+postfix, never absorbs a binary op on right (PITFALLS.md §7)"
  - "'length' keyword parsed in _parse_primary as FunctionCall(name='length', args=[operand]) — binds only to immediate primary (no postfix chain)"
  - "_dispatch_statement updated minimally: IDENTIFIER+ASSIGN→Assign, bare IDENTIFIER(...)→FunctionCall; full statement dispatch deferred to Plan 03"
  - "String tok.value is already bare content (lexer strips outer quotes) — no strip needed in parser"

requirements-completed:
  - PARSE-02
  - PARSE-01

duration: 8min
completed: "2026-06-14"
---

# Phase 02 Plan 02: Pratt Expression Parser Summary

**Pratt expression engine with full 6-level precedence ladder, all primary atoms, and left-associative postfix chaining — 15 Layer 1 expression tests turned GREEN.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-14
- **Completed:** 2026-06-14
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Implemented complete `_parse_expression()` Pratt loop enforcing all 6 precedence levels from `_BINARY_BP` with correct left-associativity
- Implemented `_parse_unary()` with nud/led split: unary `not` (right-recursive), unary `-` (binds tightest via primary-only operand), and fall-through to postfix
- Implemented `_parse_postfix()` tight loop consuming `[]` (IndexAccess), `.` (DotAccess), `()` (FunctionCall) in left-associative order tighter than any binary op
- Implemented `_parse_primary()` dispatching NUMBER, STRING, KEYWORD bool/length, IDENTIFIER, LPAREN grouped expr, LBRACKET list, LBRACE dict
- Implemented `_parse_list_literal()` and `_parse_dict_literal()` with Atena's `=` key-value separator
- Updated `_dispatch_statement()` minimally to handle `IDENTIFIER = expr` → `Assign` and bare `IDENTIFIER(...)` → `FunctionCall` so expression tests can be exercised

## Task Commits

1. **Task 1: Implement Pratt expression engine in src/atena/parser.py** - `2fcc1ed` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `src/atena/parser.py` — Added 246 lines: `_parse_expression`, `_parse_unary`, `_parse_postfix`, `_parse_primary`, `_parse_list_literal`, `_parse_dict_literal`, updated `_dispatch_statement`

## Decisions Made

- Left-associativity: right operand parsed with `min_bp=bp` (not `bp-1`) — same-precedence ops on right have `bp > min_bp` = false, so they are not absorbed, producing left-association. Verified against `10 - 3 - 2` → `BinOp('-', BinOp('-', 10, 3), 2)`.
- `length` keyword binds only to its immediate primary (not through postfix chain) — avoids ambiguity with e.g. `length items[1]` which should be `length (items[1])` but could be confusing. Implemented as `_parse_primary()` recursive call (not `_parse_postfix(_parse_primary())`).
- `_dispatch_statement` kept minimal: only Assign (IDENTIFIER=expr) and bare expression (FunctionCall via _parse_expression). Full dispatch (show, ask, if, while, repeat, function, return, add, remove, Python-ism redirects) deferred to Plan 03 as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

| Stub | File | Description |
|------|------|-------------|
| `_dispatch_statement` | src/atena/parser.py | Only handles Assign and bare FunctionCall; Plan 03 adds show, ask, if, while, repeat, function, return, add, remove, Python-ism redirects |

This stub is intentional and documented. Plan 03 owns full statement dispatch.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- `src/atena/parser.py`: FOUND
- Commit 2fcc1ed: verified
- All 15 P1 expression tests PASSED: `test_P1_binop_add`, `test_P1_binop_precedence_mul_over_add`, `test_P1_left_associativity`, `test_P1_unary_minus`, `test_P1_unary_minus_binary`, `test_P1_logical_and`, `test_P1_logical_or_lower_than_and`, `test_P1_not_unary`, `test_P1_comparison`, `test_P1_postfix_index`, `test_P1_postfix_chain_double_index`, `test_P1_dot_access`, `test_P1_function_call`, `test_P1_function_call_args`, `test_P1_list_literal`, `test_P1_dict_literal`, `test_P1_length`
- `test_Px_empty_program`: PASSED (regression)
- Statement tests (show, ask, if, while, repeat, function, return, list_add, list_remove): still FAILED (expected — Plan 03 owns them)
- IndexAccess.index_converted is False on all parsed nodes: VERIFIED by test_P1_postfix_index and test_P1_postfix_chain_double_index

## Next Phase Readiness

- Plan 03 can use `_parse_expression()` as the RHS parser for all statement forms (assign, show, if condition, while condition, repeat count, return value, add/remove value)
- `_dispatch_statement` needs to be replaced with full dispatch in Plan 03
- All 6 expression methods are clean, well-commented, and follow the PATTERNS.md conventions

---
*Phase: 02-parser*
*Completed: 2026-06-14*
