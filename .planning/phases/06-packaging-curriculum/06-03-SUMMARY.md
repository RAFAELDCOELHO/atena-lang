---
phase: 06-packaging-curriculum
plan: "03"
subsystem: docs
tags: [readme, documentation, getting-started, curriculum]
dependency_graph:
  requires: []
  provides: [DOCS-02]
  affects: [README.md]
tech_stack:
  added: []
  patterns: [beginner-first voice, second-person, warm plain-English]
key_files:
  created: []
  modified:
    - README.md
decisions:
  - "README opens with a 3-sentence hook (what, who, secret feature) before mechanics"
  - "Eight sections in exact order: hook, install, first program, two verbs, error showcase, language basics cheatsheet, examples pointer, for teachers"
  - "Error showcase uses undefined-variable mistake — most relatable beginner error"
  - "Cheatsheet covers all 19 keywords and groups them by concept (not alphabetically)"
  - "For teachers section frames the 9-rung ladder as ~50-min-per-class curriculum"
metrics:
  duration: "< 5 min"
  completed: "2026-06-15"
  tasks_completed: 1
  files_modified: 1
---

# Phase 6 Plan 3: Getting-Started README Summary

Full `README.md` rewrite — warm beginner-first getting-started guide covering install, both CLI verbs, error showcase, 19-keyword cheatsheet, 9-rung examples ladder, and a for-teachers curriculum section.

## What Was Built

`README.md` replaced the 1-line `# atena-lang` stub with a 258-line complete getting-started guide. A brand-new user can follow it from `pip install .` to running their first Atena program without any other resource.

### Eight sections delivered

1. **Hook** — 3-sentence what/who/secret-feature intro before any mechanics
2. **Install** — `pip install .` (user) and `pip install -e .` (contributor); no PyPI, no `--version`
3. **Write your first program** — `hello.atena` walkthrough with expected output and a note on automatic string coercion
4. **Running and building programs** — table of all three forms (`run`, `build`, `build --show`) with one-sentence explanations
5. **When you make a mistake** — undefined-variable buggy program + exact plain-English Atena error, no Python traceback
6. **Language basics** — cheatsheet covering all 19 keywords grouped by concept: output, input, variables, arithmetic, comparisons, if/else, while, repeat, functions, lists (1-indexed), dicts (dot access), booleans, logic operators; ends with v1.0 limitations note
7. **Examples** — table of all 9 rungs with filenames and concepts; `school.atena` capstone pointer; one-line run command
8. **For teachers** — single paragraph framing the ladder as classroom curriculum (~50 min per rung), self-teaching files, capstone assignment, plain-English errors as pedagogical safety net, `--show` bridge to Python

## Verification Passed

All automated checks passed:
- `wc -l README.md` → 258 (> 100 required)
- `grep -c "For teachers" README.md` → 1
- `grep -c "\-\-version" README.md` → 0
- `grep -c "\-\-show" README.md` → 4
- `grep "str(" README.md` → nothing
- All 19 keywords from `src/atena/tokens.py` present in cheatsheet
- No Python jargon (`traceback`, `exception`, `AST`, `subprocess`) in body text
- Voice is second-person ("you") throughout

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write the full getting-started README | f947773 | README.md |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None. README.md is a static documentation file with no runtime security surface.

## Self-Check

- [x] README.md exists and is 258 lines
- [x] Commit f947773 exists
- [x] All 8 required sections present
- [x] DOCS-02 acceptance criteria met

## Self-Check: PASSED
