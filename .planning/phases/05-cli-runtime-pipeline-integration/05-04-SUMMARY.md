---
phase: "05-cli-runtime-pipeline-integration"
plan: 4
subsystem: cli
tags: [cli, tdd, green, runtime-errors, CLI-03, CLI-04, traceback-suppression]

requires:
  - phase: "05-03"
    provides: "7 RED tests (C-14, C-20–C-25) encoding D-03/D-04/D-05 runtime-error contract"

provides:
  - "_runtime_error_message(exc, source_lines) in src/atena/cli.py — curated dispatch for ZeroDivisionError/KeyError/ValueError/IndexError + generic fallback"
  - "exec except-block calls _runtime_error_message (D-04 split: internal bugs vs learner runtime errors)"
  - "Phase 5 fully GREEN: 276 tests passing, all 5 ROADMAP criteria satisfied"

affects:
  - "CLI-03: compile-time error paths already green"
  - "CLI-04: runtime error translation now implemented"

tech-stack:
  added:
    - "traceback (stdlib) — imported in cli.py for extract_tb() line recovery"
  patterns:
    - "TDD GREEN pattern: implement production code to satisfy RED test contracts without modifying tests"
    - "D-04 split: _internal_error_message for transpiler bugs; _runtime_error_message for learner runtime errors"
    - "D-05 canonical format: 'Error on line N: message\\n  → source_line'"
    - "D-07 best-effort line recovery: traceback.extract_tb() last-frame lineno mapped to source_lines"
    - "D-03 curated dispatch: isinstance() type-based exception dispatch, no string-based matching"

key-files:
  created: []
  modified:
    - src/atena/cli.py

key-decisions:
  - "_runtime_error_message uses isinstance() dispatch (not string-based) — immune to exception class name spoofing (T-05-04-D)"
  - "Only the last traceback frame lineno is used — internal Atena frames never surfaced (T-05-04-C mitigated)"
  - "source_lines passed from source.splitlines() already in scope in main() — no extra read required"
  - "Generic fallback still uses 'Error on line N:' canonical format — never 'Something went wrong inside Atena' for learner programs"
  - "_internal_error_message preserved unchanged — C-7 and C-8 still pass; D-04 boundary is clean"

metrics:
  duration: "3min"
  completed: "2026-06-14"
  tasks: 2
  files: 1
---

# Phase 05 Plan 04: Runtime Error Translation (GREEN) Summary

**TDD GREEN phase: _runtime_error_message() implemented in cli.py — all 7 RED tests (C-14, C-20–C-25) now GREEN, full 276-test suite passing, Phase 5 ROADMAP criteria all satisfied.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-14T22:50:00Z
- **Completed:** 2026-06-14
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented `_runtime_error_message(exc: BaseException, source_lines: list[str]) -> str` in `src/atena/cli.py` immediately after `_internal_error_message`
- Added `import traceback` (stdlib) to the import block
- Curated exception dispatch covers ZeroDivisionError, KeyError, ValueError, IndexError (with Atena-sentinel check), and generic fallback
- Line number recovery uses `traceback.extract_tb(exc.__traceback__)[-1].lineno` (D-07 best-effort)
- Source line display maps Python lineno to `source_lines[lineno - 1]` when within bounds; empty string otherwise
- Canonical D-05 format: `Error on line {N}: {message}\n  → {source_line}` for all curated and generic paths
- Updated exec except-block in `main()` to call `_runtime_error_message(exc, source.splitlines())` — removed the Plan 02 TODO comment
- `_internal_error_message` left completely unchanged; transpile-error path (C-7, C-8) unaffected

## Task Commits

1. **Task 1: Implement _runtime_error_message() and wire exec except-block** — `bf966bb` (feat)
2. **Task 2: Full suite green check** — verified 276/276 passing; no separate commit needed (verification only)

## Files Created/Modified

- `src/atena/cli.py` — added `import traceback`; added `_runtime_error_message()` (52 lines); updated exec except-block (3 lines changed, TODO removed)

## GREEN Evidence

### Before (Plan 03 RED state)

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

### After (Plan 04 GREEN state)

```
tests/test_cli.py::test_c14_exec_runtime_error_no_traceback PASSED
tests/test_cli.py::test_c20_runtime_index_error PASSED
tests/test_cli.py::test_c21_runtime_zero_division PASSED
tests/test_cli.py::test_c22_runtime_key_error PASSED
tests/test_cli.py::test_c23_runtime_value_error_remove PASSED
tests/test_cli.py::test_c24_runtime_generic_uncurated PASSED
tests/test_cli.py::test_c25_runtime_error_no_traceback_subprocess PASSED

7 passed, 19 deselected in 0.02s
```

### Full suite

```
276 passed in 0.92s
```

Zero regressions. All pre-existing tests (C-1 through C-13, C-15 through C-19, and all 250 non-CLI tests) still pass.

## ROADMAP Success Criteria

All 5 Phase 5 criteria satisfied:

1. `echo "Ana" | python -m atena run examples/school.atena` → exit 0, "Welcome, Ana" in stdout — PASS
2. `python -m atena build examples/school.atena --show` → exit 0, generated Python in stdout — PASS
3. `printf 'show "\n' | python -m atena run /tmp/err.atena` → exit 1, "Error on line" in stderr, no Traceback — PASS
4. Runtime ZeroDivisionError → exit 1, "Error on line 1: you tried to divide by zero...", no Traceback — PASS
5. `python -m atena run no_such_file.atena` → "I couldn't find a file called..." in stderr, exit 1 — PASS

## TDD Gate Compliance

- RED gate: `test(05-03)` commit `45341bc` — present (Plan 03)
- GREEN gate: `feat(05-04)` commit `bf966bb` — present (this plan)
- Gate sequence: RED → GREEN — CONFIRMED

## Decisions Made

- `_runtime_error_message` uses `isinstance()` dispatch — type-based, not string-based; safe against exception name spoofing
- Only the last traceback frame lineno is extracted; the traceback object is never printed or surfaced (T-05-04-C mitigated)
- The generic fallback still uses `Error on line N:` canonical format (not "Something went wrong inside Atena") — the D-04 split is clean
- `codegen.py` was NOT modified — the D-06 line-marker enhancement was deemed optional in the plan and unnecessary given that best-effort line recovery works correctly for the test cases

## Deviations from Plan

**1. [Rule 3 - Optional feature omitted by design] codegen.py not modified**

- **Issue:** The plan marked the `_atena_index` codegen.py change as "optional" (D-06). The best-effort line recovery via `traceback.extract_tb()` correctly maps to Atena source lines for the generated code without requiring line markers in the generated Python.
- **Decision:** No change to `codegen.py` — all 7 tests pass, all 5 ROADMAP criteria pass, with zero modifications to the codegen layer.
- This is not a deviation from required behavior — the plan explicitly marked the change as optional.

## Known Stubs

None — `_runtime_error_message()` is fully implemented with real curated dispatch and generic fallback. No hardcoded placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The `_runtime_error_message()` function:
- Never prints the exception's `str()` directly to the user (T-05-04-A: KeyError key is formatted via `!r` inside a descriptive sentence)
- Only uses the last traceback frame's lineno; the traceback itself is never surfaced (T-05-04-C mitigated)
- Type-based dispatch via `isinstance()` — immune to class-name spoofing (T-05-04-D accepted)

## Self-Check: PASSED

- [x] `src/atena/cli.py` contains `_runtime_error_message` — VERIFIED
- [x] `src/atena/cli.py` contains `import traceback` — VERIFIED
- [x] exec except-block calls `_runtime_error_message` (not `_internal_error_message`) — VERIFIED
- [x] C-14, C-20–C-25 all PASS (GREEN) — VERIFIED (7 passed in 0.02s)
- [x] C-7 and C-8 still PASS — VERIFIED (26 passed in 0.08s for full test_cli.py)
- [x] Full suite 276/276 PASS — VERIFIED (276 passed in 0.92s)
- [x] Commit `bf966bb` (Task 1: feat) — FOUND
- [x] All 5 ROADMAP criteria — VERIFIED

---
*Phase: 05-cli-runtime-pipeline-integration*
*Completed: 2026-06-14*
