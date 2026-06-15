---
phase: 06-packaging-curriculum
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - README.md
  - examples/01-show.atena
  - examples/02-ask.atena
  - examples/03-variables.atena
  - examples/04-conditionals.atena
  - examples/05-while.atena
  - examples/06-repeat.atena
  - examples/07-functions.atena
  - examples/08-lists.atena
  - examples/09-dicts.atena
  - pyproject.toml
  - tests/test_examples.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase 6 packaging and curriculum deliverables: the public README, the 9-rung `.atena` example ladder, `pyproject.toml`, and the subprocess-based example test suite. The packaging metadata is sound (LICENSE present, `atena` importable, zero runtime deps, correct `[project.scripts]` entry point), indentation is consistent (all spaces, no tab mixing), and the `.atena` sources are free of Python jargon (no `str()`, `print`, etc.).

The headline defect is a **direct violation of Atena's core "integers only / no floats" contract**: `examples/03-variables.atena` divides `10 / 3` and emits `Quotient: 3.3333333333333335`, a float. The same violation is documented verbatim in the README's arithmetic section (which both shows a division example AND claims "Atena uses integers only... No floats" on the same page), and it recurs in the tested `school.atena` capstone (`avg = total / 4` → `7.5`). Because every reviewed artifact in this phase is the project's public face — the first thing a learner sees — shipping an example that contradicts the language's stated guarantee is a blocker.

Secondary issues: the README documents an error message that does not match the real CLI output (a broken contract), and two example tests are so weak they actively mask the float-division bug. A few documentation inconsistencies round out the findings.

The root cause of the float behavior lives in `src/atena/codegen.py` (mapping `/` → `ast.Div()`), which is outside this phase's review scope. The findings below are scoped to the reviewed artifacts that expose, document, and fail to catch the defect.

## Critical Issues

### CR-01: Division in examples violates the "integers only / no floats" language contract

**File:** `examples/03-variables.atena:19` (also `README.md:120` and the tested `examples/school.atena`)
**Issue:**
The project's defining contract (CLAUDE.md: "Strings/Numbers (v1.0): integers only"; README line 123/226: "Atena uses integers only (whole numbers)" / "No floats") is broken by the very example meant to teach arithmetic.

`examples/03-variables.atena` line 19:
```
show "Quotient: " + (a / b)
```
With `a = 10`, `b = 3`, the program prints:
```
Quotient: 3.3333333333333335
```
That is a float — exactly what the language promises will never happen. Verified directly: `build --show` shows the generated Python is `str(a / b)`, i.e. Python true division (`ast.Div()`), so *any* `/` yields a float. The README's own arithmetic example `quotient = 10 / 2` (line 120) prints `5.0`, and the tested capstone `school.atena` (`avg = total / 4`, total 30) prints `Your average is: 7.5`.

A complete-beginner learner following rung 3 immediately sees a 17-digit float for "10 divided by 3" in a language whose whole pitch is "integers only, no scary syntax." This is the most prominent example in the curriculum and it falsifies the central guarantee.

**Fix:**
The correct fix is at the transpiler level (out of this phase's scope): map Atena `/` to integer/floor division (`ast.FloorDiv()`) in `src/atena/codegen.py` so `10 / 3 → 3` and `10 / 2 → 5`, consistent with the integer-only contract. That is the real fix and should be tracked against the codegen.

Within this phase's reviewable surface, the example must not advertise broken behavior. Until the transpiler emits integer division, change the example to a case whose stated contract holds, e.g. choose operands that divide evenly and add a teaching note, or drop the division line:
```
# Divide (integers only in Atena v1.0 — use evenly divisible numbers)
c = 12
d = 4
show "Quotient: " + (c / d)
```
Do NOT ship the example as-is: a float on rung 3 is a contract violation a learner will hit on first run.

## Warnings

### WR-01: README documents an error message that does not match the actual CLI output

**File:** `README.md:81`
**Issue:**
The README presents Atena's plain-English error as a literal, exact output a learner will see (lines 80-83). The documented text is:
```
Error on line 2: I don't know what "result" is. Did you forget to create it?
```
The real CLI output (verified by running the documented program) is:
```
Error on line 2: I don't know what "result" is yet. Did you forget to create it first?
```
The words "yet" and "first" are present in reality but missing from the README. Since the README frames this as Atena's actual voice/safety-net behavior, a mismatch undermines trust and will confuse anyone comparing the doc to their terminal. The error-message wording is a user-facing contract for a teaching tool.

**Fix:**
Update README lines 81-83 to match the real message verbatim:
```
Error on line 2: I don't know what "result" is yet. Did you forget to create it first?
  → show "Result: " + result
```
(Or, better, generate the doc snippet from the real CLI so it cannot drift.)

### WR-02: Tests 01 and 03 use assertions too weak to detect wrong output — they mask CR-01

**File:** `tests/test_examples.py:38-59`
**Issue:**
`test_example_01_show_runs_to_completion` and `test_example_03_variables_runs_to_completion` only assert `result.stdout.strip() != ""` plus "no Traceback." They never check *what* was printed. As a result, `03-variables` passes green while printing the spec-violating float `3.3333333333333335` (CR-01). A test that asserts only "something was printed" provides almost no regression protection and actively hides the most important defect in the phase. The sibling tests (04-09) correctly assert specific substrings; 01 and 03 are the outliers.

**Fix:**
Assert the actual expected output. For 03, this also doubles as a regression guard for the integer-division fix:
```python
assert "Sum: 13" in result.stdout
assert "Difference: 7" in result.stdout
assert "Product: 30" in result.stdout
assert "Quotient: 3" in result.stdout   # integer division, not 3.3333...
assert "3.333" not in result.stdout      # explicit guard against float regression
```
For 01:
```python
assert "Hello, world!" in result.stdout
assert "The answer is: 42" in result.stdout
```

### WR-03: `school.atena` is exercised by the test suite but produces float output, and its capstone test cannot catch it

**File:** `tests/test_examples.py:159-174`
**Issue:**
`test_example_school_atena_capstone` asserts only `"Welcome, Ana" in result.stdout`. The capstone computes `avg = total / 4` and prints `Your average is: 7.5` (a float — same root cause as CR-01). The single-substring assertion lets the capstone ship float output undetected. For a "brings all nine concepts together" capstone that the README (line 258) recommends students reproduce on their own, silently emitting floats teaches the wrong mental model. (Note: `school.atena` itself is outside this phase's file scope, but its test is in scope and is too weak to protect it.)

**Fix:**
Strengthen the capstone assertion to pin numeric output, and fix the underlying division (CR-01):
```python
assert "Welcome, Ana" in result.stdout
assert "Your average is: 7" in result.stdout   # integer average after div fix
assert "7.5" not in result.stdout
```

### WR-04: `pyproject.toml` claims production-stable + Python 3.13 support that the test matrix does not prove

**File:** `pyproject.toml:14,21`
**Issue:**
The package advertises `"Development Status :: 5 - Production/Stable"` and `"Programming Language :: Python :: 3.13"`. CLAUDE.md states the intended matrix is 3.11–3.14, but there is no tox/nox/CI matrix in the repo and the only test suite ran here against a single interpreter (3.12). Claiming Production/Stable and per-version support classifiers without a multi-version test gate is an unverified promise — if a 3.13-only or 3.11-only behavior breaks, nothing catches it, yet PyPI metadata asserts the support. The classifiers also omit `3.14` despite CLAUDE.md naming it as a target.

**Fix:**
Either (a) add a real multi-version test matrix (tox/nox or CI) to back the classifiers, or (b) align the metadata with what is actually verified. Add the missing `"Programming Language :: Python :: 3.14"` classifier if 3.14 is a supported target, and consider `Development Status :: 4 - Beta` until a version matrix exists.

## Info

### IN-01: README snippet for lists does not match the actual example file

**File:** `README.md:181` vs `examples/08-lists.atena:6`
**Issue:**
README line 181 shows `grades = [8, 9, 7]` while the actual `examples/08-lists.atena` uses `grades = [8, 6, 9]`. The README snippet is illustrative (not a literal quote of the file), so this is low-severity, but the discrepancy is needless and can confuse a learner who opens the file expecting the README's values.
**Fix:** Make the README snippet match the file (`[8, 6, 9]`) or use a clearly generic placeholder.

### IN-02: README "first program" output relies on the float-division contract being intact elsewhere

**File:** `README.md:33,49`
**Issue:**
The first-program example (`show "Today's count: " + 5`) correctly prints `Today's count: 5` and the prose (line 49) reassures learners that "you never need to worry about converting types." This is accurate for string+int concatenation, but sits adjacent to the broken division contract (CR-01). Once division is fixed to integer semantics, re-verify all README numeric outputs (line 46, 120) print as documented. Tracking note, not a standalone defect.
**Fix:** After the CR-01 division fix, re-run every README code snippet and confirm the documented outputs still hold.

### IN-03: `addopts = "-v"` hardcodes verbose output for all runs

**File:** `pyproject.toml:35`
**Issue:**
Forcing `-v` in `addopts` is a style/ergonomics choice that applies to every invocation (CI logs, local runs) and cannot be easily turned off per-run without `-q` overrides. Harmless, but verbosity is better left to the invoker. Not a bug.
**Fix:** Optional — drop `-v` from `addopts` and let callers add it when wanted.

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
