---
phase: "05-cli-runtime-pipeline-integration"
plan: 3
subsystem: cli
tags: [cli, tdd, red, runtime-errors, CLI-04, test]

requires:
  - phase: "05-02"
    provides: "cli.py wired to real transpile(); exec branch routes learner runtime errors through _internal_error_message (Plan 03 changes this)"

provides:
  - "tests/test_cli.py: C-14 rewritten RED (expects 'Error on line' + '→', not 'Something went wrong inside Atena')"
  - "tests/test_cli.py: C-20–C-25 new CLI-04 stubs — all failing (RED) encoding D-03/D-04/D-05 contract"

affects:
  - "05-04"

tech-stack:
  added: []
  patterns:
    - "TDD RED pattern: write failing tests that encode the observable contract before implementing it"
    - "Monkeypatch transpile to inject controlled Python code that raises target runtime exceptions"
    - "Canonical assertion set: 'Error on line' in err, '→' in err, 'Traceback' not in err, raw class name not in err"

key-files:
  created: []
  modified:
    - tests/test_cli.py

key-decisions:
  - "C-14 rewritten: 'Something went wrong inside Atena' → NOT in err (D-04); 'Error on line' + '→' → IN err (D-05)"
  - "C-20–C-25 each target a distinct curated exception (IndexError, ZeroDivisionError, KeyError, ValueError, MemoryError/generic) per D-03 catalog"
  - "C-24 uses MemoryError as representative uncurated exception; asserts 'Error on line' OR 'while running your program' (generic fallback)"
  - "C-25 is a second ZeroDivisionError monkeypatch test confirming no-Traceback rule holds (black-box style via monkeypatch)"
  - "All 7 tests intentionally FAIL at this plan boundary — RED state is the goal; Plan 04 makes them GREEN"

requirements-completed:
  - CLI-04

duration: "1min"
completed: "2026-06-14"
---

# Phase 05 Plan 03: CLI-04 RED Test Stubs Summary

**TDD RED phase: C-14 rewritten and C-20–C-25 added — all 7 new/rewritten tests FAIL as intended, encoding the D-03/D-04/D-05 runtime-error translation contract for Plan 04 to implement.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-14T22:44:51Z
- **Completed:** 2026-06-14
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Rewrote `test_c14_exec_runtime_error_no_traceback` (RED): removed the assertion that "Something went wrong inside Atena" appears; added assertions that "Something went wrong inside Atena" is NOT present, "Error on line" IS present, and "→" IS present — encoding the D-04/D-05 requirement that learner divide-by-zero is a runtime error, not an internal bug
- Added `test_c20_runtime_index_error` (RED): IndexError from out-of-range `items[5]`; asserts "Error on line" + "→" in err, "IndexError" not in err
- Added `test_c21_runtime_zero_division` (RED): ZeroDivisionError from `10 / 0`; asserts canonical format + "divide by zero" or "denominator" in message (D-03 wording)
- Added `test_c22_runtime_key_error` (RED): KeyError from `x["missing"]`; asserts "Error on line" + "→" in err, "KeyError" not in err
- Added `test_c23_runtime_value_error_remove` (RED): ValueError from `x.remove(99)`; asserts canonical format, "ValueError" not in err
- Added `test_c24_runtime_generic_uncurated` (RED): MemoryError as uncurated exception; asserts no Traceback, no class name, either "Error on line" or "while running your program" present (generic fallback)
- Added `test_c25_runtime_error_no_traceback_subprocess` (RED): ZeroDivisionError monkeypatch; asserts "Error on line" + no Traceback + no class name (confirms the no-traceback rule holds for the canonical path)

## Task Commits

1. **Task 1: Rewrite C-14 RED and add C-20 through C-25 CLI-04 test stubs** — `45341bc` (test)

## Files Created/Modified

- `tests/test_cli.py` — C-14 rewritten (4 assertion lines changed) + C-20 through C-25 added (274 new lines total; 26 tests total, up from 20)

## Decisions Made

- C-14 now asserts the D-04 split: "Something went wrong inside Atena" is for internal transpiler bugs only; learner runtime errors get "Error on line N: ... → source" (D-05 canonical format)
- C-25 duplicates ZeroDivisionError rather than using subprocess to avoid monkeypatch-in-subprocess complexity; it serves as a belt-and-suspenders "no Traceback in canonical path" check
- All 7 tests are marked `[RED — will pass after Plan 04 implements _runtime_error_message]` in their docstrings for continuity

## RED State Evidence

### New/rewritten tests — FAIL (expected)

```
tests/test_cli.py::test_c14_exec_runtime_error_no_traceback FAILED
tests/test_cli.py::test_c20_runtime_index_error FAILED
tests/test_cli.py::test_c21_runtime_zero_division FAILED
tests/test_cli.py::test_c22_runtime_key_error FAILED
tests/test_cli.py::test_c23_runtime_value_error_remove FAILED
tests/test_cli.py::test_c24_runtime_generic_uncurated FAILED
tests/test_cli.py::test_c25_runtime_error_no_traceback_subprocess FAILED

7 failed in 0.06s
```

### Failure reason (correct for RED)

All 7 tests fail because `cli.py` still routes learner runtime errors through `_internal_error_message`, which produces:

```
"Something went wrong inside Atena — this isn't your fault. Please share your program so we can fix it."
```

- C-14 fails: "Something went wrong inside Atena" IS in err (assertion: must NOT be)
- C-20–C-23, C-25 fail: "Error on line" is NOT in err (assertion: must be)
- C-24 fails: neither "Error on line" nor "while running your program" is in err (assertion: one must be)

This is the correct RED state — the tests encode the desired behavior; the implementation to satisfy them is Plan 04's job.

### Pre-existing tests — PASS (no regression)

```
tests/test_cli.py::test_c1_run_existing_file_executes PASSED
tests/test_cli.py::test_c2_build_existing_file_emits_py PASSED
tests/test_cli.py::test_c3_run_missing_file_plain_english_error PASSED
tests/test_cli.py::test_c4_build_missing_file_plain_english_error PASSED
tests/test_cli.py::test_c5_help_no_traceback PASSED
tests/test_cli.py::test_c6_subcommand_help_no_traceback PASSED
tests/test_cli.py::test_c7_internal_error_no_line PASSED
tests/test_cli.py::test_c8_internal_error_with_line PASSED
tests/test_cli.py::test_c9_no_subcommand_no_traceback PASSED
tests/test_cli.py::test_c10_unreadable_file PASSED
tests/test_cli.py::test_c11_directory_as_file_plain_english_error PASSED
tests/test_cli.py::test_c12_non_utf8_file_plain_english_error PASSED
tests/test_cli.py::test_c13_build_unwritable_output_plain_english_error PASSED
tests/test_cli.py::test_c15_run_prints_program_output PASSED
tests/test_cli.py::test_c16_build_emits_py_file PASSED
tests/test_cli.py::test_c17_transpile_errors_exit_nonzero_run PASSED
tests/test_cli.py::test_c17b_transpile_errors_exit_nonzero_build PASSED
tests/test_cli.py::test_c18_school_atena_smoke PASSED
tests/test_cli.py::test_c19_build_show_flag PASSED

19 passed, 7 deselected in 0.72s
```

Zero regressions in C-1 through C-13, C-15 through C-19.

## TDD Gate Compliance

This is an explicit TDD RED plan — the plan frontmatter sets `type: execute` (not `type: tdd`), but the objective mandates RED-first ordering:

- RED gate: `test(05-03)` commit `45341bc` present — CONFIRMED
- GREEN gate: deferred to Plan 04 (this plan intentionally ends in RED state)

## Deviations from Plan

None — plan executed exactly as written. The 7 tests all fail for the correct reason (cli.py still uses _internal_error_message for exec branch). No pre-existing tests regressed.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Tests use monkeypatch with controlled in-memory Python snippets — no user input touches this plan.

T-05-03-A mitigated: All 7 new tests explicitly assert raw exception class names (IndexError, ZeroDivisionError, KeyError, ValueError, MemoryError) are NOT in stderr — these RED assertions encode the no-jargon contract for Plan 04.

## Known Stubs

None — this plan is test-only. The production code that satisfies these tests is Plan 04's deliverable.

## Self-Check: PASSED

- [x] `tests/test_cli.py` has `test_c20_runtime_index_error` — VERIFIED
- [x] `tests/test_cli.py` has C-14 asserting "Something went wrong inside Atena" NOT in err — VERIFIED
- [x] `tests/test_cli.py` has C-14 asserting "Error on line" in err — VERIFIED
- [x] C-14, C-20–C-25 all FAIL (RED state) — VERIFIED (7 failed in 0.06s)
- [x] C-1 through C-13, C-15 through C-19 all PASS — VERIFIED (19 passed)
- [x] Commit `45341bc` (Task 1: RED stubs) — FOUND
- [x] All 26 tests collected without syntax error — VERIFIED

---
*Phase: 05-cli-runtime-pipeline-integration*
*Completed: 2026-06-14*
