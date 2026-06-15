---
phase: 06-packaging-curriculum
plan: "02"
subsystem: curriculum
tags: [examples, curriculum, tests, concept-ladder, docs]
dependency_graph:
  requires: []
  provides: [examples/01-show.atena, examples/02-ask.atena, examples/03-variables.atena, examples/04-conditionals.atena, examples/05-while.atena, examples/06-repeat.atena, examples/07-functions.atena, examples/08-lists.atena, examples/09-dicts.atena, tests/test_examples.py]
  affects: [DOCS-01]
tech_stack:
  added: []
  patterns: [subprocess-canned-stdin, concept-ladder, three-assert-rule]
key_files:
  created:
    - examples/01-show.atena
    - examples/02-ask.atena
    - examples/03-variables.atena
    - examples/04-conditionals.atena
    - examples/05-while.atena
    - examples/06-repeat.atena
    - examples/07-functions.atena
    - examples/08-lists.atena
    - examples/09-dicts.atena
    - tests/test_examples.py
  modified: []
decisions:
  - "Each rung file opens with # Concept: header (D-03) and isolates exactly one new concept (D-01/D-02)"
  - "Interactive rungs (02-ask, school.atena) use subprocess with input= and timeout=10 to prevent CI hangs (T-06-05)"
  - "All 10 tests use subprocess (no monkeypatching) to exercise the real installed pipeline (D-12)"
metrics:
  duration_seconds: 182
  completed: "2026-06-15"
  tasks_completed: 2
  files_created: 10
---

# Phase 6 Plan 02: Concept-Ladder Examples and Execution Tests Summary

**One-liner:** 9-rung Atena concept-ladder (show → ask → variables → conditionals → while → repeat → functions → lists → dicts) with 10 green subprocess execution tests enforcing the no-Traceback promise.

## What Was Built

### Task 1: 9 concept-ladder rung files in examples/

Created 9 numbered `.atena` files, each introducing exactly one new concept with a `# Concept:` header, inline teaching comments, and standalone runnable code:

| File | Concept | Output |
|------|---------|--------|
| `01-show.atena` | Output with `show` | "Hello, world!", 42, "The answer is: 42" |
| `02-ask.atena` | Interactive input with `ask` | Prompts for name, echoes "Hello, <name>" |
| `03-variables.atena` | Variables and arithmetic | Sum, difference, product, quotient |
| `04-conditionals.atena` | `if` / `else` | "Passing" or "Not yet" based on score |
| `05-while.atena` | `while` loop | Counts 1 to 5 |
| `06-repeat.atena` | `repeat N times` | Repeats message exactly 3 times |
| `07-functions.atena` | Functions and `return` | Doubles a number via function call |
| `08-lists.atena` | Lists with 1-indexing | `grades[1]` = 8, add/remove/length |
| `09-dicts.atena` | Dicts with dot read/write | `person.name`, `person.age = 21` |

All rungs: exit 0, non-empty stdout, no Traceback, no `str(` in source.

**Commit:** 37f5bc3

### Task 2: tests/test_examples.py — 10 execution tests

Created `tests/test_examples.py` with 10 test functions following the exact subprocess harness from `tests/test_cli.py`:

- Non-interactive rungs (01, 03-09): `run_cli("run", "examples/NN-name.atena")` with three-assert rule
- Interactive rungs (02-ask, school.atena): `subprocess.run(..., input="...\n", timeout=10)` pattern
- All 10 tests: assert `returncode == 0`, expected stdout content, and `"Traceback" not in stdout + stderr`

`pytest tests/test_examples.py` → **10 PASSED in 0.36s**

**Commit:** 7af204e

## Verification

All plan verification criteria met:

1. `ls examples/*.atena | wc -l` → **10** (9 rungs + school.atena)
2. `atena run examples/01-show.atena` → exits 0, stdout non-empty
3. `echo "Alice" | atena run examples/02-ask.atena` → exits 0, "Alice" in stdout
4. `echo "Ana" | atena run examples/school.atena` → exits 0, "Welcome, Ana" in stdout
5. `pytest tests/test_examples.py -v` → exits 0, **10 PASSED**
6. No rung file contains `str(` — checked with grep

## Deviations from Plan

None — plan executed exactly as written. All 9 rung files and the test suite match the specifications in D-01 through D-13.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Example files are pedagogic programs with no PII, no credentials. Subprocess calls in tests use hardcoded paths and canned inputs — no external network access. T-06-05 (DoS via hanging ask) mitigated by `timeout=10` on all interactive tests.

## Self-Check: PASSED

Files created:
- FOUND: examples/01-show.atena
- FOUND: examples/02-ask.atena
- FOUND: examples/03-variables.atena
- FOUND: examples/04-conditionals.atena
- FOUND: examples/05-while.atena
- FOUND: examples/06-repeat.atena
- FOUND: examples/07-functions.atena
- FOUND: examples/08-lists.atena
- FOUND: examples/09-dicts.atena
- FOUND: tests/test_examples.py

Commits:
- FOUND: 37f5bc3 (feat(06-02): add 9-rung concept-ladder in examples/)
- FOUND: 7af204e (feat(06-02): add tests/test_examples.py — 10 execution tests)

Tests: `pytest tests/test_examples.py` → 10 PASSED
