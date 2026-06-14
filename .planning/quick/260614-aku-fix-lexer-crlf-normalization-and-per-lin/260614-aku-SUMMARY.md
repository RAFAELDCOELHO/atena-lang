---
quick_id: 260614-aku
status: complete
date: 2026-06-14
branch: feat/lexer
commits:
  - 157eae9
  - 25d0a5d
source: .planning/phases/01-lexer/01-REVIEW.md (WR-01, WR-02)
---

# Quick Task 260614-aku: Fix lexer review warnings WR-01 (CRLF) and WR-02 (brace leak)

## What was done

Closed the two remaining `01-REVIEW.md` warnings on the lexer, each TDD test-first with its own
atomic commit.

### WR-01 — CRLF / lone-CR line endings (commit 157eae9)
Windows-saved files (`\r\n`) and legacy files (lone `\r`) broke: `source_line = raw_line.rstrip('\n')`
left a trailing `\r` that fell through to the generic unexpected-character handler on every line.
Fix: normalize in `Lexer.__init__` —
`self._source = source.replace('\r\n', '\n').replace('\r', '\n')` — and build `self._lines` from
the normalized `self._source` so the global char cursor (`_current`/`_peek`/`_advance`, which index
`self._source`) and the per-line list stay byte-aligned. CRLF and CR sources now produce a token
stream byte-identical to the LF equivalent, with zero errors.

### WR-02 — brace-depth leak across lines (commit 25d0a5d)
`_brace_depth` (which suppresses the colon off-ramp inside dict/set literals) was initialized once
and never reset, so an unclosed `{` on any line permanently disabled the colon off-ramp for the rest
of the file. Fix: reset `self._brace_depth = 0` at the top of each iteration of the `tokenize()`
outer loop. Brace literals never span lines in v1.0, so this is safe and surgical — within-line
balanced literals (`{"k": 1}`) still balance and correctly suppress the off-ramp, but a stray `{`
can no longer leak depth into later lines.

## TDD

| # | Test (RED → GREEN) | Behavior |
|---|--------------------|----------|
| WR-01 | `test_Lx_crlf_and_cr_line_endings` | CRLF + CR lex == LF, no errors |
| WR-02 | `test_Lx_stray_brace_does_not_suppress_later_colon_offramp` | stray `{` line 1 → colon off-ramp still fires line 2 |
| WR-02 | `test_Lx_balanced_dict_colon_not_offramp` | `{"k": 1}` still NOT an off-ramp (guard) |

Each behavior test was confirmed RED against the pre-fix code before applying the fix.

## Verification

- Full suite: **91 passed, 0 failed** (was 88; +3 new tests)
- Sanity: balanced `{"k": 1}` → no colon error; `x = {1` then `if y > 1:` → off-ramp fires on line 2;
  CRLF token stream identical to LF.

## Files changed

- `src/atena/lexer.py` — `__init__` line-ending normalization; per-line `_brace_depth` reset in `tokenize()`
- `tests/test_lexer.py` — 3 regression tests

## Commits

- `157eae9` — fix(lexer): normalize CRLF and CR line endings
- `25d0a5d` — fix(lexer): reset brace depth per line so colon off-ramp survives stray braces

## Notes

`feat/lexer` had already been fast-forward-merged into `main` before this task; these fixes were
committed on `feat/lexer` (per the project's never-work-on-main rule), so `main` should be
fast-forwarded again to pick them up. All three code-review findings on the lexer (CR-01 + WR-01 +
WR-02) are now resolved.
