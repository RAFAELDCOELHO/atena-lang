---
phase: "05-cli-runtime-pipeline-integration"
plan: 2
subsystem: cli
tags: [cli, transpile, exec, run, build, argparse, tdd, pipeline]

requires:
  - phase: "05-01"
    provides: "transpile(source, filename) -> str | None driver with between-phase gating"

provides:
  - "cli.py: working atena run (exec in-process) and atena build (emits .py) wired to real transpile()"
  - "cli.py: --show flag on build prints generated Python 3 source to stdout"
  - "cli.py: sys.exit(1) when transpile() returns None (errors already on stderr)"
  - "cli.py: exec uses {'__name__': '__main__'} namespace"
  - "tests/test_cli.py: C-15 through C-19 covering run/build/error/smoke behaviors"
  - "school.atena smoke test: atena run examples/school.atena exits 0, prints expected output"

affects:
  - "05-03"
  - "05-04"

tech-stack:
  added: []
  patterns:
    - "transpile-failure path: result is None → sys.exit(1) (pipeline owns error printing)"
    - "exec in-process with {'__name__': '__main__'} namespace (D-01)"
    - "build --show: writes file then optionally prints to stdout"
    - "subprocess smoke test with canned stdin via input= parameter"

key-files:
  created: []
  modified:
    - src/atena/cli.py
    - tests/test_cli.py

key-decisions:
  - "NotImplementedError stub path removed; real transpile() never raises it"
  - "result is None triggers sys.exit(1); pipeline.py already printed errors to stderr"
  - "exec() namespace is {'__name__': '__main__'} so learner guard patterns work (D-01)"
  - "--show flag added to _build_parser; prints generated Python after writing file"
  - "C-14 kept as-is (asserts _internal_error_message for exec runtime errors) — Plan 03 replaces with _runtime_error_message (D-04)"

patterns-established:
  - "CLI error routing: transpile errors → pipeline prints to stderr → CLI sys.exit(1)"
  - "CLI output routing: program output → stdout; errors → stderr (cross-cutting)"
  - "school.atena smoke pattern: subprocess.run(..., input='Ana\\n') for ask-based programs"

requirements-completed:
  - CLI-01
  - CLI-02
  - CLI-05
  - CLI-06

duration: "8min"
completed: "2026-06-14"
---

# Phase 05 Plan 02: CLI Wiring Summary

**`atena run` and `atena build` fully wired to real `transpile()`: NotImplementedError stub removed, exec uses `__main__` namespace, `--show` flag exposes generated Python, and C-15 through C-19 tests confirm end-to-end behavior including the school.atena smoke.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-14
- **Completed:** 2026-06-14
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed the `_STUB_PLACEHOLDER` constant and `NotImplementedError` catch block from `cli.py` — the real `transpile()` never raises `NotImplementedError`
- Added `sys.exit(1)` for the `result is None` path (pipeline already printed errors to stderr)
- Updated exec namespace to `{"__name__": "__main__"}` so learner programs using `if __name__ == "__main__":` work correctly
- Added `--show` flag to `_build_parser` — prints generated Python 3 source to stdout after writing the file
- Added C-15 through C-19 tests covering: run prints output, build emits file, transpile errors exit 1, school.atena smoke with canned stdin, build `--show` flag
- ROADMAP criterion #1 confirmed: `echo "Ana" | atena run examples/school.atena` → exit 0, "Welcome, Ana" in stdout

## Task Commits

1. **Task 1: Wire real transpile() into cli.py** - `5797c99` (feat)
2. **Task 2: Add C-15 through C-19 tests** - `46af7be` (feat)

## Files Created/Modified

- `src/atena/cli.py` - Removed stub path, added `--show`, fixed exec namespace, added `result is None` exit
- `tests/test_cli.py` - Added C-15, C-16, C-17, C-17b, C-18, C-19 (126 lines, 6 new tests, 20 total)

## Decisions Made

- `--show` prints `result` after the `Built "..."` message (not before) — consistent with the build path order: write file first, then reveal
- C-14 kept with its current `_internal_error_message` assertion — Plan 03 will rewrite it to `_runtime_error_message` (D-04); the comment `# TODO Plan 03` captures this
- Task 2 is marked TDD but since Task 1 (implementation) landed first, all new tests went GREEN immediately — no RED phase was possible within this sequential plan structure; noted as deviation

## Deviations from Plan

### TDD Phase Order Note

The plan declares Task 2 `tdd="true"`, which implies writing failing tests (RED) before implementation (GREEN). However, the plan also declares Task 1 (implementation) before Task 2 (tests) in sequential order. Since Task 1 was committed first, the new tests in Task 2 went GREEN immediately. This is an artifact of the sequential-task plan structure — no correctness impact; all 20 tests pass and behaviors are fully verified.

None of the deviation rules 1-4 were triggered.

## Issues Encountered

None.

## Verification Results

```
270 passed in 1.03s (0 failed)
```

Full suite: 270 tests green (up from 264 before this plan, net +6 tests).

School.atena smoke:
```
echo "Ana" | python -m atena run examples/school.atena
Enter student name: Welcome, Ana
Your average is: 7.5
Result: pass
...
```

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced.

T-05-02-B mitigated: `BaseException` catch in `cli.py` exec branch wraps all runtime errors; no raw traceback or class name reaches stderr. The TODO comment flags D-04 for Plan 03 (`_runtime_error_message`).

T-05-02-A accepted: `exec()` receives generated Python from a typed AST via `ast.unparse()` — no string-interpolation injection path exists.

## Known Stubs

None — all behaviors are fully wired. The `_internal_error_message` call in the exec branch is temporary (D-04, Plan 03), not a stub — it produces a non-empty message.

## Self-Check: PASSED

- [x] `src/atena/cli.py` has no `_STUB_PLACEHOLDER`, no `NotImplementedError` catch — VERIFIED
- [x] `src/atena/cli.py` has `--show` argument on `_build_parser` — VERIFIED
- [x] `src/atena/cli.py` has `exec(code, {"__name__": "__main__"})` — VERIFIED
- [x] `src/atena/cli.py` has `if result is None: sys.exit(1)` — VERIFIED
- [x] `tests/test_cli.py` has `test_c15` through `test_c19` — VERIFIED
- [x] Commit `5797c99` (Task 1: cli.py wiring) — FOUND
- [x] Commit `46af7be` (Task 2: C-15 through C-19) — FOUND
- [x] 270 tests green — VERIFIED

---
*Phase: 05-cli-runtime-pipeline-integration*
*Completed: 2026-06-14*
