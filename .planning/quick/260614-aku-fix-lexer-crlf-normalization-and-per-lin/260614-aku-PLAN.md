---
quick_id: 260614-aku
type: quick
slug: fix-lexer-crlf-normalization-and-per-lin
created: 2026-06-14
branch: feat/lexer
files_modified:
  - src/atena/lexer.py
  - tests/test_lexer.py
source: .planning/phases/01-lexer/01-REVIEW.md (WR-01, WR-02)
---

<objective>
Close the two remaining code-review warnings on the lexer before re-merge, each TDD
test-first with its own atomic commit.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: WR-01 — normalize CRLF and lone-CR line endings</name>
  <files>tests/test_lexer.py, src/atena/lexer.py</files>
  <action>
    RED: add a test that CRLF ("if x\r\n    show y\r\n") and lone-CR ("if x\r    show y\r")
    sources lex with no errors and produce a token stream identical to the LF equivalent.
    Confirm it fails (trailing \r hits the unexpected-character handler today).
    GREEN: in Lexer.__init__, set self._source = source.replace('\r\n','\n').replace('\r','\n')
    and build self._lines from the normalized self._source (so the char cursor and the line
    list stay byte-aligned). Commit: "fix(lexer): normalize CRLF and CR line endings".
  </action>
  <done>CRLF/CR lex identically to LF; commit 157eae9.</done>
</task>

<task type="tdd">
  <name>Task 2: WR-02 — reset brace depth per logical line</name>
  <files>tests/test_lexer.py, src/atena/lexer.py</files>
  <action>
    RED: add a test that an unclosed '{' on line 1 ("x = {1\nif y > 1:\n") does NOT suppress
    the colon off-ramp on line 2 (expect "colons" + "Error on line 2" in the report). Add a
    guard test that a balanced {"k": 1} on one line still does NOT trigger the off-ramp.
    Confirm the stray-brace test fails today (leaked _brace_depth swallows the colon).
    GREEN: reset self._brace_depth = 0 at the top of each iteration of the tokenize() outer
    loop (brace literals never span lines in v1.0). Commit: "fix(lexer): reset brace depth
    per line so colon off-ramp survives stray braces".
  </action>
  <done>Stray brace no longer leaks; balanced dict colon preserved; commit 25d0a5d.</done>
</task>

</tasks>

<success_criteria>
Windows/legacy line endings lex like LF; a stray '{' cannot disable the colon off-ramp on
later lines; within-line dict literals still suppress the off-ramp. Full suite green.
</success_criteria>

<output>
Create 260614-aku-SUMMARY.md when done.
</output>
