---
phase: "00"
plan: "02"
subsystem: "diagnostics-spine"
tags: [tdd, errors, error-collector, dedup, sort, cap, format]
dependency_graph:
  requires:
    - "00-01 (src/atena package importable, pip install -e . working)"
  provides:
    - "ErrorCollector: add/is_empty/report with dedup+sort+cap"
    - "ERROR_CAP = 10 module constant"
    - "Canonical error format template (single source of truth)"
    - "Fully-tested errors.py — all later phases import this"
  affects:
    - "00-03 (tokens.py/ast_nodes.py): Token and Node stubs; will import ErrorCollector"
    - "00-04 (suggest): suggest() stub in errors.py will be filled in"
    - "All lexer/parser/analyzer/generator plans: import and call ErrorCollector.add()"
tech_stack:
  added: []
  patterns:
    - "@dataclass _ErrorRecord internal record (line, message, source_line)"
    - "dedup by (line, message) preserving first-occurrence order before sort"
    - "stable sort by line ascending then cap at ERROR_CAP"
    - "two-newline separator between error blocks; single-newline before overflow line"
key_files:
  created:
    - tests/test_errors.py
  modified:
    - src/atena/errors.py
decisions:
  - "Dedup key is (line, message) only — source_line is display-only and not part of identity; two calls on the same line with the same message always collapse even if source differs"
  - "Dedup happens at report() time (not at add() time) so add() is always O(1) and phases never need to guard against double-adding"
  - "Overflow line uses single newline separator (not double) after the last error block — keeps the visual weight lighter than a full blank line"
  - "suggest() stub preserved as-is with 'Plan 04' TODO — not in scope for this plan"
metrics:
  duration: "~5 min"
  completed: "2026-06-13"
  tasks: 3
  files_created: 1
  files_modified: 1
---

# Phase 00 Plan 02: ErrorCollector Diagnostics Spine Summary

**One-liner:** TDD-implemented ErrorCollector with dedup+sort+cap and canonical `Error on line {N}: {msg}\n  → {src}` format as the single source of truth for all transpiler phases.

## What Was Built

This plan replaces the `errors.py` stub body with a complete, tested implementation following the RED → GREEN TDD cycle:

- **`ERROR_CAP = 10`** module constant — the cap applied at render time.
- **`_ErrorRecord` dataclass** — internal record with `line: int`, `message: str`, `source_line: str` fields.
- **`ErrorCollector.__init__`** — initialises `self._records: list[_ErrorRecord] = []`.
- **`ErrorCollector.add(line, message, source_line)`** — appends unconditionally; O(1), no dedup at call time.
- **`ErrorCollector.is_empty()`** — returns `True` on a fresh collector, `False` after any `add()`.
- **`ErrorCollector.report()`** — dedup by `(line, message)` preserving first-occurrence, stable-sort by line, cap at 10, format each as `Error on line {N}: {message}\n  → {source_line}`, join with double newline, append overflow line with single newline if `len(unique) > 10`.
- **`tests/test_errors.py`** — 11 tests covering every specified behavior; all green.

## Verification Evidence

```
pytest tests/test_errors.py -v
  11 passed in 0.01s

pytest tests/ -v
  17 passed in 0.01s (includes prior test_imports.py smoke tests)

Python spot-check:
  from atena.errors import ErrorCollector
  ec = ErrorCollector()
  ec.add(4, 'I don\'t know what "score" is yet.', 'show score')
  assert ec.report() == 'Error on line 4: I don\'t know what "score" is yet.\n  → show score'
  # → format check PASS

grep -c "Error on line" src/atena/errors.py  → 2
  (line 5: docstring comment with {N} placeholder; line 75: the only f-string template)
  Only one format f-string; docstring is documentation, not a duplicate.

grep -v "^#" src/atena/errors.py | grep -c "NoneType|traceback|AST|DEDENT|arity"  → 0
```

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| RED | Add failing ErrorCollector tests | 686f6b1 | tests/test_errors.py (created) |
| GREEN | Implement ErrorCollector with format/dedup/sort/cap | 1f8f119 | src/atena/errors.py (replaced stub body) |

## TDD Gate Compliance

- RED gate commit exists: `686f6b1` — `test(00-02): add failing ErrorCollector tests`
- GREEN gate commit exists: `1f8f119` — `feat(00-02): implement ErrorCollector with format/dedup/sort/cap`
- REFACTOR gate: not needed — implementation is already clean and minimal.

## Deviations from Plan

None — plan executed exactly as written. The three-commit sequence in the plan specified RED → GREEN → optional REFACTOR; no refactor was needed.

## Known Stubs

`suggest()` in `src/atena/errors.py` remains a stub with `# TODO: implemented in Plan 04` — intentional and unchanged per plan spec.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. The two mitigations from the plan's STRIDE register are addressed:

| Threat | Status |
|--------|--------|
| T-00-02-01: Python jargon in report() output | Mitigated — Test 10 scans all string literals; no forbidden words present |
| T-00-02-02: Unbounded _records list (DoS) | Mitigated — ERROR_CAP enforced at report() time; add() is uncapped but report() renders ≤10 |
| T-00-02-03: source_line injection | Accepted — offline CLI, source_line is learner's own file |

## Self-Check: PASSED

- [x] `tests/test_errors.py` exists with 11 tests
- [x] `src/atena/errors.py` contains `ErrorCollector` with `add/is_empty/report` and `ERROR_CAP = 10`
- [x] `pytest tests/test_errors.py -v` exits 0, 11 passed
- [x] `pytest tests/ -v` exits 0, 17 passed
- [x] Canonical format spot-check passes in Python
- [x] Zero jargon words in string literals
- [x] RED commit `686f6b1` exists in git log
- [x] GREEN commit `1f8f119` exists in git log
