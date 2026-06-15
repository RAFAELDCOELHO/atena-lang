---
phase: 03-semantic-analyzer
plan: 03
subsystem: analyzer
tags: [semantic-analyzer, scope, arity, undefined-detection, tdd, python]

# Dependency graph
requires:
  - phase: 03-semantic-analyzer
    plan: 02
    provides: visit_BinOp (coercion), visit_IndexAccess (1→0 rewrite), basic symbol tracking

provides:
  - visit_Ask: registers node.target → "str" in active scope (D-03)
  - visit_Identifier: four-case undefined detection + D-08 outer-var teaching message + poison suppression
  - visit_FunctionDef: scope push/pop via try/finally; arity registration before body visitation
  - visit_FunctionCall: defined-before-called enforcement + arity checking; builtin pass-through
  - Full SemanticAnalyzer implementation: all 27 tests GREEN, all SEM-01..SEM-07 satisfied

affects:
  - 04-codegen (reads fully analyzed AST: str()/concat/index FunctionCall nodes, scope-checked names)
  - 05-cli (pipeline wiring; driver gates codegen on ec.is_empty())

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-level scope: self._locals (function body) / self._globals (top-level); scope = self._locals if self._locals is not None else self._globals"
    - "visit_FunctionDef try/finally scope restoration — unconditional even on internal Python errors (T-03-07)"
    - "Poison pattern: scope[name]='unknown' after first error prevents cascade for repeated undefined name (D-09, PITFALLS 12)"
    - "D-08 tailored teaching message: outer-var inside function → 'pass it as a parameter'"
    - "BUILTINS set {'length','str','_atena_concat','_atena_index'} skip arity checking in visit_FunctionCall"

key-files:
  created: []
  modified:
    - src/atena/analyzer.py
    - tests/test_analyzer.py

key-decisions:
  - "visit_Ask registers node.target → 'str' (not 'unknown') because Python input() always returns text (D-03)"
  - "visit_FunctionDef registers name BEFORE visiting body — self-recursion resolves, but no forward-call hoisting for external functions (D-09)"
  - "Built-in set handled inline in visit_FunctionCall with exact names {'length','str','_atena_concat','_atena_index'} (T-03-SC: reserved prefix prevents learner collisions)"
  - "[Rule 1 - Bug] test_A1_ask_registers_str_type used invalid 'ask ... into ...' syntax; fixed to 'answer = ask ...'"
  - "[Rule 1 - Bug] test_A2_wrong_arity_too_few used 'add' as function name; 'add' is a reserved Atena keyword; fixed to 'combine'"

# Metrics
duration: 4min
completed: 2026-06-14
---

# Phase 3 Plan 03: Scope and Arity Layer GREEN Summary

**Two-level scope with pure-function isolation, undefined-name detection with poisoning, D-08 outer-variable teaching message, and call-site arity enforcement — all 27 analyzer tests GREEN, full 189-test suite passing**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-14T17:28:24Z
- **Completed:** 2026-06-14T17:32:08Z
- **Tasks:** 3 implementation tasks + 1 checkpoint (auto-verified)
- **Files modified:** 2 (src/atena/analyzer.py, tests/test_analyzer.py)

## Accomplishments

- Implemented `visit_Ask`: registers `node.target → "str"` in the active scope (D-03: ask always returns text)
- Implemented full `visit_Identifier` with four-case resolution:
  - Case 1: name in current scope → return its type
  - Case 2: inside function, name in `self._functions` → callable, return "unknown"
  - Case 3: inside function, name in `self._globals` → D-08 tailored "pass as parameter" message + local poison
  - Case 4: fully undefined → "I don't know what X is" + `suggest()` hint + current scope poison
- Implemented `visit_FunctionDef` with complete scope push/pop via `try/finally`:
  - Registers `self._functions[name] = len(params)` AND `self._globals[name] = "function"` BEFORE body visitation (permits self-recursion, no external hoisting)
  - Pushes `{param: "unknown"}` local scope; restores unconditionally
- Implemented `visit_FunctionCall` with:
  - Bottom-up arg visitation
  - Built-in pass-through for `{"length", "str", "_atena_concat", "_atena_index"}`
  - Defined-before-called check (specific "not a function" vs "unknown function" error paths)
  - Arity error: `"{name}" expects N values, but you gave M.`
- Fixed 2 test source bugs (Rule 1): invalid `ask ... into ...` syntax and reserved keyword `add` used as function name

## Task Commits

1. **Task 1: visit_Ask str registration + test bug fixes** — `9eeab81` (feat)
2. **Task 2: visit_Identifier — undefined detection, poisoning, D-08** — `513c3ed` (feat)
3. **Task 3: visit_FunctionDef scope push/pop + visit_FunctionCall arity** — `e776745` (feat)

## Files Created/Modified

- `src/atena/analyzer.py` — Updated with:
  - `visit_Ask`: `scope[node.target] = "str"` (D-03)
  - `visit_Identifier`: four-case resolution with D-08 outer-var message and poison suppression
  - `visit_FunctionDef`: arity registration + try/finally scope push/pop
  - `visit_FunctionCall`: builtin bypass + defined-before-called + arity check
- `tests/test_analyzer.py` — Fixed 2 test sources:
  - `test_A1_ask_registers_str_type`: corrected `ask "name?" into answer` → `answer = ask "What is your name?"`
  - `test_A2_wrong_arity_too_few`: renamed function `add` (Atena keyword) → `combine`

## Decisions Made

- **visit_FunctionDef registers BEFORE body**: Self-recursive calls work; external forward references do not (D-09, PITFALLS 20). This matches a single top-to-bottom pass.
- **Built-in names as an inline set**: Using `{"length","str","_atena_concat","_atena_index"}` directly in `visit_FunctionCall` avoids coupling to any external registry. The `_atena_` prefix ensures learner-authored names can never collide (T-03-SC).
- **D-08 tailored message for outer-var access**: Rather than "I don't know what X is", a name that exists at top-level but is inaccessible from inside a function gets "A function can only use its own inputs — pass X in as a parameter." — the pedagogical payoff of the strict pure-function D-07 restriction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_A1_ask_registers_str_type used invalid Atena syntax**
- **Found during:** Task 1 verification
- **Issue:** The test source `'ask "name?" into answer\nx = answer + "!"\n'` generates a parse error because Atena uses `answer = ask "prompt"` syntax, not `ask "prompt" into answer`. The test asserted `ec.is_empty()` but the parse error would always fire.
- **Fix:** Changed source to `'answer = ask "What is your name?"\nx = answer + "!"\n'` which produces an `Ask` node with `target="answer"` correctly.
- **Files modified:** tests/test_analyzer.py
- **Commit:** 9eeab81

**2. [Rule 1 - Bug] test_A2_wrong_arity_too_few used reserved keyword "add" as function name**
- **Found during:** Task 1 (pre-analysis of failing tests)
- **Issue:** The test defined `function add(a, b)` but `add` is in the Atena `KEYWORDS` set (tokenized as `KEYWORD`, not `IDENTIFIER`). The parser's `_parse_function_def` calls `self._expect(TokenType.IDENTIFIER, ...)` which fails, producing a parse error instead of an arity error.
- **Fix:** Renamed the test function from `add` to `combine` throughout the test source.
- **Files modified:** tests/test_analyzer.py
- **Commit:** 9eeab81

## Test Results

### All 27 Analyzer Tests GREEN

- All 11 A1_ (golden mutated-AST snapshot) tests pass
- All 9 A2_ (error-path) tests pass
- All 7 Ax_ (cross-requirement) tests pass

### Full Suite: 189/189 Passing

No regressions in test_lexer.py, test_parser.py, test_errors.py, test_tokens.py, test_ast_nodes.py, test_imports.py, test_cli.py.

## Threat Mitigations Applied

- **T-03-07 (scope leak via try/finally):** `visit_FunctionDef` restores `self._locals` and `self._current_fn` unconditionally in `finally` — scope cannot leak between functions.
- **T-03-SC (builtin name collision):** `_atena_`-prefixed names in the builtin set cannot be produced by learner-authored Atena code (the lexer/parser only inject them via FunctionCall nodes in the analyzer itself).
- **T-03-06 (BUILTINS reserved):** First check in `visit_FunctionCall` passes through builtins before any arity check, so learner programs that happen to use `length(items)` (Atena builtin) are never incorrectly flagged as "undefined function".

## Known Stubs

None — all semantic analysis decisions are fully implemented. The analyzer correctly:
- Injects `str()` coercion for string+number/bool combinations
- Routes unknown-typed `+` through `_atena_concat`
- Rewrites literal 1-based indices to 0-based; routes dynamic indices through `_atena_index`
- Detects undefined names with plain-English errors and suggest() affordance
- Enforces two-level pure-function scope
- Enforces defined-before-called and arity for user-defined functions

## Threat Flags

None — this plan modifies only Python source files (no network endpoints, auth paths, file access, or schema changes).

## Self-Check: PASSED

- FOUND: src/atena/analyzer.py
- FOUND: tests/test_analyzer.py
- FOUND: 03-03-SUMMARY.md
- FOUND commit 9eeab81 (Task 1: visit_Ask + test bug fixes)
- FOUND commit 513c3ed (Task 2: visit_Identifier)
- FOUND commit e776745 (Task 3: visit_FunctionDef + visit_FunctionCall)
- All 27 analyzer tests GREEN (verified)
- Full 189-test suite passing (verified)
