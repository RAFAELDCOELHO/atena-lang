---
phase: 03-semantic-analyzer
plan: 02
subsystem: analyzer
tags: [semantic-analyzer, type-inference, coercion, index-rewrite, tdd, python]

# Dependency graph
requires:
  - phase: 03-semantic-analyzer
    plan: 01
    provides: SemanticAnalyzer skeleton with 22 visit stubs + 27 RED test stubs

provides:
  - visit_BinOp: str() coercion injection and _atena_concat routing for unknown-typed operands
  - visit_IndexAccess: 1-based to 0-based literal fold + idempotency guard + dynamic _atena_index routing
  - visit_Assign: basic symbol type registration (name → inferred type) in current scope
  - visit_Identifier: symbol table lookup returning registered type or "unknown"
  - _COERCE_TABLE: fully populated for all 9 str/number/bool type pairs
  - _HUMAN_TYPE: complete map of 6 lattice members to plain-English labels
  - Literal visitor type returns: NumberLiteral→"number", StringLiteral→"str", BoolLiteral→"bool"
  - Structural visitor child visitation: ListLiteral, DictLiteral, Show, If, While, Repeat, Return, FunctionCall, DotAccess, ListAdd, ListRemove, FunctionDef

affects:
  - 03-03 (scope/arity: adds undefined-name errors, ask registration, arity checks, two-level scope)
  - 04-codegen (reads mutated AST: str() FunctionCall nodes, _atena_concat FunctionCall nodes, folded index values, _atena_index FunctionCall nodes)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_COERCE_TABLE.get((left_type, right_type), 'error') — total coverage, list/dict combos handled by fallback"
    - "BinOp.__class__ = FunctionCall in-place mutation for _atena_concat injection (no parent context needed)"
    - "IndexAccess.index_converted idempotency guard — first check in visit_IndexAccess"
    - "Bottom-up type inference: _visit returns type string; chains propagate correctly"
    - "visit_Assign registers inferred type in scope; visit_Identifier looks it up"

key-files:
  created: []
  modified:
    - src/atena/analyzer.py

key-decisions:
  - "BinOp node converted in-place to FunctionCall via __class__ reassignment for _atena_concat — avoids needing parent context and satisfies test_A1_unknown_plus_uses_concat_helper"
  - "Basic symbol table tracking (visit_Assign registers type, visit_Identifier looks up) implemented in Plan 02 — required by chain coercion tests (test_A1_string_concat_no_coerce, test_A1_number_plus_number_no_coerce)"
  - "list/dict combos not in _COERCE_TABLE — fallback .get(..., 'error') handles them, consistent with plan's note on ANY rows"
  - "str() coercion wraps the OPERAND, not the whole BinOp — BinOp stays as structural node with mutated child"

# Metrics
duration: 5min
completed: 2026-06-14
---

# Phase 3 Plan 02: Expression Semantics GREEN Summary

**visit_BinOp with str() coercion and _atena_concat routing, visit_IndexAccess with 1-based-to-0-based literal fold and dynamic _atena_index routing, _COERCE_TABLE and _HUMAN_TYPE fully populated — 18 of 27 analyzer tests now GREEN**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-14T17:16:54Z
- **Completed:** 2026-06-14T17:22:00Z
- **Tasks:** 3
- **Files modified:** 1 (src/atena/analyzer.py)

## Accomplishments

- Populated `_HUMAN_TYPE` with all 6 type lattice members and `_COERCE_TABLE` with all 9 explicit str/number/bool pairs
- Implemented `visit_BinOp`: bottom-up type inference, `str()` FunctionCall injection for coerce_right/coerce_left, `_atena_concat` FunctionCall in-place mutation for unknown-typed operands, "I can't add" error for disallowed combos
- Implemented `visit_IndexAccess`: idempotency guard, literal 0 error, literal-positive fold (n→n-1), literal-negative UnaryOp error, dynamic _atena_index routing; correctly handles nested access (`grid[2][3]` → `grid[1][2]`) via bottom-up visitation
- Added basic symbol type tracking to `visit_Assign` (register inferred type) and `visit_Identifier` (look up registered type) — required by chain coercion tests
- Updated all structural visitor stubs (Show, If, While, Repeat, Return, FunctionCall, FunctionDef, DotAccess, ListAdd, ListRemove, ListLiteral, DictLiteral) to visit their children and return correct type strings
- Turned 18/27 tests GREEN; 9 scope/arity tests correctly remain RED for Plan 03

## Task Commits

1. **Task 1: Populate _COERCE_TABLE, _HUMAN_TYPE, literal/structural visitor types** - `9b47784` (feat)
2. **Task 2: Implement visit_BinOp** - `8ac2e6c` (feat)
3. **Task 3: Implement visit_IndexAccess** - `c5cbe6e` (feat)

## Files Created/Modified

- `src/atena/analyzer.py` — Updated with all three tasks:
  - `_HUMAN_TYPE`: 6 entries (str→"text", number→"number", bool→"true/false", list→"list", dict→"dictionary", unknown→"unknown")
  - `_COERCE_TABLE`: 9 explicit str/number/bool pair entries; list/dict "error" via `.get(..., "error")` fallback
  - `visit_BinOp`: full coercion+concat+error dispatch
  - `visit_IndexAccess`: idempotency guard + literal fold + bounds errors + dynamic routing
  - `visit_Assign`: registers `scope[name] = inferred` for coercion type tracking
  - `visit_Identifier`: returns `scope.get(name, "unknown")` for type lookup
  - All 22 structural visitor stubs updated with child visitation and correct return types

## Decisions Made

- **BinOp→FunctionCall in-place mutation (`node.__class__ = FunctionCall`):** When either operand of `+` has unknown type, the plan described replacing `node.left` with a `FunctionCall("_atena_concat")` and setting `node.right` to a sentinel. However, `test_A1_unknown_plus_uses_concat_helper` asserts that `assign.value` (the BinOp) IS a `FunctionCall`. This requires the BinOp object itself to become a FunctionCall. The in-place `__class__` reassignment preserves the object reference (so `assign.value` still points to the same object, now visible as a FunctionCall) without needing parent context. Python fully supports `__class__` reassignment between compatible dataclass types.

- **Symbol tracking in Plan 02 (not Plan 03):** The plan's task descriptions said "symbol table registration deferred to Plan 03." However, `test_A1_string_concat_no_coerce` (tracking `x = "a"+"b"` as "str" then using `x+1`) and `test_A1_number_plus_number_no_coerce` (tracking `x = 1+2` as "number" then using `"prefix"+x`) both require symbol table lookup. Implementing basic type tracking in `visit_Assign`/`visit_Identifier` in Plan 02 is necessary to satisfy these tests. The FULL scope enforcement (undefined-name errors, ask registration, two-level scope, arity) remains Plan 03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Implement BinOp→FunctionCall via `__class__` mutation rather than node.left replacement**
- **Found during:** Task 2 (visit_BinOp _atena_concat injection)
- **Issue:** The plan's described approach (set `node.left = FunctionCall("_atena_concat")`, `node.right = NumberLiteral(0)`) would leave `assign.value` as a BinOp, failing `test_A1_unknown_plus_uses_concat_helper` which asserts `isinstance(assign.value, FunctionCall)`.
- **Fix:** Used `node.__class__ = FunctionCall` to convert the BinOp in-place to a FunctionCall, then set `node.name = "_atena_concat"` and `node.args = [orig_left, orig_right]`. All parent references (e.g., `assign.value`) now correctly see a FunctionCall.
- **Files modified:** src/atena/analyzer.py
- **Commit:** 8ac2e6c

**2. [Rule 2 - Missing Critical Functionality] Added basic symbol tracking in Plan 02 (deferred by plan, but required by tests)**
- **Found during:** Task 2 (visit_BinOp implementation — chain coercion tests)
- **Issue:** The plan deferred all symbol table registration to Plan 03. However, `test_A1_string_concat_no_coerce` and `test_A1_number_plus_number_no_coerce` require that variable types are tracked across assignments for correct coercion decisions. Without tracking, `x` (from `x = "a"+"b"`) would be "unknown" and `x+1` would route through `_atena_concat` instead of coercing the `1`.
- **Fix:** Added `scope[node.name] = inferred` in `visit_Assign` and `scope.get(node.name, "unknown")` in `visit_Identifier`. The FULL scope enforcement (undefined errors, two-level scope, ask, arity) is still Plan 03.
- **Side effect:** `test_A1_bool_literal_type_inferred` also turned GREEN (was supposed to remain RED per must_haves). Since `x = true` now correctly registers `x → "bool"`, `x + 1` correctly errors as "can't add bool+number." This is the CORRECT behavior — the must_haves incorrectly assumed symbol tracking wasn't needed until Plan 03.
- **Files modified:** src/atena/analyzer.py
- **Commit:** 8ac2e6c

## Test Results

### Tests GREEN (18/27)

SEM-01..05 expression-level tests (A1/A2/Ax layers):
- `test_A1_index_literal_rewritten` — items[1] → index.value==0, index_converted True
- `test_A1_nested_index_rewritten` — grid[2][3] → outer index 2, inner index 1
- `test_A1_string_concat_no_coerce` — "a"+"b" unchanged, x+1 coerces right
- `test_A1_str_coerce_number_rhs` — "hello"+5 wraps 5 in str()
- `test_A1_str_coerce_number_lhs` — 1+"x" wraps 1 in str()
- `test_A1_number_plus_number_no_coerce` — 1+2 unchanged, "prefix"+x coerces x
- `test_A1_str_coerce_bool_rhs` — "a"+true wraps true in str()
- `test_A1_unknown_plus_uses_concat_helper` — getValue()+1 → FunctionCall("_atena_concat")
- `test_A1_variable_index_uses_atena_index_helper` — items[i] → FunctionCall("_atena_index")
- `test_A1_bool_literal_type_inferred` — x=true; x+1 correctly errors (positive deviation)
- `test_A2_index_zero_error` — items[0] → "start at 1, not 0" error on line 2
- `test_A2_index_negative_error` — items[-3] → "no negative positions" error
- `test_A2_cannot_combine_number_bool` — 1+true → "can't add" error
- `test_A2_cannot_combine_list_str` — [1]+1 → "can't add" error
- `test_Ax_chain_coercion_correct` — "a"+1+2 → both 1 and 2 wrapped in str()
- `test_Ax_nested_subscript_independent` — grid[2][3] no double-shift
- `test_Ax_index_converted_idempotent` — re-analysis doesn't double-shift
- `test_Ax_empty_program_no_errors` — empty program + minimal valid program produce no errors

### Tests RED (9/27 — Plan 03 scope)

- `test_A1_ask_registers_str_type` — ask target registration (Plan 03 visit_Ask)
- `test_A2_undefined_variable` — SEM-06 undefined name detection
- `test_A2_undefined_suggests_close_name` — SEM-06 suggest() affordance
- `test_A2_call_before_defined` — SEM-07 no-hoisting enforcement
- `test_A2_wrong_arity_too_many` — SEM-07 arity checking
- `test_A2_wrong_arity_too_few` — SEM-07 arity checking
- `test_A2_function_reads_outer_var` — D-08 tailored outer-variable message
- `test_Ax_poison_suppresses_cascade` — D-09 poisoning
- `test_Ax_multiple_errors_collected` — multi-error collection

## No Regressions

All 111 pre-existing tests (test_parser.py, test_tokens.py, test_lexer.py) pass unchanged.

## Known Stubs

- `visit_Ask`: does not register `node.target → "str"` in symbol table (Plan 03)
- `visit_FunctionDef`: visits body but does not push/pop local scope or register arity (Plan 03)

## Threat Flags

None — this plan modifies only Python source files (no network endpoints, auth paths, file access, or schema changes). The T-03-02 through T-03-04 mitigations from the plan's threat model are implemented:
- T-03-03 (unlisted type pairs fallback to "error"): satisfied by `_COERCE_TABLE.get(..., "error")`
- T-03-04 (double-shift prevention): satisfied by `node.index_converted` idempotency guard

## Self-Check: PASSED

- FOUND: src/atena/analyzer.py
- FOUND: 03-02-SUMMARY.md
- FOUND commit 9b47784 (Task 1: constants + structural visitors)
- FOUND commit 8ac2e6c (Task 2: visit_BinOp + symbol tracking)
- FOUND commit c5cbe6e (Task 3: visit_IndexAccess)
