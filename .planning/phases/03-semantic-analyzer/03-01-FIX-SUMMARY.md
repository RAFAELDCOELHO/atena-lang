---
phase: 03-semantic-analyzer
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/03-semantic-analyzer/03-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
finding_status:
  CR-01: fixed
  CR-02: fixed
  WR-01: fixed
  WR-02: fixed
  WR-03: fixed
  WR-04: fixed
  WR-05: documented
  WR-06: fixed
---

# Phase 3: Code Review Fix Summary

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/03-semantic-analyzer/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (CR-01, CR-02, WR-01..WR-06)
- Fixed: 8 (all)
- Skipped: 0

**Test count:** 189 baseline → 200 after fixes (11 new tests added)

---

## Fixed Issues

### CR-01: str() coercion injection is not idempotent

**Files modified:** `src/atena/analyzer.py`, `tests/test_analyzer.py`
**Commit:** 8a069b2
**Applied fix:**
Added a `_coerced` flag on BinOp nodes (mirroring `IndexAccess.index_converted`).
After `coerce_right` or `coerce_left` injection the flag is set. On a second
`visit_BinOp` call the flag is detected via `getattr(node, "_coerced", False)` and
the method returns `"str"` immediately without re-mutating the node.
Also fixed WR-03 in the same change: after `node.__class__ = FunctionCall` swap,
the stale `op`, `left`, `right` fields are deleted via `delattr`.

**Test added:** `test_Ax_coercion_idempotent` — re-analyzes a `"a" + 1` program and
asserts the tree shape is unchanged (BinOp not converted to FunctionCall on second pass).

---

### CR-02: add/remove statement targets bypass defined-before-use check

**Files modified:** `src/atena/analyzer.py`, `tests/test_analyzer.py`
**Commit:** 9effafe
**Applied fix:**
Added `_check_list_target(node)` helper that mirrors `visit_Identifier` Case 4:
looks up `node.target` in the current scope, emits a plain-English error with
`suggest()` hint when undefined, and poisons the name to suppress cascade errors.
Wired into both `visit_ListAdd` and `visit_ListRemove`.

**Tests added:**
- `test_A2_add_to_undefined_list_errors` — `add 1 to mylist` with undefined mylist errors
- `test_A2_remove_from_undefined_list_errors` — `remove 1 from mylist` with undefined mylist errors

---

### WR-01: Built-in helper names are unguarded

**Files modified:** `src/atena/analyzer.py`, `tests/test_analyzer.py`
**Commit:** b6ffc74
**Applied fix:**
Three parts:
1. **IN-02 (single source of truth):** Hoisted `_BUILTIN_HELPERS = frozenset({"length", "str"})` and `_INTERNAL_HELPERS = frozenset({"_atena_concat", "_atena_index"})` as module-level constants. `visit_FunctionCall` now references these constants.
2. **`_atena_` prefix reservation:** `visit_Assign` and `visit_FunctionDef` reject names starting with `_atena_` with a plain-English "reserved internal name" error. The guard only fires for user-written source (analyzer-injected FunctionCall nodes are created directly in memory, never via `visit_Assign`/`visit_FunctionDef`).
3. **Builtin shadowing:** `visit_FunctionCall` now only bypasses arity checks for `_BUILTIN_HELPERS` when the name is NOT in `self._functions`. If the user defined `function str(x)`, the normal arity/defined checks apply.

**Tests added:**
- `test_A2_atena_prefix_assign_rejected` — `_atena_index = 5` errors
- `test_A2_atena_prefix_function_def_rejected` — `function _atena_concat(a, b)` errors
- `test_A2_builtin_function_user_redefined_checked` — `function str(x)` redefinition; wrong-arity call to `str(5, 6)` now errors

---

### WR-02: Duplicate function definitions silently accepted

**Files modified:** `src/atena/analyzer.py` (in WR-01 commit), `tests/test_analyzer.py`
**Commit (tests):** 6ee43ac
**Applied fix:**
The fix was implemented inside `visit_FunctionDef` as part of WR-01: before registering a new function, check if `node.name` is already in `self._functions`. If so, emit a plain-English redefinition error and keep the first registration (arity stays stable). The body is still visited to collect further errors.

**Tests added:**
- `test_A2_duplicate_function_def_errors` — second `function f(a, b)` errors with "already defined"
- `test_Ax_duplicate_function_first_arity_used` — after duplicate, `f(1)` is NOT an arity error (first arity=1 wins)

---

### WR-03: Stale op/left/right fields persist after BinOp.__class__ = FunctionCall

**Files modified:** `src/atena/analyzer.py` (in CR-01 commit), `tests/test_analyzer.py`
**Commit (test):** 46a49ff
**Applied fix:**
After the in-place `node.__class__ = FunctionCall` swap in `visit_BinOp`, a `delattr`
loop removes `op`, `left`, `right` if they exist. This was implemented alongside CR-01.
The parallel `str()` coercion path already built fresh `FunctionCall` nodes (no stale fields).

**Test added:** `test_Ax_no_stale_attrs_after_concat_conversion` — after `_atena_concat`
conversion, asserts `hasattr(rhs, "op")` is False, `"left"` False, `"right"` False.

---

### WR-04: Poisoned undefined name keeps type "unknown" after later valid assignment

**Files modified:** `src/atena/analyzer.py`, `tests/test_analyzer.py`
**Commit:** 25825a2
**Applied fix (minimal safe):**
`visit_Assign` already unconditionally overwrites `scope[node.name] = inferred`, which
is exactly the correct behavior — a later valid assignment re-types a previously poisoned
name. Added a detailed code comment documenting:
- The safe behavior: `visit_Assign` overwrites the poisoned entry
- The v1.0 single-pass limitation: a name USED before its assignment keeps "unknown" at
  the use site; any downstream "+" routes through `_atena_concat` rather than the
  more precise `str()` coercion. This is intentional and safe (over-routes to runtime
  helper, never mis-coerces).

**Test added:** `test_Ax_poison_overwritten_by_valid_assign` — `show ghost; ghost = 5`
produces exactly 1 error (the undefined use); the assignment corrects the scope.

---

### WR-05: DotAccess and DictLiteral keys never validated

**Files modified:** `src/atena/analyzer.py`
**Commit:** f5d97d1
**Applied fix (documentation):**
Per review guidance, static validation of dict field names requires a full dict type
system (out of scope for v1.0). Added explicit code comments to `visit_DotAccess` and
`visit_DictLiteral` documenting:
- Why key/field names cannot be statically validated (no per-variable dict type in v1.0)
- That a field typo slips to runtime as KeyError/AttributeError
- That Phase-4 should emit guarded access helpers to convert these to plain-English errors

No behavior change. No test required (behavior unchanged, limitation is documented).

---

### WR-06: _visit_default silently swallows unknown node types

**Files modified:** `src/atena/analyzer.py`, `tests/test_analyzer.py`
**Commit:** 02e134d
**Applied fix:**
Made the gap surface in tests rather than production (per review guidance — do NOT raise
to the user at runtime, which would violate collect-all-errors).

**Test added:** `test_Ax_all_node_types_have_visitors` — uses `inspect` to enumerate
every concrete `Node` subclass from `ast_nodes` and asserts `SemanticAnalyzer` has a
`visit_<Type>` method for each. Any future node added without a visitor will fail this test.

Also added a `DO NOT ADD WITHOUT VISITOR` warning comment to `_visit_default`.

---

## Skipped Issues

None. All 8 in-scope findings were addressed.

---

## Notes on Info Findings

- **IN-01** (`visit_Program` is dead code): Left unchanged. The dead method is harmless
  and changing it would require restructuring `analyze()` — scope creep beyond the fix task.
- **IN-02** (magic string set for builtins): Addressed as part of WR-01 (hoisted
  `_BUILTIN_HELPERS` and `_INTERNAL_HELPERS` constants).
- **IN-03** (missing test coverage): Fully addressed — 11 new tests cover all the gaps
  identified (coercion idempotency, list-mutation undefined targets, builtin shadowing,
  duplicate defs, stale attrs, poison overwrite, node visitor coverage).

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
