---
phase: 05-cli-runtime-pipeline-integration
verified: 2026-06-14T23:45:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 5: CLI, Runtime, Pipeline Integration — Verification Report

**Phase Goal:** The four phases are wired under a driver and a two-verb CLI so a learner can run or build a program, and runtime errors are translated to plain English — the no-stack-trace promise holds end-to-end.
**Verified:** 2026-06-14T23:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `atena run file.atena` transpiles and executes the program (CLI-01) | VERIFIED | `echo "Ana" | python -m atena run examples/school.atena` → exit 0, "Welcome, Ana" in stdout; C-1, C-15, C-18 pass |
| 2 | `atena build file.atena` writes generated Python without executing (CLI-02) | VERIFIED | `python -m atena build --show examples/school.atena` → exit 0, generated Python on stdout; C-2, C-16, C-19 pass |
| 3 | Transpilation errors exit non-zero with plain-English output, no traceback (CLI-03) | VERIFIED | `printf 'show "\n' | atena run /tmp/err.atena` → exit 1, "Error on line 1: ...", "Traceback" absent; C-17, C-17b pass |
| 4 | Runtime errors are translated to plain-English Atena messages with the correct Atena line number and non-empty source line — the real-pipeline, multi-line case (CLI-04) | VERIFIED | `printf 'a=10\nb=0\nshow "computing"\nshow a/b\n' | atena run` → "Error on line 4: you tried to divide by zero ... → show a / b"; all 10 tests in `test_cli_runtime_lines.py` pass, including `test_runtime_line_multiline_zero_division` and `test_runtime_negative_index_helper_reports_call_site` |
| 5 | Missing or unreadable file → friendly plain-English message, exit 1 (CLI-05) | VERIFIED | `python -m atena run no_such_file.atena` → "I couldn't find a file called ..."", exit 1; C-3/C-4/C-10/C-11/C-12 pass |
| 6 | `atena build --show` reveals the generated Python (CLI-06) | VERIFIED | `--show` flag present on `_build_parser`; `test_c19_build_show_flag` passes; manual run confirms "print" in stdout |

**Score:** 6/6 truths verified

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/atena/pipeline.py` | `transpile()` + `compile_for_run()` with four-phase wiring | VERIFIED | Both functions present; `_gate()` and `_analyze()` helper extracted; GEN-03 structurally enforced |
| `src/atena/cli.py` | `main()` with run/build subcommands, `_runtime_error_message()`, `_internal_error_message()` | VERIFIED | All functions present; exec path calls `compile_for_run`; build path calls `transpile`; `_HELPER_FRAMES` frozenset for frame-skip logic |
| `src/atena/codegen.py` | `build_module()` + `_stamp()` carry Atena `lineno` onto emitted AST nodes (CR-01 fix) | VERIFIED | `build_module()` at line 145; `_stamp()` at line 241 sets `py_node.lineno = line` for every emitted node |
| `tests/test_cli.py` | C-1 through C-25 (all passing) | VERIFIED | 26/26 tests pass |
| `tests/test_pipeline.py` | Pipeline smoke tests | VERIFIED | 8/8 tests pass |
| `tests/test_cli_runtime_lines.py` | 10 real-pipeline tests asserting exact line + non-empty source line (gap-closure) | VERIFIED | 10/10 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py` | `pipeline.py` | `from atena.pipeline import compile_for_run, transpile` | WIRED | Import at line 21; `compile_for_run` called at line 230 in `run` path; `transpile` called at line 207 in `build` path |
| `pipeline.py` | `codegen.py` | `CodeGenerator(program).build_module()` / `.generate()` | WIRED | `compile_for_run` calls `build_module()` at line 132; `transpile` calls `generate()` at line 96 |
| `pipeline._analyze()` | `lexer/parser/analyzer` | `Lexer/Parser/SemanticAnalyzer` chain with `_gate()` | WIRED | Three-phase chain with `_gate()` checks at lines 56, 61, 66 |
| `cli.py exec path` | `_runtime_error_message` | `except BaseException as exc` → `_runtime_error_message(exc, source.splitlines())` | WIRED | Line 247; `_internal_error_message` reserved for `compile_for_run` failures (CR-03 fix) |
| `_runtime_error_message` | `_HELPER_FRAMES` | `if frame.name in _HELPER_FRAMES: continue` | WIRED | Lines 135-138; skips `_atena_index`/`_atena_concat` frames to attribute errors to call-site Atena line |
| `codegen._stamp()` | Atena `lineno` → Python AST nodes | `py_node.lineno = line` for every emitted node | WIRED | Lines 250-252 in `codegen.py`; `_emit` and `_emit_as_stmt` both call `_stamp` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `cli.py` run path | `code` (compiled CodeType) | `compile_for_run(source, ...)` → real AST module with Atena line numbers | Yes — Atena AST nodes carry `line` field from lexer; stamped onto Python nodes in `_stamp()` | FLOWING |
| `_runtime_error_message` | `atena_lineno` | `traceback.extract_tb(exc.__traceback__)` → last non-helper frame `.lineno` | Yes — Python CPython line table maps back to the Atena `lineno` stamped in `build_module()` | FLOWING |
| `_runtime_error_message` | `source_line` | `source_lines[atena_lineno - 1].strip()` | Yes — line is within bounds because lineno is the Atena line, not a shifted Python line | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| school.atena runs end-to-end | `echo "Ana" \| python -m atena run examples/school.atena` | exit 0; "Welcome, Ana" in stdout | PASS |
| build --show outputs generated Python | `python -m atena build --show examples/school.atena` | exit 0; "# Generated by Atena" + `def _atena_index` in stdout | PASS |
| Compile-time error exits 1, no traceback | `printf 'show "\n' > /tmp/err.atena && python -m atena run /tmp/err.atena` | exit 1; "Error on line 1: ... make sure every \" has a matching \"" | PASS |
| Runtime error on REAL multi-line program: correct line 4, non-empty source | `printf 'a=10\nb=0\nshow "computing"\nshow a/b\n' > /tmp/div.atena && python -m atena run /tmp/div.atena` | exit 1; "Error on line 4: you tried to divide by zero"; "→ show a / b" (non-empty, correct line) | PASS |
| Missing file → plain English | `python -m atena run no_such_file.atena` | exit 1; "I couldn't find a file called \"no_such_file.atena\"." | PASS |
| build refuses to overwrite input | `printf 'show 1\n' > /tmp/prog.py && python -m atena build /tmp/prog.py` | exit 1; "I can only build files ending in \".atena\"." | PASS |
| Helper frame skip: `_atena_index` error maps to call-site | `printf 'nums=[1,2,3]\nshow 1\nx=0\nshow nums[x]\n' > /tmp/vi.atena && python -m atena run /tmp/vi.atena` | "Error on line 4: List positions in Atena start at 1 ... → show nums[x]" | PASS |

### Probe Execution

Step 7c: No probe scripts found or declared in PLAN files. SKIPPED — no conventional `scripts/*/tests/probe-*.sh` files present.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-01 | 05-01, 05-02 | `atena run` transpiles and executes | SATISFIED | `compile_for_run` + `exec(code, {"__name__": "__main__"})` in cli.py; C-1/C-15/C-18 pass |
| CLI-02 | 05-01, 05-02 | `atena build` writes generated Python without executing | SATISFIED | `transpile()` + file write in build path; C-2/C-16 pass |
| CLI-03 | 05-01, 05-04 | Errors printed, exit non-zero on transpile failure | SATISFIED | `_gate()` in pipeline prints to stderr; cli.py calls `sys.exit(1)` when `result is None`; C-17/C-17b pass |
| CLI-04 | 05-03, 05-04 | Runtime errors translated to plain-English with Atena line number | SATISFIED | `_runtime_error_message()` in cli.py; `_stamp()` + `build_module()` in codegen; `compile_for_run()` in pipeline; all 10 real-pipeline tests in `test_cli_runtime_lines.py` pass with exact line and non-empty source line |
| CLI-05 | 05-02 | Missing/unreadable file → friendly plain-English | SATISFIED | `_file_error_message()` in cli.py; C-3/C-4/C-10/C-11/C-12 pass |
| CLI-06 | 05-02 | `--show` flag reveals generated Python | SATISFIED | `_build_parser.add_argument("--show", ...)` at line 44; `if args.show: print(result)` at line 223; C-19 passes |

No orphaned requirements: REQUIREMENTS.md maps CLI-01 through CLI-06 to Phase 5; all six are covered.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | No TBD/FIXME/XXX markers; no stubs; no return null/empty patterns; no placeholder comments | — | Clean |

Scan confirmed: no TBD, FIXME, XXX, TODO, HACK, or PLACEHOLDER strings in `pipeline.py`, `cli.py`, or `codegen.py`. No empty handler stubs. The one doc note for `IN-02` (unused `filename` param in `transpile`) is explicitly acknowledged in code and the 05-REVIEW.md as "kept for signature symmetry" — not a blocker, and no marker left in source.

### Human Verification Required

None. All required behaviors are verifiable programmatically and were verified. The end-to-end test (`test_c18_school_atena_smoke`) uses a subprocess with real stdin passthrough; behavioral spot-checks ran the actual CLI binary against real `.atena` files.

### Gaps Summary

No gaps. All six CLI requirements are satisfied in the codebase and confirmed by:

1. 286 passing tests (full suite, exit 0), including 10 real-pipeline tests in `test_cli_runtime_lines.py` that were added specifically to catch the CR-01 false-pass that existed before gap closure.
2. Live behavioral spot-checks on real `.atena` files confirming the critical CLI-04 property: a multi-line program whose runtime error is on line 4 reports exactly "Error on line 4" with the non-empty offending source line in the `→` field. The previous monkeypatched test suite had masked this — the gap-closure commit (`401eb45`) fixed it with `build_module()` + `_stamp()` + `compile_for_run()` and added the real-pipeline regression tests.

The no-stack-trace promise holds end-to-end: compile-time errors, runtime errors, file-not-found errors, and internal transpiler bugs all produce plain-English output and never surface a Python `Traceback`, raw exception class name, or internal Atena jargon to the learner.

---

_Verified: 2026-06-14T23:45:00Z_
_Verifier: Claude (gsd-verifier)_
