---
phase: 04-code-generator
plan: 05
subsystem: testing
tags: [pytest, fixtures, golden-snapshot, subprocess, codegen]

# Dependency graph
requires:
  - phase: 04-04
    provides: keyword mangling, nested-repeat uniqueness, on-demand helper bodies — all tested by previous plans
  - phase: 04-01
    provides: dot-write parser fix (_dot_target DotAccess convention), CodeGenerator base implementation

provides:
  - "Locked golden fixtures: 6 .atena/.expected.py pairs covering all codegen constructs"
  - "GEN-06 acceptance gate: school.atena → school.expected.py byte-for-byte roundtrip + execution test"
  - "12 targeted fixture tests (G1 text-match + G2 subprocess execution per fixture)"
  - "248-test full suite GREEN — Phase 4 complete"

affects:
  - phase-05-cli (pipeline.py will run codegen; fixtures can be used for integration testing)
  - phase-06-examples (examples/school.atena is the user-facing curriculum flagship)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Layer 1 golden fixture tests: _generate(source) == fixture.expected.py (text-match)"
    - "Layer 2 execution tests: subprocess.run([sys.executable, '-c', py_src], input=canned_stdin)"
    - "Locked fixture derivation: run pipeline on .atena, write output to .expected.py, lock"

key-files:
  created:
    - tests/fixtures/school.atena
    - tests/fixtures/school.expected.py
    - tests/fixtures/keyword_mangle.atena
    - tests/fixtures/keyword_mangle.expected.py
    - tests/fixtures/nested_repeat.atena
    - tests/fixtures/nested_repeat.expected.py
    - tests/fixtures/dynamic_index.atena
    - tests/fixtures/dynamic_index.expected.py
    - tests/fixtures/concat_helper.atena
    - tests/fixtures/concat_helper.expected.py
    - tests/fixtures/dict_dot_write.atena
    - tests/fixtures/dict_dot_write.expected.py
    - examples/school.atena
  modified:
    - tests/test_codegen.py

key-decisions:
  - "[04-05]: keyword_mangle fixture uses 'pass' (not 'class') — 'class' is caught by parser Python-ism redirect before codegen; 'pass' is a valid Atena identifier that reaches codegen and must be mangled"
  - "[04-05]: school.atena uses source-level str() coercion notation removed after user review — concat_helper pattern (_atena_concat) is used instead"
  - "[04-05]: Golden fixtures locked after user review at Task 2 checkpoint — school.atena + school.expected.py are approved and must not be modified without re-derivation"

patterns-established:
  - "Fixture lock pattern: derive expected.py from pipeline, present for human review, then lock — any pipeline change causes text-match test to fail"
  - "Execution test pattern: read .expected.py from disk, run via subprocess with canned stdin, assert stdout content"
  - "Canned stdin for deterministic test: 'Ana\\n' fed to school.expected.py via input= parameter"

requirements-completed: [GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06]

# Metrics
duration: multi-session (Task 1 + checkpoint + Task 3)
completed: 2026-06-14
---

# Phase 4 Plan 05: Golden Fixtures + Integration Acceptance Gate Summary

**Canonical school.atena capstone locked and tested: 6 fixture pairs with text-match + subprocess execution tests drive GEN-06 acceptance and complete Phase 4 (248 tests GREEN)**

## Performance

- **Duration:** Multi-session (Tasks 1 and checkpoint prior sessions; Task 3 this session)
- **Started:** 2026-06-14 (Task 1)
- **Completed:** 2026-06-14 (Task 3)
- **Tasks:** 3 (Task 1: fixture authoring, Task 2: human-verify checkpoint, Task 3: test implementation)
- **Files modified:** 13 fixture files created + 1 test file modified

## Accomplishments

- Authored `school.atena` — canonical capstone covering all v1.0 constructs (ask, variables, if/else, while, nested repeat, functions+return, lists add/remove/length/literal-index/variable-index, dicts dot-read+dot-write, str coercion, arithmetic)
- Derived and locked `school.expected.py` via pipeline derivation (not hand-authored), confirmed executable with canned stdin "Ana"
- Authored 5 targeted fixture pairs isolating individual codegen features: keyword mangling, nested-repeat loop var uniqueness, dynamic index routing, _atena_concat helper, dict dot-write subscript Store
- Implemented all 12 fixture tests (G1 text-match + G2 execution per fixture pair) plus the GEN-06 golden roundtrip + execution tests — replacing the intentional `test_G2_school_execution_placeholder`
- Full suite from 236 → 248 tests, all passing — Phase 4 is complete

## Task Commits

Each task was committed atomically:

1. **Task 1: Author school.atena + all targeted fixtures, derive all expected.py snapshots** - `345741a` (feat)
2. **Checkpoint revision: remove source-level str(), re-derive school.expected.py** - `fea4bd3` (fix) — user requested removal of source-level `str()` calls; school.atena updated to use `_atena_concat` pattern (concat operator) instead; snapshots re-derived and re-approved
3. **Task 3: Implement golden + targeted fixture tests; full suite GREEN** - `68b4a20` (feat)

**Plan metadata:** _(committed next)_ (docs)

## Files Created/Modified

- `tests/fixtures/school.atena` - Canonical capstone: 55 lines, all v1.0 constructs
- `tests/fixtures/school.expected.py` - Locked golden snapshot (approved by user)
- `tests/fixtures/keyword_mangle.atena` - `pass = 5 / show pass` — exercises keyword mangling
- `tests/fixtures/keyword_mangle.expected.py` - Contains `pass_ = 5 / print(pass_)`
- `tests/fixtures/nested_repeat.atena` - Nested 3x2 repeat — exercises loop var uniqueness
- `tests/fixtures/nested_repeat.expected.py` - Contains `_atena_i0`, `_atena_i1` (2 distinct vars)
- `tests/fixtures/dynamic_index.atena` - `grades[i]` (variable index) — exercises _atena_index
- `tests/fixtures/dynamic_index.expected.py` - Contains `_atena_index(i)` helper call
- `tests/fixtures/concat_helper.atena` - `function join(a, b) / return a + b` — exercises _atena_concat
- `tests/fixtures/concat_helper.expected.py` - Contains `_atena_concat(a, b)` helper call
- `tests/fixtures/dict_dot_write.atena` - `student.name = "Ana"` — exercises subscript Store
- `tests/fixtures/dict_dot_write.expected.py` - Contains `student["name"] = "Ana"` (subscript Store)
- `examples/school.atena` - Curriculum flagship (identical to tests/fixtures/school.atena)
- `tests/test_codegen.py` - Added 12 targeted fixture tests + GEN-06 golden + execution tests

## Decisions Made

- **keyword_mangle fixture uses 'pass' not 'class':** The plan template said `class = 5` but 'class' is blocked by the parser's Python-ism redirect before reaching codegen. 'pass' is the correct keyword to test via the full pipeline — it is a valid Atena identifier that reaches codegen and must be mangled. Test asserts `"pass_"` in result (not `"class_"`).
- **Source-level str() calls removed from school.atena (user request at checkpoint):** Original school.atena used `show "Student: " + str(name)` style. User requested removing the `str()` form and using Atena's native string concatenation (`"Student: " + name` letting _atena_concat handle it). school.atena updated, school.expected.py re-derived and re-approved.
- **Post-phase quick task tracked:** The `str()` built-in is currently not callable in Atena programs (only the analyzer injects coercion marks). A post-phase quick task is tracked to either expose `str()` as a user-callable function or provide a clear error.

## Deviations from Plan

### Checkpoint Revision (User-requested, not auto-fix)

**Checkpoint revision: school.atena str() style → native concat**
- **Found during:** Task 2 (human-verify checkpoint)
- **Issue:** User requested removing source-level `str()` calls from school.atena in favor of Atena's native string concatenation form
- **Fix:** Updated school.atena to use `"label: " + variable` patterns; re-derived school.expected.py via pipeline; re-verified execution with "Ana" stdin; user approved revised fixtures
- **Files modified:** tests/fixtures/school.atena, tests/fixtures/school.expected.py, examples/school.atena
- **Verification:** Pipeline produces same school.expected.py byte-for-byte; subprocess with "Ana" exits 0 with "Ana" in stdout
- **Committed in:** fea4bd3

---

**Total deviations:** 1 user-directed revision at checkpoint (not an auto-fix rule; user review drove the change)
**Impact on plan:** No scope change. The revision improved school.atena as a teaching artifact — learners now see native Atena concatenation, not a Python built-in.

## Issues Encountered

None in Task 3. The 10 targeted fixture tests all passed on the first run because:
- The fixtures were correctly derived in Tasks 1/checkpoint
- The expected.py files exactly match what the pipeline produces
- Each fixture was verified executable before being locked

## Known Stubs

None — all tests implement real assertions against locked fixture content. No placeholder values.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Subprocess execution in tests uses only stdlib and canned inputs.

## Next Phase Readiness

- Phase 4 is COMPLETE: GEN-01 through GEN-06 all satisfied, 248 tests passing
- Phase 5 (CLI: `atena run` / `atena build`) can consume the pipeline without modification — `pipeline.py` stub will be replaced with the full pipeline chain (Lexer → Parser → Analyzer → CodeGenerator)
- `examples/school.atena` is ready as the curriculum flagship for Phase 6 documentation

## Self-Check

### Verified files exist:
- `/Users/juliorcoelho/atena-lang/tests/fixtures/school.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/school.expected.py` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/keyword_mangle.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/keyword_mangle.expected.py` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/nested_repeat.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/nested_repeat.expected.py` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/dynamic_index.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/dynamic_index.expected.py` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/concat_helper.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/concat_helper.expected.py` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/dict_dot_write.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/fixtures/dict_dot_write.expected.py` - FOUND
- `/Users/juliorcoelho/atena-lang/examples/school.atena` - FOUND
- `/Users/juliorcoelho/atena-lang/tests/test_codegen.py` - FOUND

### Verified commits exist:
- Task 1: 345741a - FOUND
- Checkpoint revision: fea4bd3 - FOUND
- Task 3: 68b4a20 - FOUND

### Test suite: 248 passed, 0 failed

## Self-Check: PASSED

---
*Phase: 04-code-generator*
*Completed: 2026-06-14*
