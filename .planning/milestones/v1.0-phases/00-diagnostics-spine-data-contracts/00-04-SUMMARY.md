---
phase: "00"
plan: "04"
subsystem: "diagnostics-spine"
tags: [tdd, suggest, difflib, case-only, did-you-mean, ATENA_KEYWORDS]
dependency_graph:
  requires:
    - "00-02 (ErrorCollector + error format established)"
  provides:
    - "suggest(name, candidates) — ready-to-append suggestion string or None"
    - "ATENA_KEYWORDS — 19-entry plain list for use by any phase"
    - "difflib-backed fuzzy matching with case-only mismatch priority"
  affects:
    - "All later phases: lexer/parser/analyzer can call suggest() on unknown names"
    - "00-05 (CLI): error output will include Did-you-mean suggestions via suggest()"
tech_stack:
  added:
    - "difflib (stdlib) — get_close_matches for fuzzy name matching"
  patterns:
    - "case-only check before fuzzy check (D-06 capitalization rule fires first)"
    - "early-return chain: empty → exact → case-only → fuzzy → None"
    - "ATENA_KEYWORDS as independent plain list (no sibling imports from errors.py)"
key_files:
  created: []
  modified:
    - src/atena/errors.py
    - tests/test_errors.py
decisions:
  - "ATENA_KEYWORDS has 19 entries (matching the authoritative enumerated list in the plan and tokens.KEYWORDS dict); the plan text saying '18' was an off-by-one — fixed via Rule 1"
  - "Case-only mismatch fires before fuzzy difflib check: any candidate whose lowercase equals name.lower() returns the D-06 form immediately"
  - "Exact match returns None (no suggestion when name is already correct)"
  - "errors.py imports only stdlib (difflib); zero sibling-module imports enforced"
  - "ATENA_KEYWORDS is intentionally duplicated from tokens.py's KEYWORDS set to preserve errors.py import isolation — callers extend via list(ATENA_KEYWORDS) + local_names"
metrics:
  duration: "~10 min"
  completed: "2026-06-13"
  tasks: 2
  files_created: 0
  files_modified: 2
---

# Phase 00 Plan 04: "Did you mean?" Suggestion Engine Summary

**One-liner:** TDD-implemented `suggest()` function in `errors.py` using `difflib.get_close_matches` with case-only mismatch detection (D-06), plus `ATENA_KEYWORDS` constant — 22 tests all green.

## What Was Built

This plan replaces the `suggest()` stub and empty `ATENA_KEYWORDS` placeholder with a fully-tested implementation following the RED → GREEN TDD cycle:

- **`ATENA_KEYWORDS: list[str]`** — 19 Atena reserved words as a plain list. Maintained independently from `tokens.py`'s `KEYWORDS` dict so `errors.py` has zero sibling-module imports and can be used by any pipeline phase without circular dependencies.
- **`import difflib`** — the only new import, stdlib.
- **`suggest(name, candidates) -> str | None`** — five-step early-return algorithm:
  1. `candidates` empty → `None`
  2. `name in candidates` (exact match) → `None`
  3. Any `candidate` where `name.lower() == candidate.lower()` → `'Did you mean "{candidate}"? Names must match capitalization exactly.'` (D-06 form)
  4. `difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)` → `'Did you mean "{match}"?'`
  5. No match → `None`
- **`tests/test_errors.py`** — extended from 11 to 22 tests (S-1 through S-11 added); all 22 green.

## Verification Evidence

```
pytest tests/test_errors.py -v
  22 passed in 0.01s

pytest tests/ -v
  42 passed in 0.03s

Spot-check:
  from atena.errors import suggest, ATENA_KEYWORDS
  assert suggest("scr", ["score", "show", "ask"]) == 'Did you mean "score"?'
  assert suggest("Score", ["score"]) == 'Did you mean "score"? Names must match capitalization exactly.'
  assert suggest("banana", ["score", "show", "ask"]) is None
  assert suggest("shwo", list(ATENA_KEYWORDS)) == 'Did you mean "show"?'
  assert len(ATENA_KEYWORDS) == 19
  print("all exemplar checks PASS")  # → PASS

grep -c "^from atena|^import atena" src/atena/errors.py  → 0
  (zero sibling imports confirmed)
```

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| RED | Add failing suggest() and ATENA_KEYWORDS tests | 0b90359 | tests/test_errors.py (extended), src/atena/errors.py (stub ATENA_KEYWORDS added) |
| GREEN | Implement suggest() with case-only detection and difflib | 0158e29 | src/atena/errors.py (full impl), tests/test_errors.py (S-10 count fixed) |

## TDD Gate Compliance

- RED gate commit exists: `0b90359` — `test(00-04): add failing suggest() and ATENA_KEYWORDS tests`
- GREEN gate commit exists: `0158e29` — `feat(00-04): implement suggest() with case-only detection and difflib fuzzy matching`
- REFACTOR gate: not needed — implementation is clean and minimal with no duplication.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ATENA_KEYWORDS count: plan said "18 items" but listed 19**
- **Found during:** GREEN phase test run — test S-10 initially set to `== 18`, but the plan's own enumerated list had 19 items (show, ask, if, else, while, repeat, times, and, or, not, function, return, add, to, remove, from, length, true, false), and `tokens.KEYWORDS` (the authoritative sibling dict) also has 19 entries confirmed by `test_T5_keywords_has_19_entries`.
- **Fix:** Updated test S-10 assertion from `== 18` to `== 19` to match the actual enumerated keyword list; `ATENA_KEYWORDS` implemented with all 19 items.
- **Files modified:** `tests/test_errors.py`
- **Commit:** `0158e29`

**2. [Rule 1 - Bug] Jargon word "token" in new ATENA_KEYWORDS docstring**
- **Found during:** GREEN phase first run — the docstring for `ATENA_KEYWORDS` mentioned "tokens.KEYWORDS", which caused `test_no_jargon_in_errors_py` to fail.
- **Fix:** Rewrote docstring to avoid "token"; uses "reserved words" and "sibling modules" instead.
- **Files modified:** `src/atena/errors.py`
- **Commit:** `0158e29` (fixed in same GREEN commit before committing)

## Known Stubs

None — all stubs from Plan 01 and Plan 02 in `errors.py` are now resolved:
- `suggest()` stub → fully implemented
- `ATENA_KEYWORDS` stub → populated with 19 items

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced.

| Threat | Status |
|--------|--------|
| T-00-04-01: DoS via large candidate list | Accepted with documentation — candidate set bounded by number of variables + 19 keywords in one program (a few hundred at most); documented in `suggest()` docstring |
| T-00-04-02: Information disclosure via suggestion output | Accepted — suggest() returns only names from the learner's own code or Atena's keyword list |
| T-00-04-03: ATENA_KEYWORDS mutation at runtime | Accepted — callers use `list(ATENA_KEYWORDS) + extra` pattern to get a copy; no defensive copy needed |

## Self-Check: PASSED

- [x] `src/atena/errors.py` exports `suggest`, `ATENA_KEYWORDS`, `ErrorCollector`, `ERROR_CAP`
- [x] `import difflib` is the only new import; `grep -c "^from atena|^import atena" src/atena/errors.py` → 0
- [x] `pytest tests/test_errors.py -v` exits 0, 22 passed
- [x] `pytest tests/ -v` exits 0, 42 passed
- [x] All 5 exemplar spot-checks pass
- [x] RED commit `0b90359` exists in git log
- [x] GREEN commit `0158e29` exists in git log
- [x] No stubs remain in errors.py
