---
phase: 04-code-generator
plan: "04"
subsystem: codegen
tags: [tdd, green-phase, edge-cases, keyword-mangling, nested-repeat, helper-execution, verbatim-emission]
dependency_graph:
  requires:
    - 04-03-SUMMARY.md
  provides:
    - GEN-04 validated: keyword mangling via keyword.kwlist trailing-underscore scheme
    - GEN-04 validated: unique _atena_i* loop vars via monotonic counter (never reset)
    - GEN-04 validated: on-demand helper bodies (_atena_index, _atena_concat) confirmed working
    - GEN-05 self-check confirmed on all edge-case outputs
    - Verbatim-emission discipline confirmed: no re-str-wrap, no double-shift
  affects:
    - 04-05-PLAN.md (school.atena golden fixture — all edge cases now locked)
tech_stack:
  added: []
  patterns:
    - "test _mangle() directly for pipeline-blocked keywords (class, import) — full-pipeline tests reserved for passable keywords"
    - "_atena_concat(3,5) → '35' (str concat) not 8 (numeric add) — confirmed via subprocess"
    - "test_G3_all_python_keywords_mangled: parametric over keyword.kwlist minus pipeline_blocked set"
key_files:
  created: []
  modified:
    - tests/test_codegen.py
decisions:
  - "_mangle() tested directly for class/import: both trigger Python-ism redirects in the parser so they cannot be tested via the full pipeline helper; _mangle() is the codegen function that matters"
  - "_atena_concat contract: returns str(a)+str(b) always — str concat, not numeric addition; join(3,5)='35' not 8"
  - "pipeline_blocked set in test_G3_all_python_keywords_mangled documents exactly which Python keywords hit Atena pipeline errors vs. which pass through to codegen"
metrics:
  duration: "~4 min"
  completed: "2026-06-14T20:26:28Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 4 Plan 4: GEN-04/GEN-05 Edge-Case Battery GREEN

All GEN-04 correctness guarantees validated via execution tests: keyword mangling, nested-repeat loop-var uniqueness, on-demand helper bodies, and verbatim-emission discipline.

## What Was Built

### Task 1: Keyword mangling + nested-repeat uniqueness tests

Six new tests added to `tests/test_codegen.py`:

**`test_G3_keyword_mangling_class`**: Tests `_mangle("class") == "class_"` directly. `class` triggers a Python-ism redirect in the Atena parser, so the test calls `_mangle()` directly (the exact codegen function) rather than `_generate()`. GEN-04 satisfied.

**`test_G3_keyword_mangling_import`**: Tests `_mangle("import") == "import_"` directly. Same rationale.

**`test_G3_keyword_mangling_execution`**: Uses `pass` (a Python keyword that Atena accepts as an identifier). `_generate("pass = 42\nshow pass\n")` → Python contains `pass_` → subprocess stdout is `42`. Confirms mangling is consistent at both definition and use sites.

**`test_G3_all_python_keywords_mangled`**: Iterates over all `keyword.kwlist` entries, filtering out those blocked by the Atena pipeline (Atena language keywords + Python-ism redirect targets). For each passable keyword, runs `_generate(f"{k} = 1\nshow {k}\n")` and asserts `k + "_"` appears and `ast.parse()` succeeds. Documents the `pipeline_blocked` set as the authoritative filter.

**`test_G3_three_sibling_repeats_unique_vars`**: Three consecutive `repeat 1 times` blocks → 3 distinct `_atena_i*` loop vars in output. Proves the monotonic counter never resets between sibling loops.

**`test_G2_nested_repeat_executes_correct_count`**: `n = 0 / repeat 3 times / repeat 2 times / n = n + 1 / show n` → subprocess stdout `6`. The two distinct loop vars do not interfere; total iterations are correct.

### Task 2: Helper body execution tests + verbatim-emission discipline tests

Six new tests added to `tests/test_codegen.py`:

**`test_G2_atena_index_helper_blocks_zero`**: `i = 0 / gradeslist = [5, 7, 9] / show gradeslist[i]` → `_atena_index` in output, subprocess exits non-zero, stderr contains `"List positions"`. Confirms the runtime 1-based enforcement.

**`test_G2_atena_index_helper_valid`**: `i = 1` → subprocess stdout `5` (Python index 0 of `[5, 7, 9]`). Confirms 1→0 conversion at runtime.

**`test_G2_atena_concat_helper_string_result`**: `function join(a, b) / return a + b / show join(3, 5)` → `_atena_concat` in output, subprocess stdout `35` (not 8). Confirms string concatenation contract: `str(3) + str(5) = "35"`.

**`test_G3_verbatim_no_str_wrap_number_plus_number`**: `x = 5 / y = 3 / show x + y` → `"str(x)"` NOT in output, `"x + y"` IS in output, stdout `8`. Confirms no over-coercion for number+number BinOps.

**`test_G3_verbatim_no_double_shift`**: `grades = [5, 7, 9] / show grades[2]` → `"grades[1]"` in output, `"grades[0]"` NOT in output, `"grades[2]"` NOT in output, stdout `7`. Confirms literal index folded once by analyzer and emitted verbatim by codegen.

**`test_G3_verbatim_nested_index_no_double_shift`**: `grid = [[1,2],[3,4]] / show grid[1][2]` → `"grid[0][1]"` in output, stdout `2`. Confirms both nested indices shifted exactly once.

## Deviations from Plan

None — plan executed exactly as written.

The existing `codegen.py` implementation was already complete and correct from Plans 02 and 03.  All 12 new tests are GREEN from the start (this is expected for an edge-case battery plan against an already-implemented feature).

One adaptation applied: `test_G3_keyword_mangling_class` and `test_G3_keyword_mangling_import` test `_mangle()` directly rather than via `_generate()`, because `class` and `import` trigger Python-ism redirects in the Atena parser and cannot reach codegen through the full pipeline.  This is correct behavior documented in `STATE.md [04-01]` and is the appropriate test approach — we verify the codegen function itself, not the pipeline's intentional rejection of these tokens.

## Verification Results

```
pytest tests/test_codegen.py -k "G3_keyword or G3_nested or G2_nested or G3_three_sibling or G3_all_python" -v
  → 8 passed

pytest tests/test_codegen.py -k "G2_atena or G3_verbatim" -v
  → 6 passed

python -c "import keyword; print(keyword.iskeyword('class'), keyword.iskeyword('import'))"
  → True True

pytest tests/ -q --tb=no
  → 1 failed (test_G2_school_execution_placeholder -- intentional pytest.fail() stub)
  → 236 passed
```

## Commits

| Hash | Message |
|------|---------|
| `7161a8b` | `test(04-04): keyword mangling + nested-repeat uniqueness battery GREEN` |
| `bb92fb0` | `test(04-04): helper body execution + verbatim-emission discipline tests GREEN` |

## Self-Check: PASSED

Files verified to exist:
- `tests/test_codegen.py` — 659 lines, 12 new tests added (6 Task 1, 6 Task 2)

Commits verified: `7161a8b` and `bb92fb0` both present in git log.
