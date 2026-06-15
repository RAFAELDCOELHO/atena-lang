---
phase: 01-lexer
plan: 03
subsystem: lexer
tags: [tdd, green-phase, lexer, indentation, INDENT, DEDENT, NEWLINE, EOF, LEX-02, LEX-03, LEX-04]

requires:
  - phase: 01-lexer plan 02
    provides: Core character scanner (per-char dispatch, all token types, _brace_depth, ErrorCollector integration)
provides:
  - Complete Lexer with indentation engine — INDENT/DEDENT/NEWLINE emission, uniform-step enforcement, blank/comment skip, EOF drain
  - All 29 lexer tests GREEN; all 87 tests (Phase 0 + Phase 1) GREEN
  - src/atena/lexer.py delivers LEX-01 through LEX-08 as specified
affects:
  - Phase 02 (Parser) — consumes the balanced INDENT/DEDENT/NEWLINE/EOF stream produced here

tech-stack:
  added: []
  patterns:
    - Outer-loop-owns-line-number: self._line set to line_index+1 per iteration; _advance() updates col only
    - Blank/comment skip before indent stack: Pattern 3 — skipped lines do not touch _indent_stack
    - Standard indentation stack algorithm with CPython-style INDENT/DEDENT emission (D-08)
    - Uniform-step validation layer on top of standard stack (D-05/D-06/D-07)
    - Tab/space mixing check fires before indent/dedent branching — catches mixed dedent too
    - EOF drain: trailing NEWLINE + DEDENT per open block + EOF emitted in _drain_at_eof()
    - abs_pos tracker in tokenize() keeps self._pos consistent with line-indexed outer loop

key-files:
  created: []
  modified:
    - src/atena/lexer.py

key-decisions:
  - "Tab/space mixing check moved before the indent/dedent branch so it fires on mixed-character dedent (not just indent) — required for test_L4_mixed_tabs_spaces_error which uses a tab dedent after a space indent"
  - "outer-loop owns self._line (line_index + 1 per iteration); _advance() no longer increments self._line — removes double-counting on non-blank lines"
  - "_scan_line receives start_col and self._pos is pre-set by the outer loop to abs_pos + width before calling it — avoids rewriting the per-char dispatch logic"
  - "EOF drain checks last token type before emitting trailing NEWLINE — prevents duplicate NEWLINE when last line already ends cleanly"

patterns-established:
  - "Pattern: Indentation engine separates measurement (_measure_indent), validation+emission (_handle_indentation), and drain (_drain_at_eof) into three distinct methods"
  - "Pattern: recover-and-continue (D-04) — every indentation error calls ErrorCollector.add() then returns normally; scanning always continues"

requirements-completed: [LEX-02, LEX-03, LEX-04]

duration: 10min
completed: 2026-06-13
---

# Phase 1 Plan 3: Indentation Engine Summary

**Indentation engine with standard stack + uniform-step layer + EOF drain — INDENT/DEDENT/NEWLINE emission integrated with the Plan 02 character scanner, turning all 29 lexer tests GREEN (87 total).**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-13T23:08:00Z
- **Completed:** 2026-06-13T23:12:21Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `_measure_indent()` — counts leading whitespace chars (tabs count as 1, not tabstop width)
- Added `_handle_indentation()` — standard stack algorithm (D-08) + uniform-step validation (D-05/D-06/D-07) + tab/space mixing check
- Added `_drain_at_eof()` — trailing NEWLINE guard + DEDENT-per-open-block + EOF emission
- Restructured `tokenize()` outer loop — line-indexed iteration; self._line set per loop; blank/comment lines skipped before stack; abs_pos tracks source position for within-line scanner
- Removed `self._line += 1` from `_advance()` — eliminates double-counting; _advance() now updates pos and col only
- All four plain-English error key phrases present: "tabs and spaces", "doesn't match", "too far", "same size"

## Task Commits

1. **Task 1: Add indentation engine, blank/comment skip, and EOF drain to src/atena/lexer.py** - `61638f6` (feat)

**Plan metadata:** (see docs commit below)

## Files Created/Modified

- `/Users/juliorcoelho/atena-lang/src/atena/lexer.py` — Added _measure_indent, _handle_indentation, _drain_at_eof; restructured tokenize() outer loop; refactored _advance() to remove line-tracking side-effect; refactored _scan_line() to accept start_col and scan from pre-set position

## Decisions Made

- Tab/space mixing check moved outside the indent/dedent branch to fire in both directions — the failing test used a tab-indented dedent after space indents, which only entered the DEDENT branch; the check must precede the branch to catch this case
- Kept `_advance()` / `_current()` / `_peek()` using the global `self._pos` cursor — minimal divergence from Plan 02's working scanner; outer loop sets self._pos = abs_pos + width before calling _scan_line
- Used line-indexed outer loop (enumerate) to own self._line rather than a character-by-character approach — simpler and more robust than trying to sync the global cursor with line tracking through _advance()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tab/space mixing check must precede indent/dedent branching**
- **Found during:** Task 1 — test_L4_mixed_tabs_spaces_error still failing after initial implementation
- **Issue:** Plan placed the mixing check only in the INDENT branch. The test case `"if x\n    show y\n\tshow z\n"` has a tab at width=1 after a space-indent at width=4. Since 1 < 4, the DEDENT branch runs first and emits "doesn't match" before the mixing check can fire
- **Fix:** Moved the tab/space mixing check to the top of `_handle_indentation()`, before any branch on `width > top` / `width < top` / `width == top`. Check runs on every non-zero-width indentation regardless of direction
- **Files modified:** src/atena/lexer.py
- **Verification:** test_L4_mixed_tabs_spaces_error passes; all 29 lexer tests pass; 87 total pass
- **Committed in:** 61638f6 (included in main task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan algorithm for mixed-character dedent)
**Impact on plan:** Fix necessary for correctness; no scope change.

## Issues Encountered

Initial implementation placed the tab/space check only in the INDENT branch (following the plan's behavior block exactly). The mixing-check test uses a tab at a DEDENT point — fix required moving the check before the branch. All other tests passed on first implementation.

## Known Stubs

None — all methods fully implemented and wired. The lexer delivers a complete INDENT/DEDENT-balanced `list[Token]` terminated by EOF, ready for the Phase 2 Parser.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

Threat mitigations verified:
- **T-01-03-01 (DoS / pop-loop termination):** Pop loop terminates because stack shrinks each iteration; stack initialised with [0]; test_L2_eof_drain_mid_block and test_L4_staircase_dedent_error both pass without hanging
- **T-01-03-03 (no traceback on bad indent):** All test_L4_* tests pass — error collected, scanning continues, no exception escapes
- **T-01-03-04 (tab/space detection):** Checks indent_chars (leading whitespace only), not mid-line spaces; test_L4_mixed_tabs_spaces_error passes

## Next Phase Readiness

Phase 1 is 100% complete:
- 29/29 lexer tests GREEN
- 58/58 Phase 0 tests GREEN (no regression)
- 87 total: 0 failed
- `src/atena/lexer.py` implements LEX-01 through LEX-08
- Output is a flat, INDENT/DEDENT-balanced `list[Token]` terminated by EOF — Parser (Phase 2) can begin

## Self-Check: PASSED

- src/atena/lexer.py exists: FOUND
- Commit 61638f6 exists: FOUND
- 29 lexer tests GREEN: CONFIRMED (29 passed, 0 failed)
- 58 Phase 0 tests GREEN: CONFIRMED (87 total — all pass)
- _handle_indentation defined: CONFIRMED (grep count = 1)
- _drain_at_eof defined: CONFIRMED (grep count = 1)
- "tabs and spaces" phrase present: CONFIRMED
- "doesn't match" phrase present: CONFIRMED
- "too far" phrase present: CONFIRMED (in _handle_indentation)
- "same size" phrase present: CONFIRMED (in _handle_indentation)

---
*Phase: 01-lexer*
*Completed: 2026-06-13*
