---
phase: 02-parser
reviewed: 2026-06-14T12:24:45Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/atena/parser.py
  - tests/test_parser.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-14T12:24:45Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the recursive-descent + Pratt expression parser (`src/atena/parser.py`) and its
test suite (`tests/test_parser.py`). All 59 tests pass. The parser is structurally sound:
the progress invariant holds under heavy malformed input (no hangs reproduced),
`IndexAccess.index_converted` is always `False` from the parser, `_fn_depth` is correctly
restored on error via `finally`, and error recovery via synchronize-on-NEWLINE-first
correctly preserves the lexer's balanced INDENT/DEDENT for enclosing blocks.

No BLOCKER-class defects were found — the collect-all-errors contract holds, no Python
traceback escapes, and the codegen gate (`errors.is_empty()`) protects against the worst
outcomes of the issues below.

However, several defects degrade correctness and — critically for a teaching language whose
entire value proposition is plain-English diagnostics — produce misleading or cascaded error
messages, and silently accept constructs whose meaning diverges from what a non-programmer
intends. The most material findings:

- A complete statement followed by trailing junk (`x = a b`) is accepted as a (wrong)
  AST node *and* produces a confusing secondary error, because `_consume_newline()` is
  lenient instead of requiring a statement terminator (WR-01).
- A stray block-header keyword (`else` at top level) emits two errors, the second being the
  meaningless `I didn't expect "" here` pointing at an orphaned INDENT token (WR-02).
- `length` only binds to the immediate primary, so `length items[0]` silently parses as
  `len(items)[0]` — the opposite of the learner's intent, with no error (WR-03).
- `not` binds *tighter* than comparison, the opposite of Python and of natural-language
  reading; `not a == b` silently becomes `(not a) == b` (WR-04).
- Chained comparisons (`1 < 2 < 3`) are silently accepted and produce semantically wrong
  output (WR-05).

## Warnings

### WR-01: Trailing tokens after a complete statement are silently accepted and produce a misleading error

**File:** `src/atena/parser.py:418-426` (`_consume_newline`), and all call sites (e.g. `:452`, `:486`, `:632`)
**Issue:** `_consume_newline()` consumes a NEWLINE *if present* and otherwise does nothing.
It does not assert that the statement actually ended. As a result, a statement that parses a
complete expression but has leftover tokens on the line is accepted, the (wrong) AST node is
appended to `program.statements`, and the leftover token then triggers a separate, confusing
error on the *next* dispatch.

Reproduced:
```
x = a b      → stmts=[Assign(name='x', value=Identifier('a'))]  + error: I didn't expect "b" here.
show x y     → stmts=[Show(value=Identifier('x'))]              + error: I didn't expect "y" here.
x = 5 garbage→ stmts=[Assign(name='x', value=NumberLiteral(5))] + error: I didn't expect "garbage" here.
```

Two problems: (1) `program.statements` no longer faithfully represents the source — a
half-parsed `Assign(x, a)` leaks in even though the line is invalid; (2) the diagnostic names
the leftover token (`"b"`) rather than explaining the actual mistake (extra content after a
complete statement), which is exactly the kind of opaque message Atena promises to avoid.
The codegen gate (`is_empty()`) prevents the leaked node from reaching codegen *in this
specific case*, but the parser contract — "a returned statement is a valid statement" — is
violated.

**Fix:** Make `_consume_newline` enforce the terminator. Rename to e.g. `_end_statement` and
raise a `_ParseError` when the current token is not a statement boundary:
```python
def _end_statement(self) -> None:
    """Require a statement terminator (NEWLINE) or block/stream boundary."""
    if self._check(TokenType.NEWLINE):
        self._advance()
        return
    if self._check(TokenType.DEDENT, TokenType.EOF):
        return  # block-final / file-final statement: terminator already consumed/absent
    tok = self._current()
    raise _ParseError(
        tok.line,
        f'I didn\'t expect "{tok.value}" after the end of this line.',
        tok.source_line,
    )
```
This raises *before* the statement node is returned, so synchronize fires and no partial node
leaks into `program.statements`.

### WR-02: A stray block-header keyword produces a cascaded, meaningless second error on the orphaned INDENT

**File:** `src/atena/parser.py:639-761` (`_dispatch_statement` — no INDENT case) and `:161-171` (`_synchronize`)
**Issue:** When an erroneous statement header is immediately followed by an indented block,
`_synchronize` consumes through the NEWLINE and leaves the cursor on the orphaned `INDENT`
token. `_dispatch_statement` has no case for `INDENT` at statement position, so it falls
through to the generic branch and reports `I didn't expect "" here` (INDENT's value is the
empty string). A single mistake yields two errors, the second of which is meaningless to a
learner.

Reproduced (token stream confirmed: `KEYWORD else / NEWLINE / INDENT / KEYWORD show / …`):
```
else
    show x
```
→
```
Error on line 1: I didn't expect "else" here.
  → else

Error on line 2: I didn't expect "" here.    ← spurious, points at INDENT
  →     show x
```
Same double-error occurs for any unknown header followed by a block (`notakeyword\n    show x\n`)
and for a second `else` clause after a complete if/else. This undermines the
"one error per bad line, no spam" goal that `test_Px_three_bad_statements_three_errors`
encodes, and the `""`-valued message is precisely the opaque output Atena is meant to avoid.

**Fix:** When `_synchronize` lands on (or `_dispatch_statement` encounters) a stray
`INDENT`/`DEDENT` at statement position, skip the orphaned block instead of reporting on it.
Simplest: have `_synchronize` swallow a following orphaned INDENT…DEDENT pair, or add an
explicit guard at the top of `_dispatch_statement`:
```python
# An orphaned INDENT here means the previous header errored; skip its block silently
# rather than emitting a meaningless `""` diagnostic.
if self._check(TokenType.INDENT):
    self._skip_orphaned_block()   # consume balanced INDENT..DEDENT without re-reporting
    return None
```
At minimum, never surface a diagnostic whose `{tok.value}` is the empty string — substitute a
human-readable token description.

### WR-03: `length` binds only to the immediate primary, silently mis-parsing `length items[0]` and `length student.grades`

**File:** `src/atena/parser.py:343-353` (`_parse_primary`, `length` branch — calls `_parse_primary()`, not `_parse_postfix(_parse_primary())`)
**Issue:** `length` consumes only the next *primary*, so any postfix (`[]`, `.`, `()`) binds to
the result of `length`, not to its operand. For a non-programmer, `length items[0]` reads as
"the length of `items[0]`" but parses as `len(items)[0]`; `length student.grades` parses as
`len(student).grades`. Both are silently accepted with no error and produce semantically wrong
output. `length f()` produces the unrelated, confusing error `Only named functions can be
called.` because the postfix `()` attaches to the `length(...)` call node.

Reproduced:
```
x = length items[0]      → IndexAccess(target=FunctionCall('length',[items]), index=0)  i.e. len(items)[0]
x = length student.grades→ DotAccess(target=FunctionCall('length',[student]), name='grades')  i.e. len(student).grades
x = length f()           → Error: Only named functions can be called.
```
This is the documented design from plan 02-02 ("length binds tightest — only immediate
primary"), so it is intentional — but the design itself is a footgun for the target audience
and, unlike a normal precedence choice, it produces *no error* when the learner's intent is
violated.

**Fix:** Either (a) let `length` take a full postfix chain so the natural reading holds:
```python
self._advance()
operand = self._parse_postfix(self._parse_primary())
return FunctionCall(name="length", args=[operand], line=tok.line, source_line=tok.source_line)
```
or (b) keep the tight binding but require the operand to be parenthesized when followed by a
postfix, emitting a plain-English hint (e.g. *'Write `length (items[0])` to take the length of
one item.'*). Option (a) matches learner intuition and removes the silent mis-parse.

### WR-04: Unary `not` binds tighter than comparison — opposite of Python and of natural-language reading

**File:** `src/atena/parser.py:231-247` (`_parse_unary`, `not` handled before the binary loop in `_parse_expression`)
**Issue:** Because `not` is consumed in `_parse_unary` (the nud) before the Pratt binary loop,
`not a == b` parses as `(not a) == b`. In Python — Atena's target language — `not a == b`
means `not (a == b)` (`not` has *lower* precedence than `==`). The natural-language reading
("not a equals b") also groups as `not (a == b)`. So a learner's intent is silently inverted,
and the same source has different meaning in Atena vs. the Python it transpiles to.

Reproduced:
```
x = not a == b → BinOp('==', UnaryOp('not', a), b)   i.e. (not a) == b
```
`test_Px_logical_not_in_condition` enshrines `(not x) == 0` as correct, so this is a
deliberate, tested decision — but it is a latent semantic footgun for the stated audience and
deserves an explicit decision record, not silent acceptance.

**Fix (decision-dependent):** Preferred — give `not` a binding power just *below* comparison
(as Python does) so `not a == b` parses as `not (a == b)`, matching Python and intuition.
Handle `not` as a prefix operator inside the precedence ladder rather than as a primary-level
nud, or special-case it to parse its operand with `min_bp` set just above `or`/`and` but below
comparison. If the tight binding is genuinely intended, add a parser-level warning/hint when
`not` is directly followed by a comparison so the learner is told to parenthesize.

### WR-05: Chained comparisons (`1 < 2 < 3`, `a == b == c`) are silently accepted and mis-evaluated

**File:** `src/atena/parser.py:196-229` (`_parse_expression` — comparison operators share bp=3 and chain left-associatively)
**Issue:** All comparison operators share binding power 3 and are left-associative, so
`1 < 2 < 3` builds `BinOp('<', BinOp('<', 1, 2), 3)`. Codegen from this AST emits `(1 < 2) < 3`,
which evaluates as `True < 3` — not the chained comparison a learner intends and not what the
identical Python source (`1 < 2 < 3`, which Python chains) would do. No error is produced.
`a == b == c` is likewise accepted silently.

Reproduced:
```
x = 1 < 2 < 3 → BinOp('<', BinOp('<', 1, 2), 3)   → emits (1 < 2) < 3 → True < 3
x = a == b == c → accepted, no error
```
For non-programmers this is a silent correctness trap with surprising output.

**Fix:** Detect a comparison operator whose left operand is itself a comparison `BinOp` and
emit a plain-English error, e.g. *'Compare two things at a time — write `1 < 2 and 2 < 3`.'*
This can be done in the Pratt loop: before building a comparison `BinOp`, check whether
`left` is a comparison `BinOp` and raise `_ParseError` if so.

## Info

### IN-01: Stale, self-contradicting comment block references a non-existent method

**File:** `src/atena/parser.py:436-451` (inside `_parse_show`)
**Issue:** A 16-line comment narrates a guard that lives "in `_parse_primary_with_ask_guard`",
a method that does not exist anywhere in the file (`grep` confirms a single reference — the
comment itself). The comment also reasons in circles ("we override _parse_primary … here we
just parse normally — the guard is in _parse_primary itself"). It is misleading documentation
that will rot reader trust and mis-direct future maintainers. The actual behavior (D-02
redirect for `ask` in expression position) is already correctly handled at `:357-362`.

**Fix:** Delete lines 436-451 and replace with one accurate line, e.g.
`# 'ask' in expression position is redirected by _parse_primary (see :357).`

### IN-02: Empty-expression statements report `I didn't expect "" here`, exposing the NEWLINE token's empty value

**File:** `src/atena/parser.py:380` (`_parse_primary` fallthrough) reached via `show`/`return` with no operand
**Issue:** `show\n` and (inside a function) `return\n` reach `_parse_primary` with the current
token being NEWLINE (value `""`), producing `I didn't expect "" here.` For a teaching language
this is opaque — the learner sees empty quotes, not a description of the problem ("`show` needs
something to show").

**Fix:** In `_parse_primary`'s final `raise`, special-case structural tokens (NEWLINE/DEDENT/EOF)
with a friendlier message such as *'I expected something here but the line ended.'*, or have
`_parse_show`/`_parse_return` check for an immediate terminator before calling
`_parse_expression` and emit a construct-specific hint.

### IN-03: Inconsistent and duplicated error strings across paired parse helpers

**File:** `src/atena/parser.py:403` vs `:408` (dict `=` message), and `:273-278` vs `:280` (unclosed-bracket message duplicated as a literal)
**Issue:** The dict-literal parser emits `'Expected "=" after the key name in the dictionary.'`
for the first pair but `'Expected "=" after the key name.'` for subsequent pairs — the same
error worded two ways depending on position. Separately, the unclosed-`]` message
`'I reached the end of the line still waiting for a "]".'` is duplicated as a string literal in
two adjacent branches. These are magic-string duplications that will drift.

**Fix:** Hoist repeated diagnostics into module-level constants (e.g. `_MSG_UNCLOSED_BRACKET`)
and use a single consistent wording for the dict `=` separator in both the first-pair and
loop branches.

---

_Reviewed: 2026-06-14T12:24:45Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
