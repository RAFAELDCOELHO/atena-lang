---
quick_id: 260614-a8w
type: quick
slug: fix-lexer-guard-integer-scanner-against-
created: 2026-06-14
branch: feat/lexer
files_modified:
  - src/atena/lexer.py
  - tests/test_lexer.py
source: .planning/phases/01-lexer/01-REVIEW.md (CR-01)
---

<objective>
Fix code-review finding CR-01: the integer scanner gates on `char.isdigit()`, which
accepts non-ASCII Unicode digits (e.g. Arabic-Indic `١٢٣`). Those are emitted as NUMBER
tokens and pass cleanly through the lexer, only to make `ast.parse` raise a `SyntaxError`
at the Phase 4/5 code generator — a Python traceback reaching the learner, which violates
the project's core promise. Guard every digit check with `.isascii()` so a non-ASCII digit
is reported as a plain-English unexpected-character error at lex time instead.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Guard the integer scanner against non-ASCII digits (test-first)</name>
  <files>tests/test_lexer.py, src/atena/lexer.py</files>

  <action>
    1. RED: add `test_L8_non_ascii_digit_rejected` to tests/test_lexer.py asserting that
       lexing `"y = ١\n"` (U+0661) emits NO NUMBER token and records a plain-English
       "Error on line 1" via ErrorCollector, with no Python exception escaping. Confirm it
       FAILS against the current scanner (`١` currently becomes a NUMBER token, ec empty).
    2. GREEN: change every `isdigit()` check in src/atena/lexer.py (4 sites: dispatch gate,
       integer-collect loop, decimal-off-ramp peek, fractional-collect loop) to also require
       `.isascii()`. A non-ASCII digit then falls through to the generic unexpected-character
       catch-all (which already advances — always-make-progress preserved).
    3. Confirm the new test passes and the full suite stays green.
  </action>

  <verify>
    <automated>python3 -m pytest tests/ -q</automated>
  </verify>

  <done>
    New regression test green; full suite green (88 passed). Non-ASCII digits can no longer
    reach codegen. Commit: "fix(lexer): guard integer scanner against non-ASCII digits".
  </done>
</task>

</tasks>

<success_criteria>
A non-ASCII Unicode digit produces a plain-English unexpected-character error at lex time
(never a NUMBER token, never a Python exception). ASCII integers are unaffected. Full suite
green. CR-01 closed before feat/lexer merges.
</success_criteria>

<output>
Create 260614-a8w-SUMMARY.md when done.
</output>
