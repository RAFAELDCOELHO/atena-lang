---
phase: 03-semantic-analyzer
verified: 2026-06-14T00:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 3: Semantic Analyzer Verification Report

**Phase Goal:** The AST is enriched in place with every semantic decision — coercion, index rewrite, scope and arity checks — so the generator can later emit verbatim and never re-derive anything.
**Verified:** 2026-06-14
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `str()` is injected for `string+number` and `string+bool` | ✓ VERIFIED | `visit_BinOp` wraps `node.right` or `node.left` with `FunctionCall(name="str")` via `_COERCE_TABLE`; `test_A1_str_coerce_number_rhs`, `test_A1_str_coerce_bool_rhs` pass |
| 2 | `"a"+1+2` chains correctly — both 1 and 2 wrapped | ✓ VERIFIED | Bottom-up dispatch: inner BinOp returns "str" after coercing 1; outer sees ("str","number") and coerces 2; confirmed by direct probe and `test_Ax_chain_coercion_correct` |
| 3 | Literal `items[1]` rewrites index to 0, sets `index_converted=True` (idempotent) | ✓ VERIFIED | `visit_IndexAccess` folds in place; `test_A1_index_literal_rewritten`, `test_Ax_index_converted_idempotent` pass |
| 4 | Nested `grid[2][3]` becomes `grid[1][2]` without double-shift | ✓ VERIFIED | `_visit(node.target)` visits inner before outer; direct probe confirmed outer=2, inner=1; `test_Ax_nested_subscript_independent` passes |
| 5 | `items[0]` errors "start at 1, not 0"; `items[-3]` errors with "no negative positions" | ✓ VERIFIED | Compile-time messages verified by direct probe; `test_A2_index_zero_error`, `test_A2_index_negative_error` pass |
| 6 | Variable index `items[i]` replaces index with `FunctionCall("_atena_index")` | ✓ VERIFIED | Dynamic path in `visit_IndexAccess`; `test_A1_variable_index_uses_atena_index_helper` passes |
| 7 | Undefined variable produces one plain-English error with line number; second use is silenced by poison | ✓ VERIFIED | `visit_Identifier` Case 4 poisons scope; `test_A2_undefined_variable`, `test_Ax_poison_suppresses_cascade` pass |
| 8 | Outer-variable access from function body produces tailored "pass as parameter" message (D-08) | ✓ VERIFIED | Case 3 in `visit_Identifier`; error text confirmed "pass" + "parameter"; `test_A2_function_reads_outer_var` passes |
| 9 | Calling undefined function or wrong-arity call produces plain-English error; correct calls produce no error | ✓ VERIFIED | `visit_FunctionCall` enforces defined-before-called and arity; `test_A2_call_before_defined`, `test_A2_wrong_arity_too_many`, `test_A2_wrong_arity_too_few` pass |

**Score:** 9/9 truths verified

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| SEM-01 | `str()` coercion for `string+number` and `string+bool`, bottom-up chain | ✓ SATISFIED | `_COERCE_TABLE` entries `("str","number")->"coerce_right"`, `("str","bool")->"coerce_right"`, `("number","str")->"coerce_left"`, `("bool","str")->"coerce_left"`; `visit_BinOp` injects `FunctionCall(name="str")`; chain test verified |
| SEM-02 | Plain-English error for disallowed `+` combinations | ✓ SATISFIED | `_COERCE_TABLE` maps `("number","bool")`, `("bool","number")`, `("bool","bool")` to `"error"`; list/dict fallback via `.get(...,"error")`; error text: "I can't add a {type} and a {type} together" |
| SEM-03 | 1-indexed → 0-indexed rewrite (idempotent); nested `grid[2][3]→grid[1][2]` | ✓ SATISFIED | `visit_IndexAccess` folds `node.index.value -= 1`, sets `node.index_converted = True`; idempotency guard at method entry; direct probe + `test_Ax_nested_subscript_independent` |
| SEM-04 | Literal index `0` → "Lists in Atena start at 1, not 0."; negative literal → distinct error | ✓ SATISFIED | Explicit `if node.index.value == 0` and `elif isinstance(UnaryOp "-")` branches; distinct messages; `test_A2_index_zero_error`, `test_A2_index_negative_error` pass |
| SEM-05 | Variable index routed through `_atena_index` runtime helper | ✓ SATISFIED | `else` branch creates `FunctionCall(name="_atena_index", args=[orig_index])`; `test_A1_variable_index_uses_atena_index_helper` passes |
| SEM-06 | Undefined variable detected, plain-English error, suggest() hint, cascades suppressed | ✓ SATISFIED | `visit_Identifier` four-case resolution; poison pattern; suggest() from `errors.py`; D-08 outer-var teaching message; `test_A2_undefined_variable`, `test_A2_undefined_suggests_close_name`, `test_Ax_poison_suppresses_cascade` pass |
| SEM-07 | Functions defined before called (no hoisting); arity checked | ✓ SATISFIED | `visit_FunctionDef` registers BEFORE body; `visit_FunctionCall` checks `self._functions`; arity error format verified; `test_A2_call_before_defined`, `test_A2_wrong_arity_too_many`, `test_A2_wrong_arity_too_few` pass |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/atena/analyzer.py` | `SemanticAnalyzer` class with all 22 visit methods, `_COERCE_TABLE`, `_HUMAN_TYPE`, `_BUILTIN_HELPERS`, `_INTERNAL_HELPERS` | ✓ VERIFIED | 599 lines; all listed visitor methods present; constants populated; `analyze()` returns same Program object (in-place mutation confirmed) |
| `tests/test_analyzer.py` | 3-layer test suite (A1/A2/Ax) covering all SEM-01..SEM-07 | ✓ VERIFIED | 38 tests; 625 lines; all pass (38/38); includes post-review tests for CR-01/CR-02/WR-01..WR-06 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_analyzer.py` | `src/atena/analyzer.py` | `from atena.analyzer import SemanticAnalyzer` | ✓ WIRED | Import confirmed; all 38 tests chain through real pipeline |
| `src/atena/analyzer.py` | `src/atena/errors.py` | `from atena.errors import ErrorCollector, suggest, ATENA_KEYWORDS` | ✓ WIRED | Import present line 12; `suggest()` called in `visit_Identifier` and `visit_FunctionCall`; `ATENA_KEYWORDS` used as fallback candidates |
| `visit_BinOp` | `_COERCE_TABLE` | `_COERCE_TABLE.get((left_type, right_type), "error")` | ✓ WIRED | `_COERCE_TABLE` present at module level; lookup confirmed; list/dict fallback via `.get(...,"error")` |
| `visit_IndexAccess` | `IndexAccess.index_converted` | idempotency guard at method entry | ✓ WIRED | `if node.index_converted: self._visit(node.index); return "unknown"` — verified prevents double-shift |
| `visit_IndexAccess` | `FunctionCall("_atena_index")` | dynamic index routing | ✓ WIRED | `else` branch creates and assigns helper; `test_A1_variable_index_uses_atena_index_helper` confirms |
| `visit_Identifier` | `self._globals / self._locals` | scope resolution: locals first if inside function | ✓ WIRED | `scope = self._locals if self._locals is not None else self._globals` pattern consistent across all visitor methods |
| `visit_FunctionDef` | `self._functions` | `self._functions[node.name] = len(node.params)` | ✓ WIRED | Registered before body visit; try/finally scope restore confirmed |
| `visit_FunctionCall` | `self._functions` | `node.name not in self._functions → error` | ✓ WIRED | Defined-before-called check; arity check; builtin bypass confirmed |
| `visit_Assign` | `self._globals / self._locals` | `scope[node.name] = inferred` | ✓ WIRED | Direct probe: `x = 5` → `sa._globals["x"] == "number"` |

### Data-Flow Trace (Level 4)

The analyzer is a tree-walking transformer, not a renderer. Level 4 trace is performed by verifying that AST mutations made by the analyzer actually appear in the returned `Program` object:

| Transformation | AST Field Checked | Probe Result | Status |
|----------------|-------------------|--------------|--------|
| str() coercion: `"hello"+5` → `node.right = FunctionCall("str")` | `prog.statements[0].value.right` | `FunctionCall(name="str", args=[NumberLiteral(5)])` | ✓ FLOWING |
| Index rewrite: `items[1]` → `index.value=0, index_converted=True` | `prog.statements[1].value.index` | `NumberLiteral(value=0), index_converted=True` | ✓ FLOWING |
| Dynamic index: `items[i]` → `node.index = FunctionCall("_atena_index")` | `prog.statements[2].value.index` | `FunctionCall(name="_atena_index", args=[Identifier("i")])` | ✓ FLOWING |
| _atena_concat injection: `getValue()+1` → `FunctionCall("_atena_concat")` | `prog.statements[1].value` | `FunctionCall(name="_atena_concat", args=[...])` with no stale BinOp attrs | ✓ FLOWING |
| ask str typing: `answer = ask "..."` → `_globals["answer"]="str"` | `sa._globals["answer"]` | `"str"` | ✓ FLOWING |
| Scope isolation: function local vars do NOT appear in globals | `sa._globals` after `localvar=5` in function | `{"f": "function"}` — `localvar` absent | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 38 analyzer tests pass | `pytest tests/test_analyzer.py -q` | 38 passed, 0 failed in 0.02s | ✓ PASS |
| Full 200-test suite (no regressions) | `pytest tests/ -q` | 200 passed, 0 failed in 0.28s | ✓ PASS |
| `analyze()` returns same Program object | `id(result) == id(prog)` | True — in-place mutation contract holds | ✓ PASS |
| Error messages contain no Python jargon | grep for Traceback, AttributeError, NoneType, token, AST, DEDENT, arity | None found in any error output | ✓ PASS |
| Error format: "Error on line N: ..." | First line of all error reports | All begin `Error on line N:` | ✓ PASS |
| `_atena_concat` conversion leaves no stale attrs | `hasattr(rhs, "op")`, `hasattr(rhs, "left")` after swap | False, False — stale attrs deleted | ✓ PASS |
| Coercion idempotency: second analyze() pass is no-op | Re-run analyzer on already-analyzed program | Tree shape unchanged; no double-wrap; no BinOp→FunctionCall corruption | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED (no probe scripts defined for this phase — no `scripts/*/tests/probe-*.sh` exist)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TBD/FIXME/XXX/HACK/PLACEHOLDER markers found in `src/atena/analyzer.py` or `tests/test_analyzer.py` |

One notable non-stub "return null" pattern — `visit_Program` returns `"unknown"` and is dead code (IN-01 from REVIEW.md). This is an info-level finding from the code review, explicitly accepted as harmless in `03-01-FIX-SUMMARY.md`. It does not affect goal achievement.

### Human Verification Required

None. All must-haves are verifiable programmatically. The error message quality (plain-English, encouraging voice) was verified by direct output inspection — all messages meet the standard.

---

## Summary

Phase 3 goal is fully achieved. The `SemanticAnalyzer` enriches the parsed `Program` AST in place across all seven semantic dimensions:

1. **SEM-01/02 (Coercion):** `visit_BinOp` injects `str()` wrappers for allowed string-plus-number/bool combinations and emits plain-English errors for disallowed ones. Chain coercion (`"a"+1+2`) resolves correctly bottom-up. The `_atena_concat` helper is injected for unknown-typed operands. Coercion is idempotent via the `_coerced` flag.

2. **SEM-03/04/05 (Index rewrite):** `visit_IndexAccess` folds literal 1-based indices to 0-based in place (idempotent via `index_converted`), emits distinct errors for literal-0 and literal-negative, and routes dynamic indices through `FunctionCall("_atena_index")`. Nested subscripts rewrite independently without double-shift.

3. **SEM-06 (Undefined variables):** `visit_Identifier` implements four-case scope resolution with poison suppression (one error per name), `suggest()` hints, and a tailored teaching message for outer-variable access from inside a function (D-08).

4. **SEM-07 (Function scope/arity):** `visit_FunctionDef` pushes/pops a fresh local scope via `try/finally`, registers arity before visiting the body (enabling self-recursion). `visit_FunctionCall` enforces defined-before-called and exact arity. Local variables never leak to global scope.

The code review (03-REVIEW.md) surfaced 2 critical + 6 warning findings. All were addressed in the fix pass: CR-01 (coercion idempotency), CR-02 (list target undefined detection), WR-01 (reserved prefix guard + builtin shadowing), WR-02 (duplicate function def error), WR-03 (stale attrs after class swap), WR-04 (poison overwrite doc), WR-05 (v1.0 limitation documented), WR-06 (visitor coverage test). 11 new tests were added, bringing the total to 38 analyzer tests / 200 suite-wide.

The Phase 4 generator can read the analyzed AST verbatim and never re-derive any semantic decision.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
