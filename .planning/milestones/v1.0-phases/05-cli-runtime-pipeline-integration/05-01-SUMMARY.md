---
phase: "05-cli-runtime-pipeline-integration"
plan: 1
subsystem: pipeline
tags: [pipeline, transpile, four-phase, wiring, tdd]
dependency_graph:
  requires: [src/atena/lexer.py, src/atena/parser.py, src/atena/analyzer.py, src/atena/codegen.py, src/atena/errors.py]
  provides: [src/atena/pipeline.py::transpile]
  affects: [src/atena/cli.py, tests/test_pipeline.py, tests/test_cli.py]
tech_stack:
  added: []
  patterns: [between-phase-gating, ErrorCollector-injection, GEN-03-codegen-gate, stderr-error-reporting]
key_files:
  created: [src/atena/pipeline.py, tests/test_pipeline.py, tests/test_pipeline_tdd.py]
  modified: [tests/test_cli.py]
decisions:
  - "Between-phase gating: errors.is_empty() checked after each phase; CodeGenerator never called on a partial/error AST (GEN-03 enforced structurally)"
  - "Single shared ErrorCollector injected across all four phases — one errors instance per transpile() call"
  - "filename parameter accepted but not forwarded to phases — reserved for CLI compile() target in Phase 5"
metrics:
  duration: "3 min"
  completed: "2026-06-14"
  tasks: 2
  files_changed: 4
---

# Phase 05 Plan 01: Pipeline Driver (transpile) Summary

**One-liner:** Four-phase pipeline driver `transpile(source, filename) -> str | None` wired with between-phase `errors.is_empty()` gating and GEN-03-compliant codegen guard.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD RED: failing tests for transpile() | 5ea1038 | tests/test_pipeline_tdd.py |
| 1 (GREEN) | Implement transpile() four-phase wiring | 6a58e7a | src/atena/pipeline.py, tests/test_cli.py |
| 2 | Smoke-test the full pipeline with school.atena | 007fd3b | tests/test_pipeline.py |

## What Was Built

`src/atena/pipeline.py` now exports a real `transpile(source: str, filename: str) -> str | None` that:

1. Instantiates a single shared `ErrorCollector`
2. Runs phases in sequence: Lexer → Parser → SemanticAnalyzer → CodeGenerator
3. Gates between phases: any error stops the pipeline, prints `errors.report()` to stderr, returns `None`
4. Only calls `CodeGenerator(program).generate()` when `errors.is_empty()` (GEN-03)

`tests/test_pipeline.py` provides 8 smoke tests covering:
- Happy path: `show 1` → `print(1)`
- Lexer/parser/analyzer error paths each return `None`
- `school.atena` golden fixture: `make_greeting` and `input()` present in output
- Canonical `Error on line` format confirmed in stderr via `capsys`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated C-1 and C-2 in test_cli.py from placeholder to real assertions**
- **Found during:** GREEN phase implementation
- **Issue:** C-1 (`test_c1_run_existing_file_shows_placeholder`) and C-2 (`test_c2_build_existing_file_shows_placeholder`) were testing the `NotImplementedError` placeholder path that only existed when `transpile()` was a stub. Once the real implementation landed, `atena run show 1.atena` outputs `1` and exits 0; `atena build` prints `Built "prog.py".` — neither contains the old placeholder message.
- **Fix:** Renamed and rewrote both tests to assert the real behavior: C-1 checks `"1" in result.stdout`, C-2 checks `'Built "prog.py".' in combined`.
- **Files modified:** `tests/test_cli.py`
- **Commit:** `6a58e7a`

## Verification Results

```
pipeline OK
264 tests passed in 0.81s (0 failed)
```

Full suite: 264 tests green (up from 253 before this plan, net +11 tests).

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced.
`pipeline.py` handles untrusted source text; the between-phase gating and `errors.report()` ensure only canonical plain-English output reaches stderr (T-05-01-C mitigated).
GEN-03 structural enforcement (T-05-01-A) confirmed by test `test_transpile_analyzer_error_returns_none` and TDD RED→GREEN cycle.

## Self-Check: PASSED

- [x] `src/atena/pipeline.py` exists with `def transpile` — FOUND
- [x] `tests/test_pipeline.py` exists with 8 tests — FOUND
- [x] `tests/test_pipeline_tdd.py` exists with 3 TDD tests — FOUND
- [x] Commit `5ea1038` (RED): test(05-01) — FOUND
- [x] Commit `6a58e7a` (GREEN): feat(05-01) implement transpile() — FOUND
- [x] Commit `007fd3b` (Task 2): feat(05-01) pipeline smoke tests — FOUND
- [x] 264 tests green — VERIFIED
