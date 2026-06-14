---
quick_id: 260614-a8w
status: complete
date: 2026-06-14
branch: feat/lexer
commit: bee9f8f
source: .planning/phases/01-lexer/01-REVIEW.md (CR-01)
---

# Quick Task 260614-a8w: Guard integer scanner against non-ASCII digits

## What was done

Closed code-review finding **CR-01** before `feat/lexer` merges. The integer scanner gated
purely on `str.isdigit()`, which returns `True` for non-ASCII Unicode digits (e.g. Arabic-Indic
`١٢٣`, U+0661+). Such characters were emitted as `NUMBER` tokens and passed cleanly through the
lexer, only to make `ast.parse()` raise a `SyntaxError` at the Phase 4/5 code generator — a raw
Python traceback reaching the learner, which directly violates the project's core promise.

Guarded all four digit checks in `src/atena/lexer.py` with `.isascii()`:
- dispatch gate (`if ch.isdigit() and ch.isascii():`)
- integer-collect loop
- decimal-off-ramp peek (`self._peek().isdigit() and self._peek().isascii()`)
- fractional-collect loop

A non-ASCII digit now fails the number dispatch, is not alphabetic, and falls through to the
existing generic unexpected-character catch-all (which already calls `_advance()`, so the
always-make-progress invariant is preserved). Result: a plain-English
`Error on line N: I don't know what "١" means …` at lex time instead of a downstream crash.

## TDD

1. **RED** — added `test_L8_non_ascii_digit_rejected` to `tests/test_lexer.py`: lexing `"y = ١\n"`
   must emit no `NUMBER` token and record a line-1 `ErrorCollector` entry. Confirmed FAILING
   against the unguarded scanner (`١` became a `NUMBER`).
2. **GREEN** — applied the four `.isascii()` guards. Test passes.

## Verification

- New regression test: **PASS**
- Full suite: **88 passed, 0 failed** (was 87; +1 new test)
- Sanity: ASCII `42` still lexes to `NUMBER '42'` with no error; the `3.5` decimal off-ramp still
  fires its "whole numbers" message; `١` produces the unexpected-character error and zero NUMBER tokens.

## Files changed

- `src/atena/lexer.py` — 4 `isdigit()` checks guarded with `isascii()` (+ explanatory comment)
- `tests/test_lexer.py` — `test_L8_non_ascii_digit_rejected` regression test

## Commit

`bee9f8f` — fix(lexer): guard integer scanner against non-ASCII digits

## Notes

CR-02 (CRLF handling, WR-01) and the brace-depth leak (WR-02) from the same review remain open
and are tracked for Phase 5 (CLI wiring) — out of scope for this fix.
