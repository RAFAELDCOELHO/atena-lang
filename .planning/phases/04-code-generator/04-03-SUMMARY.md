---
phase: 04-code-generator
plan: "03"
subsystem: codegen
tags: [tdd, green-phase, codegen, list, dict, function, helpers, on-demand]
dependency_graph:
  requires:
    - 04-02-SUMMARY.md
  provides:
    - All 22 node emitters implemented in CodeGenerator
    - length keyword → len() mapping (GEN-02)
    - FunctionCall-as-statement fix (_emit_as_stmt)
    - On-demand helper preamble active (_atena_index, _atena_concat)
    - Full construct coverage GREEN
  affects:
    - 04-04-PLAN.md (school.atena golden test — all emitters now ready)
tech_stack:
  added: []
  patterns:
    - "_emit_as_stmt(): wraps ast.expr in ast.Expr when used at statement level"
    - "length → len() special-case in _emit_FunctionCall (Atena keyword → Python builtin)"
    - "_build_preamble() active: parses _ATENA_INDEX_SRC/_ATENA_CONCAT_SRC via ast.parse().body"
key_files:
  created: []
  modified:
    - src/atena/codegen.py
    - tests/test_codegen.py
decisions:
  - "_emit_as_stmt() introduced: expression nodes at statement level must be wrapped in ast.Expr or ast.unparse() concatenates them to the prior statement on the same line"
  - "length → len() mapped in _emit_FunctionCall: 'length' is an Atena keyword that maps to the Python builtin 'len'; it is NOT mangled via _mangle() since it is not a Python keyword"
metrics:
  duration: "~8 min"
  completed: "2026-06-14T20:19:18Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 4 Plan 3: List/Dict/Function/Helper emitters complete — full construct coverage GREEN

All 22 CodeGenerator node emitters implemented; on-demand helper preamble active; `length` → `len()` fix applied; FunctionCall-as-statement wrapping fixed.

## What Was Built

### Task 1: List/Dict/Index/DotAccess/ListAdd/Remove emitters + `length` fix

All emitters for list/dict/index/dot constructs were already in place from Plan 02. The one missing piece was the `"length"` → `len()` special case in `_emit_FunctionCall`:

**Bug fixed (Rule 1):** `_emit_FunctionCall` emitted `length(grades)` instead of `len(grades)`.  The Atena keyword `length` maps to the Python builtin `len`; without the special case, generated Python raised `NameError: name 'length' is not defined` at runtime.

**Fix:** Added `if func_name == "length":` branch before the helper-tracking guard, emitting `ast.Call(func=ast.Name(id="len"), ...)`.

**New tests added (RED → GREEN):**
- `test_G2_index_access_executes_verbatim`: `grades[1]` (Atena) → `grades[0]` (Python, from analyzer rewrite) → prints `5`; no double-shift.
- `test_G2_dict_dot_read_executes`: `student.name` → `student["name"]` → prints `Ana`.
- `test_G2_list_add_remove_executes`: add/remove/length list ops execute correctly; `show length grades` now emits `print(len(grades))` and produces `1`.

### Task 2: FunctionDef/Return + on-demand helper preamble + function execution tests

**Bug fixed (Rule 1 — blocking):** FunctionCall nodes at statement level (e.g. top-level `greet("Ana")`) returned `ast.Call` (an `ast.expr`). When placed directly in `body_stmts`, `ast.unparse()` concatenated the call to the preceding statement on the same line, producing a SyntaxError: `print(name)greet("Ana")`.

**Fix:** Introduced `_emit_as_stmt(node)` method that calls `_emit(node)` and wraps the result in `ast.Expr(value=...)` when the result is an `ast.expr` (not already a statement). Updated `generate()`, `_emit_If`, `_emit_While`, `_emit_Repeat`, and `_emit_FunctionDef` to use `_emit_as_stmt()` for all body-list building.

**On-demand preamble confirmed active:** `_build_preamble()` uses `ast.parse(_ATENA_INDEX_SRC).body` / `ast.parse(_ATENA_CONCAT_SRC).body` to inject helper function definitions only when the program references them. This was implemented (not a stub) in Plan 02.

**New tests added (RED → GREEN):**
- `test_G1_function_def_emit`: `function greet(name)` → Python contains `def greet(name):`.
- `test_G2_function_call_executes`: define `greet`, call `greet("Ana")`, subprocess prints `Ana`.
- `test_G2_function_with_return_executes`: `function square(n) / return n * n` → `square(4)` prints `16`.
- `test_Gx_on_demand_index_helper_present_when_used`: program with `g[i]` (dynamic index) → generated Python includes `def _atena_index`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `length` keyword emitted verbatim instead of mapped to `len`**
- Found during: Task 1 (test_G2_list_add_remove_executes RED → NameError at runtime)
- Issue: `_emit_FunctionCall` had no special case for `"length"`, so `show length grades` generated `print(length(grades))` — Python `length` is undefined.
- Fix: Added `if func_name == "length": return ast.Call(func=ast.Name("len"), ...)` branch in `_emit_FunctionCall`.
- Files modified: `src/atena/codegen.py`
- Commit: `2ed416f`

**2. [Rule 1 - Bug] FunctionCall at statement level not wrapped in ast.Expr**
- Found during: Task 2 (test_G2_function_call_executes RED → SyntaxError in generated Python)
- Issue: `_emit(FunctionCall_node)` returns `ast.Call` (an expr). When placed directly into body statement lists, `ast.unparse()` concatenated it to the prior statement: `print(name)greet("Ana")` — invalid Python.
- Fix: Introduced `_emit_as_stmt()` that wraps `ast.expr` results in `ast.Expr()`. Updated all body-list builders (`generate()`, `_emit_If`, `_emit_While`, `_emit_Repeat`, `_emit_FunctionDef`) to use it.
- Files modified: `src/atena/codegen.py`
- Commit: `d1d4e2a`

## Verification Results

```
pytest tests/test_codegen.py -k "G1_dict or G1_list or G2_index or G2_dict or G2_list" -v
  → 5 passed

pytest tests/test_codegen.py -k "G1_function or G2_function or Gx_on_demand" -v
  → 5 passed

pytest tests/ -q --tb=no
  → 1 failed (test_G2_school_execution_placeholder -- intentional pytest.fail() stub)
  → 224 passed

Manual verbatim check: grades[2] → grades[1] (no double-shift) → 'verbatim OK'
Manual on-demand: x=5/show x → no _atena_index; g[i] → def _atena_index prepended
```

## Commits

| Hash | Message |
|------|---------|
| `2ed416f` | `feat(04-03): list/dict/index/dot emitters complete + length→len fix` |
| `d1d4e2a` | `feat(04-03): FunctionCall-as-stmt fix + function/helper tests complete` |

## Self-Check: PASSED

Files verified to exist:
- `src/atena/codegen.py` — all 22 emitters + _emit_as_stmt + length→len fix
- `tests/test_codegen.py` — 7 new tests added (3 Task 1, 4 Task 2)

Commits verified: `2ed416f` and `d1d4e2a` — both present in git log.
