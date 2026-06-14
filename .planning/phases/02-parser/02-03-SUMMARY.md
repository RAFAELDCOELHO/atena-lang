---
phase: 02-parser
plan: "03"
subsystem: parser
tags: ["statement-dispatch", "recursive-descent", "tdd", "ast", "error-recovery"]

requires:
  - phase: 02-02
    provides: "_parse_expression() Pratt engine, all primary atoms, postfix chaining — 15 Layer 1 expression tests green"

provides:
  - "_dispatch_statement() full keyword-led dispatch replacing Plan 02 stub"
  - "_parse_show(), _parse_ask(), _parse_if(), _parse_while(), _parse_repeat()"
  - "_parse_function_def() with fn_depth tracking in finally (T-02-09)"
  - "_parse_return() with fn_depth == 0 check (D-04 item 3)"
  - "_parse_list_add(), _parse_list_remove() with keyword 'to'/'from' guards"
  - "_parse_assignment() with ask-RHS detection (D-01/D-02)"
  - "_parse_expression_statement() with == misuse redirect (D-04 item 2)"
  - "_consume_newline() helper for block-final statements before DEDENT/EOF"
  - "Python-ism redirects: def, elif, for, class, import (D-04 item 1)"
  - "ask guard in _parse_primary for D-02 misuse in expression position"
  - "Unclosed-bracket early-exit in _parse_postfix for better error message"

affects: ["02-04", "02-05"]

tech-stack:
  added: []
  patterns:
    - "keyword-led dispatch: _dispatch_statement peeks tok.value for KEYWORD tokens and routes to named parse methods"
    - "ask-as-assignment: _parse_assignment detects 'ask' after ASSIGN and delegates to _parse_ask — no Assign wrapper emitted (D-01/D-02)"
    - "fn_depth-finally: _parse_function_def increments fn_depth before block parse, decrements in finally so error recovery never leaks (T-02-09)"
    - "_consume_newline: tolerant NEWLINE consumer that silently skips if at DEDENT/EOF — avoids false errors on block-final statements"
    - "Python-ism-via-_ParseError: redirect errors raised as _ParseError inside _dispatch_statement — caught by _parse_statement, collected, then synchronize resumes parsing"
    - "ask-in-expression-position: _parse_primary checks for 'ask' KEYWORD and raises D-02-redirect before falling through to generic error"
    - "unclosed-bracket-early-exit: _parse_postfix checks for NEWLINE/EOF immediately after consuming '[' and raises the ']' error before _parse_expression fails generically"

key-files:
  created: []
  modified:
    - "src/atena/parser.py"

key-decisions:
  - "Ask node carries both prompt (str literal) and target (identifier name) per D-01/D-02 — no Assign wrapper emitted; the Ask IS the statement node"
  - "fn_depth decremented in finally block inside _parse_function_def — ensures consistency even when body parsing raises _ParseError (T-02-09)"
  - "Python-ism redirects (def/elif/for/class/import) fire from _dispatch_statement via _ParseError, collected by _parse_statement's except clause, recovery via _synchronize"
  - "== misuse detected in _parse_expression_statement after full expression parse — BinOp with op=='==' at statement position triggers D-04 item 2 redirect"
  - "ask in expression position redirects in _parse_primary — D-02 fires whether ask appears in 'show ask ...' or any other expression context"
  - "Unclosed bracket: _parse_postfix checks for NEWLINE/EOF immediately after consuming '[' to emit 'waiting for ]' rather than generic empty-token error"
  - "_consume_newline is tolerant (no-op at DEDENT/EOF) so block-final statements do not generate spurious 'expected newline' errors"

requirements-completed:
  - PARSE-01
  - PARSE-03
  - PARSE-04

duration: 10min
completed: "2026-06-14"
---

# Phase 02 Plan 03: Statement Dispatcher Summary

**Full recursive-descent statement dispatcher with all 9 keyword statement forms, Python-ism redirects, fn_depth tracking, and ask/== misuse detection — all 51 parser tests green including Layer 1, Layer 2, and Px cross-requirement tests.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-14
- **Completed:** 2026-06-14
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Replaced the Plan 02 stub `_dispatch_statement` with a full keyword-led dispatch covering all Atena statement forms
- Implemented `_parse_show()` — consume "show", parse expression, consume newline
- Implemented `_parse_assignment()` with ask-RHS detection: when `name = ask "..."` is seen, emits `Ask(prompt=..., target=name)` directly (no Assign wrapper, per D-01/D-02)
- Implemented `_parse_ask()` called from `_parse_assignment` — validates STRING follows "ask", emits Ask node
- Implemented `_parse_if()` with optional else clause detection
- Implemented `_parse_while()` with condition + block
- Implemented `_parse_repeat()` with count expression + "times" keyword validation
- Implemented `_parse_function_def()` with parameter list parsing and `fn_depth` tracking in `finally` (T-02-09)
- Implemented `_parse_return()` with `fn_depth == 0` check for top-level return redirect (D-04 item 3)
- Implemented `_parse_list_add()` and `_parse_list_remove()` with keyword "to"/"from" guards
- Implemented `_parse_expression_statement()` with `==`-as-assignment redirect (D-04 item 2)
- Added `_consume_newline()` helper — tolerant consumer that no-ops at DEDENT/EOF
- Added Python-ism redirects in `_dispatch_statement`: def, elif, for, class, import (D-04 item 1)
- Added ask guard in `_parse_primary` for D-02 misuse when ask appears in expression position
- Added unclosed-bracket early-exit in `_parse_postfix` to emit "waiting for ]" rather than generic empty-token error

## Task Commits

1. **Task 1: Implement _dispatch_statement and all statement parser methods** - `f9241b7` (feat)

## Files Created/Modified

- `src/atena/parser.py` — Added 335 lines, removed 33 lines: full statement dispatch replacing the Plan 02 stub; 11 new private methods; _consume_newline helper; ask guard in _parse_primary; unclosed-bracket early-exit in _parse_postfix

## Decisions Made

- **Ask node shape (D-01/D-02 confirmed):** `name = ask "..."` maps to `Ask(prompt="...", target="name")` as the direct statement node. No Assign wrapper. The Ask IS the statement, so the analyzer and generator can handle it without unwrapping.
- **fn_depth in finally (T-02-09):** `_fn_depth += 1` before `_parse_block()`, `_fn_depth -= 1` in `finally`. If the block parse raises a `_ParseError` (caught by `_parse_statement`'s except clause), the finally still fires and depth stays consistent. Verified by `test_Px_return_inside_function_no_error`.
- **== misuse detected post-parse:** The `==` slip is caught inside `_parse_expression_statement()` after `_parse_expression()` returns a `BinOp` with `op == "=="`. This approach is cleaner than peeking at the COMPARISON token before parsing, because the expression is fully formed.
- **_consume_newline tolerant:** Returns without consuming if at DEDENT or EOF. This makes block-final statements (e.g. last `show` before DEDENT) parse without error — the DEDENT is consumed by `_parse_block()`, not `_consume_newline()`.
- **Unclosed bracket redirect:** Added check in `_parse_postfix` before calling `_parse_expression()` for the index. When we consume `[` and the next token is NEWLINE/EOF, we immediately raise `'I reached the end of the line still waiting for a "]".'` rather than letting `_parse_primary` fail with a generic `I didn't expect "" here.` message.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unclosed bracket produced generic "I didn't expect \"\" here" error**
- **Found during:** Task 1 verification — `test_P2_unclosed_bracket` failed
- **Issue:** After consuming `[`, `_parse_expression()` was called and `_parse_primary` saw a NEWLINE token (value `""`), raising a generic error instead of the expected "waiting for `]`" message
- **Fix:** Added NEWLINE/EOF check in `_parse_postfix` immediately after consuming `[`, before calling `_parse_expression()` — raises the specific "]" error immediately
- **Files modified:** `src/atena/parser.py` (`_parse_postfix`)
- **Commit:** f9241b7 (included in task commit)

## Issues Encountered

None beyond the single auto-fixed deviation above.

## Known Stubs

None — the full statement dispatch is implemented. Plan 04 adds error recovery improvements and validates the `Px_three_bad_statements_three_errors` cross-requirement test expectations.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- `src/atena/parser.py`: FOUND
- Commit f9241b7: verified via `git log --oneline -1`
- All 51 parser tests PASSED: Layer 1 (P1_*), Layer 2 (P2_*), Px cross-requirement tests
- fn_depth tracking: `test_Px_return_inside_function_no_error` PASSED (return inside fn → ec.is_empty())
- `test_Px_empty_program` PASSED (regression)
- Ask node shape: `test_P1_ask_basic` PASSED (stmt is Ask, not Assign)

## Next Phase Readiness

- Plan 04 can add error recovery improvements, `Px_three_bad_statements_three_errors` exact count validation, and any remaining Python-ism redirects
- All AST node types from `ast_nodes.py` are now constructable by the parser — the full contract B surface is covered
- `fn_depth` tracking is in place for Plan 04's potential scope-level checks

---
*Phase: 02-parser*
*Completed: 2026-06-14*
