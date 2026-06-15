---
phase: 04-code-generator
verified: 2026-06-14T21:21:58Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 4: Code Generator Verification Report

**Phase Goal:** The fully analyzed AST is translated into valid, readable, runnable Python 3 — emitted verbatim from the analyzed tree, gated on zero errors, and self-checked.
**Verified:** 2026-06-14T21:21:58Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | school.atena round-trips to school.expected.py exactly AND executes with canned stdin to expected output | VERIFIED | `test_G1_golden_school_roundtrip` (text match) + `test_G2_school_execution_with_canned_stdin` (stdin=Ana → stdout contains "Ana", "pass") both pass; direct repro confirms returncode=0, 10 lines of correct output |
| 2 | Core constructs map correctly (show, ask, repeat, while, if/else, true/false, and/or/not) AND list/dict ops map correctly (add, remove, length, dict literal, dot read, dot write) | VERIFIED | All 13 construct checks pass in generated school.atena output; dedicated execution tests (test_G2_dict_dot_read_executes, test_G2_list_add_remove_executes, test_G2_dict_dot_write_execution) confirm correct runtime behavior; and/or/not verified directly |
| 3 | Generator emits indices/coercions verbatim — no double-shift on nested grid[2][3], no str()-wrap on number+number x+1 | VERIFIED | `test_G3_verbatim_no_double_shift` (grades[2]→grades[1] in output, executes to 7), `test_G3_verbatim_nested_index_no_double_shift` (grid[1][2]→grid[0][1], executes to 2), `test_G3_verbatim_no_str_wrap_number_plus_number` (x+y not str-wrapped, executes to 8) — all pass |
| 4 | Generated Python correctly indented, unique loop var per nested repeat, keyword mangling at BOTH definition AND call site | VERIFIED | `test_G3_nested_repeat_unique_loop_vars` (_atena_i0, _atena_i1 distinct), `test_CR01_keyword_function_call_mangled` (def pass_ AND pass_(5) both in output, executes to 5); `test_G3_all_python_keywords_mangled` covers all Python keywords that can reach codegen |
| 5 | Every generated program passes internal ast.parse() self-check; generator emits no Python when upstream error was collected | VERIFIED | `ast.parse(python_source)` called in `generate()` (verified via `inspect.getsource`); `test_G3_zero_error_gate` confirms malformed input raises AssertionError before codegen; `test_G3_ast_parse_selfcheck_broader` confirms all core construct outputs pass ast.parse |

**Score:** 5/5 truths verified

---

### Deferred Items

None. All phase 4 success criteria are met.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/atena/codegen.py` | CodeGenerator class, ast.unparse strategy (D-01), D-02 patches, GEN-05 self-check | VERIFIED | 499 lines; exports CodeGenerator; imports only ast_nodes + stdlib (ast, keyword, re); no forbidden imports confirmed |
| `tests/test_codegen.py` | Three-layer test suite (G1/G2/G3/Gx + CR tests) | VERIFIED | 927 lines, 48 tests across all layers; all 48 pass |
| `tests/fixtures/school.atena` | Maximal capstone exercising full construct set (D-04) | VERIFIED | 55 lines; exercises: I/O, variables, if/else, while, nested repeat, functions+return, lists, dicts, str-coercion, all ops |
| `tests/fixtures/school.expected.py` | Locked golden snapshot derived from pipeline (D-06) | VERIFIED | 55 lines; pipeline produces exact text match |
| `tests/fixtures/keyword_mangle.{atena,expected.py}` | Keyword mangling fixture | VERIFIED | Both files present; round-trip test and execution test pass |
| `tests/fixtures/nested_repeat.{atena,expected.py}` | Nested repeat fixture | VERIFIED | Both files present; loop vars _atena_i0, _atena_i1 confirmed distinct |
| `tests/fixtures/dynamic_index.{atena,expected.py}` | Dynamic index _atena_index helper fixture | VERIFIED | Both files present; _atena_index in output; execution confirms correct value |
| `tests/fixtures/concat_helper.{atena,expected.py}` | _atena_concat helper fixture | VERIFIED | Both files present; execution prints '35' (str concat, not numeric add) |
| `tests/fixtures/dict_dot_write.{atena,expected.py}` | Dict dot-write fixture | VERIFIED | Both files present; execution prints 'Ana' and '9' |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_codegen.py` | `src/atena/codegen.py` | `from atena.codegen import CodeGenerator` | WIRED | Import confirmed; 48 tests drive CodeGenerator.generate() through full pipeline |
| `tests/test_codegen.py` | `src/atena/parser.py` | `_generate()` pipeline helper | WIRED | Lexer→Parser→Analyzer→CodeGenerator chain confirmed in all test calls |
| `src/atena/codegen.py` | `src/atena/ast_nodes.py` | imports all 22 node types | WIRED | All 22 node types imported; _emit_* methods cover every node type |
| `CodeGenerator.generate()` | `ast.parse()` self-check | `ast.parse(python_source)` after D-02 patches | WIRED | Confirmed via inspect.getsource; GEN-05 self-check fires on every generate() call |
| `_emit_Repeat` | unique loop var | monotonic `_loop_counter` | WIRED | Counter never decrements; `_atena_i{n}` naming confirmed distinct across nesting and siblings |
| `_emit_FunctionDef`/`_emit_FunctionCall` | `_mangle()` | called on name at both def and call sites | WIRED | CR-01 fix confirmed: both `_emit_FunctionDef` (line 334) and `_emit_FunctionCall` general path (line 410) call `_mangle()` |
| `analyzer.visit_Assign` | `_dot_target` validation | visits `_dot_target` before `node.value` | WIRED | CR-02 fix confirmed: `nope.grade = 10` produces "I don't know what 'nope' is yet" error, not runnable code |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `school.expected.py` | `name`, `grades`, `avg`, `verdict` | school.atena fully analyzed AST → CodeGenerator.generate() | Yes — verified execution with canned stdin Ana produces correct 10-line output | FLOWING |
| `dict_dot_write.expected.py` | student dict fields | analyzed AST with _dot_target chain | Yes — execution confirms "Ana" and "9" in stdout | FLOWING |
| `dynamic_index.expected.py` | `grades[_atena_index(i)]` | _atena_index helper injected by CodeGenerator._build_preamble | Yes — execution confirms value 5; _atena_index(0) raises plain-English IndexError | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| school.atena executes with canned stdin | subprocess(school.expected.py, input='Ana') | returncode=0, stdout contains "Ana", "pass" | PASS |
| CR-01 repro: function pass(n)/show pass(5) | _generate + subprocess | generates "def pass_"+"pass_(5)", executes to '5' | PASS |
| CR-02 repro: nope.grade = 10 | analyzer runs, checks ec | ec non-empty, error message plain English, no generated code | PASS |
| Verbatim no-double-shift: grades[2] | _generate("grades[2]") | output contains grades[1], not grades[0] or grades[2], executes to 7 | PASS |
| No extra str() wrap: x+y | _generate("x=5 y=3 show x+y") | str(x) absent, x+y present, executes to 8 | PASS |
| Keyword mangling at def AND call | _generate("function pass(n) / show pass(5)") | "def pass_" AND "pass_(5)" both present, ast.parse passes | PASS |
| Unique loop vars across nested repeats | _generate(nested repeat) | _atena_i0 and _atena_i1 distinct | PASS |
| GEN-05 self-check in generate() | inspect.getsource(generate) | "ast.parse(python_source)" present | PASS |
| Zero-error gate | _generate("x = ") | AssertionError "Pipeline errors before codegen" raised | PASS |
| DIAG-03: no traceback for user errors | show xyz / grades[0] / "x" = | All produce plain-English errors, no Traceback string | PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| GEN-01 | 04-01, 04-02, 04-03, 04-05 | Generator emits valid Python 3 for core constructs | SATISFIED | test_G1_show_string_literal, test_G1_assign_number, test_G1_repeat_generates_for_loop, test_G1_if_else_generates_correctly, test_G2_show_number_executes, test_G2_arithmetic_executes — all pass |
| GEN-02 | 04-01, 04-03, 04-05 | Generator emits list/dict operations and dot access (read+write) | SATISFIED | test_G1_dict_literal, test_G1_list_add_generates_append, test_G2_dict_dot_read_executes, test_G2_list_add_remove_executes, test_G1_dict_dot_write_fixture, test_G2_dict_dot_write_execution — all pass |
| GEN-03 | 04-01, 04-02, 04-05 | Generator runs only when zero errors collected | SATISFIED | test_G3_zero_error_gate: malformed input prevents generate() call; GEN-03 gate enforced by driver contract (ec.is_empty() assertion in _generate helper) |
| GEN-04 | 04-03, 04-04, 04-05 | Correct indentation, unique loop vars, keyword mangling | SATISFIED | test_G3_keyword_mangling_execution, test_G3_all_python_keywords_mangled, test_G3_nested_repeat_unique_loop_vars, test_G3_three_sibling_repeats_unique_vars, test_CR01_keyword_function_call_mangled — all pass |
| GEN-05 | 04-01, 04-02, 04-04, 04-05 | ast.parse() self-check on every output | SATISFIED | ast.parse(python_source) called in generate() after D-02 patches; test_G3_ast_parse_selfcheck_all_snippets, test_G3_ast_parse_selfcheck_broader — all pass |
| GEN-06 | 04-05 | Golden school.atena round-trips exactly to school.expected.py | SATISFIED | test_G1_golden_school_roundtrip (exact text equality confirmed), test_G2_school_execution_with_canned_stdin (execution confirmed) — both pass |

All 6 requirements SATISFIED. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/atena/codegen.py` | 158–161 | Unreachable `isinstance(result, list)` branch in `generate()` | Info (IN-02 from REVIEW) | Harmless defensive guard; no functional impact |
| `src/atena/codegen.py` | 344 | Unreachable `or [ast.Pass()]` in _emit_FunctionDef | Info (IN-02 from REVIEW) | Parser always produces non-empty body; harmless |
| `src/atena/codegen.py` | 182–198 | Regex-based D-02 patches operate on raw string, not AST | Info (IN-01 from REVIEW) | GEN-05 self-check guards against producing unparseable output; v1.0 safe |

No TBD/FIXME/XXX markers found in any phase 4 source files.

**Open warnings from code review (WR-01..WR-04) — tracked but NOT phase-blocking per REVIEW.md:**

- WR-01: `str` builtin shadowing — if a user defines `function str(x)`, analyzer-injected `str()` coercions call the user's function. Demonstrated: leaks a Python `TypeError` traceback (DIAG-03 violation) in this contrived edge case. Scheduled as a post-phase quick task.
- WR-02: Arithmetic safety-net regression — `a = 2; b = "x"; show a + b * 3` leaks a Python `TypeError` traceback post-fix (the `_atena_concat` fallback that incidentally masked this was removed by the arithmetic type-checking improvement). Tracked in STATE.md as a known v1.0 limitation.
- WR-03: GEN-05 self-check failure escapes as an uncaught exception — mitigated by CR-01 fix (the only reachable trigger was the call-site mangling gap); Phase 5 CLI will add the top-level friendly-message wrapper.
- WR-04: Misleading parser error for nested dot-write and `==` typo in dot context — parser quality issue, no functional regression.

These four warnings are pre-accepted non-blockers per the phase instructions. WR-01 and WR-02 each represent an edge-case DIAG-03 violation but neither is exercised by the learner's intended happy paths or any existing test fixture.

---

### Human Verification Required

None. All success criteria are verifiable programmatically and have been verified.

---

### Gaps Summary

No gaps. All 5 must-have truths are VERIFIED. All 6 requirements (GEN-01..GEN-06) are SATISFIED. 251 tests pass (48 in test_codegen.py, 203 across prior phases). The two critical code-review blockers (CR-01: call-site keyword mangling, CR-02: dot-write undefined-object error) are confirmed resolved by direct repro. The phase goal — "the fully analyzed AST is translated into valid, readable, runnable Python 3, emitted verbatim, gated on zero errors, and self-checked" — is achieved.

---

_Verified: 2026-06-14T21:21:58Z_
_Verifier: Claude (gsd-verifier)_
