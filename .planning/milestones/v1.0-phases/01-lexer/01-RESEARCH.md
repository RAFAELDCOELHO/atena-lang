# Phase 1: Lexer - Research

**Researched:** 2026-06-13
**Domain:** Hand-rolled indentation-sensitive lexer (off-side-rule tokenizer), Python 3.12 / stdlib only
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Tailored teaching off-ramps (not generic).**
For out-of-scope constructs detectable at lex time, the lexer emits a specific, redirecting plain-English message — not a generic "unexpected character." Anything not in the detected set falls through to the generic LEX-08 message.

**D-02 — The four detected off-ramps:**
1. Decimal numbers (digit-dot-digit, e.g. `3.5`) → "Atena works with whole numbers only — try 3 or 4 instead of 3.5."
2. Single-quoted strings (`'hello'`) → "Atena text goes inside double quotes — try \"hello\"."
3. Python-style trailing colon (`:`) → "Atena doesn't use colons — just indent the next line to start the block."
4. Semicolons (`;`) → "Put each step on its own line."

**D-03 — Voice: guide, don't just describe.**
Off-ramp messages follow the locked Phase 0 voice (first-person, calm, "Plain & kind"). Each message guides toward the v1.0 alternative. Because each off-ramp has a genuine known fix, always guide.

**D-04 — Collected + recover-and-continue.**
Off-ramps are collected errors. The lexer recovers and keeps scanning after each one so a learner sees every off-ramp in a single run.

**D-05 — Strict uniform-step indentation (stricter than CPython).**
Atena enforces a consistent indent unit, not merely a consistent relative increase.

**D-06 — First indented line sets the unit.**
The first indented line of a file pins both the indent character (tab vs space) and the unit width. Each file may choose its own unit; it must then be consistent within that file.

**D-07 — One unit per block; over-indent and ragged widths are errors.**
- Over-indent (jumping two-or-more units): friendly error.
- Ragged width (a level whose indentation isn't the established unit deeper): friendly error.
- Unmatched dedent (dedent to a level never opened): friendly error.

**D-08 — Still built on the standard machinery.**
Uniform-step is a validation layer on top of the indentation stack algorithm (ARCHITECTURE Pattern 1), the EOF drain (Pitfall 2), and skip-blank/comment-before-measuring (Pattern 3). Keep those exactly as researched.

### Claude's Discretion

- **Comment marker = `#`** (defaulted; single character, runs from `#` to end of line). Flag for user confirmation if a more beginner-friendly marker is wanted.
- **Exact wordings** for lexer errors — draft in Phase 0 voice.
- **Per-off-ramp recovery mechanics** — how far to skip after each detected off-ramp. Must satisfy always-make-progress / never-hang invariant.
- **`col` precision** — `Token` carries a `col` field; decide how precisely it is populated.
- **String escapes** — v1.0 has no escapes. A backslash inside `"…"` is a literal backslash.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. String-escape handling and float numbers are existing Out-of-Scope items. A `\n`-style off-ramp message is a candidate v2 enhancement only.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEX-01 | Lexer tokenizes source into the defined token types (STRING, NUMBER, IDENTIFIER, OPERATOR, COMPARISON, ASSIGN, LPAREN, RPAREN, LBRACKET, RBRACKET, LBRACE, RBRACE, COMMA, DOT, NEWLINE, INDENT, DEDENT, EOF) | TokenType enum already defined in `tokens.py`; scanner loops through all character classes mapping to these 19 types |
| LEX-02 | Lexer emits INDENT/DEDENT tokens by tracking indentation level, and drains all open blocks at end of file | ARCHITECTURE Pattern 1 (stack algorithm) + Pitfall 2 (EOF drain) cover this exactly |
| LEX-03 | Lexer skips blank lines and comment-only lines, emitting no NEWLINE for them | ARCHITECTURE Pattern 3; must check before touching indent stack |
| LEX-04 | Lexer enforces consistent tabs OR spaces within a file and reports a plain-English error on mixed indentation | ARCHITECTURE Pattern 2 + D-05/D-06/D-07 extend to uniform-step enforcement |
| LEX-05 | Lexer distinguishes ASSIGN (`=`) from COMPARISON (`==`) and recognizes all comparison (`!=`, `>`, `<`, `>=`, `<=`) and arithmetic (`+ - * /`) operators | ARCHITECTURE Pattern 4 (maximal-munch) covers `=`/`==`; single-char lookahead handles `!=`/`>=`/`<=` |
| LEX-06 | Lexer recognizes all keywords: show, ask, if, else, while, repeat, times, and, or, not, function, return, add, to, remove, from, length, true, false | `KEYWORDS` dict in `tokens.py` already contains all 19; lexer does identifier-then-keyword-lookup |
| LEX-07 | Lexer reads double-quoted string literals and integer numbers only, stamping every token with its line number and source-line text | `Token` dataclass already has `line`, `col`, `source_line`; string scanning loops until `"` or EOL |
| LEX-08 | Lexer reports a plain-English error for an unterminated string or an unexpected character | D-01/D-02 extend this to four tailored off-ramps; remaining unknowns fall to generic message |
</phase_requirements>

---

## Summary

Phase 1 implements `src/atena/lexer.py` — the first real pipeline phase. It scans Atena source text character-by-character, emitting a fully-materialized `list[Token]` with balanced INDENT/DEDENT tokens, stamping every token with line number, column, and the full source-line text. It plugs into the Phase 0 `ErrorCollector` and `Token`/`KEYWORDS` contracts already in place; nothing new needs to be defined outside `lexer.py` and `tests/test_lexer.py`.

The lexer has two layers beyond the standard off-side-rule algorithm. First, the standard machinery: indentation stack, EOF drain, blank/comment-line skipping before stack measurement, maximal-munch for `=` vs `==`. Second, the uniform-step enforcement layer (D-05–D-07): on the first indented line the indent character and unit width are pinned; every subsequent indented line is validated against this unit. Over-indent (jump of more than one unit), ragged width (not a clean multiple), and unmatched dedent (no matching stack entry) each produce a distinct plain-English error. Third, the four teaching off-ramps (D-01–D-04): decimal numbers, single-quoted strings, trailing colons, and semicolons each produce a specific guiding error message and recover-and-continue.

All errors are reported through `ErrorCollector.add()`. The lexer never raises to the user, never fails fast, and never emits a Python traceback. Recovery mechanics for off-ramps must satisfy the always-make-progress invariant. The output is a flat, INDENT/DEDENT-balanced `list[Token]` terminated by a single EOF token.

**Primary recommendation:** Implement the lexer as a single `Lexer` class in `src/atena/lexer.py` with a char-by-char cursor, an `indent_stack: list[int]`, and a `uniform_step` validation sub-layer. Follow the CPython stack algorithm exactly (D-08), then apply the uniform-step policy as a post-check after each push or pop decision. Write tests before implementation (TDD), in `tests/test_lexer.py` mirroring the style of `tests/test_tokens.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Char-by-char scanning | Lexer | — | No other phase sees raw source text |
| INDENT/DEDENT/NEWLINE emission | Lexer | — | Must own the indentation stack; parser only consumes structural tokens |
| Blank/comment-line skipping | Lexer | — | Must happen before stack is measured; parser has no visibility into raw lines |
| Uniform-step indentation validation | Lexer | — | Only the lexer measures indentation widths; later phases see only INDENT/DEDENT |
| Teaching off-ramp detection | Lexer | — | Off-ramps are character-level constructs; unreachable by later phases |
| Token stamping (line, col, source_line) | Lexer | — | Source position must be carried from first contact with source text |
| Error collection (add to ErrorCollector) | Lexer (report) | ErrorCollector (accumulate) | Lexer calls add(); ErrorCollector owns formatting and output |
| Keyword classification | Lexer (KEYWORDS lookup) | tokens.py (KEYWORDS dict) | Lexer scans identifier-shaped text, then looks up in existing KEYWORDS |
| Maximal-munch operators | Lexer | — | Single-character lookahead, entirely a scanning concern |

---

## Standard Stack

### Core (all stdlib — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.13 (installed) | Implementation language | Already the project runtime; 3.11+ is the floor per CLAUDE.md |
| `dataclasses` (stdlib) | bundled | `Token` is already a frozen dataclass in `tokens.py` | Standard; in use since Phase 0 |
| `enum` (stdlib) | bundled | `TokenType` is already an `Enum` in `tokens.py` | Standard; in use since Phase 0 |
| `pytest` | 9.0.3 (installed) | Test runner | Already in use; pytest 9.x requires Python ≥3.10; confirmed compatible |

[VERIFIED: local environment — `python3 --version` returns 3.12.13, `pytest --version` returns 9.0.3]

### No New Dependencies

The lexer phase installs zero new packages. `src/atena/lexer.py` imports:
- `from atena.tokens import TokenType, Token, KEYWORDS` (sibling module, Phase 0 deliverable)
- `from atena.errors import ErrorCollector` (sibling module, Phase 0 deliverable)
- Nothing from outside the stdlib or the project

[ASSUMED] — standard pattern for single-pass hand-rolled lexers; verified consistent with ARCHITECTURE.md and STACK.md which confirm stdlib-only for the entire transpiler core.

---

## Package Legitimacy Audit

> No external packages are installed in this phase. All code is stdlib + sibling modules.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Source text (str)
      │
      ▼
┌─────────────────────────────────────────────────┐
│  Lexer.__init__(source, errors: ErrorCollector)  │
│                                                 │
│  State:                                         │
│    pos: int  (current char offset)              │
│    line: int  (1-based)                         │
│    col: int   (0-based)                         │
│    indent_stack: list[int]  = [0]               │
│    indent_char: str | None  (tab or space)      │
│    indent_unit: int | None  (unit width)        │
│    tokens: list[Token]  (output accumulator)    │
└──────────┬──────────────────────────────────────┘
           │ tokenize() — main scan loop
           │
    ┌──────▼──────────────┐
    │ Per physical line:  │
    │  1. Skip if blank   │◄── blank or all-whitespace → continue
    │     or comment-only │◄── whitespace then '#' → continue
    │  2. Measure indent  │
    └──────┬──────────────┘
           │
    ┌──────▼──────────────────────────────────────┐
    │  Indentation handler (per logical line)     │
    │                                             │
    │  Standard stack check:                      │
    │    width == top → nothing                   │
    │    width >  top → push + emit INDENT        │
    │    width <  top → pop loop + emit DEDENT(s) │
    │      → if top ≠ width: "unmatched" error    │
    │                                             │
    │  Uniform-step validation layer (D-05–D-07): │
    │    First indent → pin indent_char + unit    │
    │    Subsequent:                              │
    │      wrong char  → "don't mix" error        │
    │      over-indent → "too far" error          │
    │      ragged width → "same size" error       │
    └──────┬──────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────────┐
    │  Per-character scanner (rest of line)       │
    │                                             │
    │  Whitespace → skip (mid-line)               │
    │  Letter/_ → scan identifier/keyword         │
    │  Digit    → scan integer; decimal off-ramp  │
    │  "        → scan string (or unterminated)   │
    │  '        → single-quote off-ramp           │
    │  =        → maximal-munch ASSIGN or EQ      │
    │  ! < > *  → maximal-munch operators         │
    │  + - /    → single-char OPERATOR            │
    │  ( ) [ ]  → single-char bracket             │
    │  { }      → single-char brace               │
    │  , .      → COMMA / DOT                     │
    │  :        → colon off-ramp                  │
    │  ;        → semicolon off-ramp              │
    │  #        → comment, skip to EOL            │
    │  \n       → emit NEWLINE, advance line      │
    │  other    → generic unexpected-char error   │
    └──────┬──────────────────────────────────────┘
           │
    ┌──────▼──────────────┐
    │  EOF handler        │
    │  Drain indent_stack │ → emit NEWLINE (if last line had content)
    │  (one DEDENT per    │   then DEDENT for each stack entry > 0
    │  entry above 0)     │   then EOF token
    └──────┬──────────────┘
           │
           ▼
    list[Token]  (balanced INDENT/DEDENT, terminated with EOF)
           │
           ▼
    ErrorCollector  (errors accumulated in-place; never raised)
```

### Recommended Project Structure

The phase creates exactly two files:

```
src/
└── atena/
    └── lexer.py          # Lexer class: source str → list[Token]

tests/
└── test_lexer.py         # All lexer tests (3 layers)
```

No changes to existing files except `pyproject.toml` if the feature branch needs it (it doesn't — existing `testpaths = ["tests"]` discovers `test_lexer.py` automatically).

### Pattern 1: Standard Indentation Stack (CPython tokenizer algorithm)

**What:** Initialize `indent_stack = [0]`. At the start of each logical (non-blank, non-comment) line, measure leading whitespace as a character count. Compare to `indent_stack[-1]`:
- equal → no token
- greater → push width, emit `INDENT`
- less → pop and emit `DEDENT` until `top <= width`; after popping, `top` MUST equal `width` — if not, it is an unmatched-dedent error

**When to use:** Always, for every non-blank/non-comment line.

**Example:**
```python
# Source: ARCHITECTURE.md Pattern 1
def _handle_indentation(self, width: int) -> None:
    top = self._indent_stack[-1]
    if width > top:
        self._indent_stack.append(width)
        self._emit(TokenType.INDENT)
    elif width < top:
        while self._indent_stack[-1] > width:
            self._indent_stack.pop()
            self._emit(TokenType.DEDENT)
        if self._indent_stack[-1] != width:
            self._errors.add(
                self._line,
                "This line's indentation doesn't match any block above it.",
                self._current_source_line,
            )
    # width == top: nothing to emit
```

### Pattern 2: Uniform-Step Validation Layer (D-05–D-07)

**What:** A post-check layered on top of Pattern 1. Runs after the standard stack decision but only if no "unmatched dedent" error was already reported for this line. The validation state is two values: `indent_char` (the character used — `' '` or `'\t'`) and `indent_unit` (the width of one step, e.g. `4` for 4-space indent).

**Initialization:**
- `indent_char = None`, `indent_unit = None` at construction
- On the first line with `width > 0`: pin `indent_char = leading[0]`, `indent_unit = width`

**Checks per logical line (after standard stack):**

| Condition | Error message draft |
|-----------|---------------------|
| Leading whitespace contains `indent_char`'s opposite | "Don't mix tabs and spaces for indentation — pick one and use it everywhere." |
| `width > top` and `(width - top) > indent_unit` | "This line is indented too far — keep each step the same size." |
| `width > top` and `(width - top) != indent_unit` | "Keep your indentation the same size as the rest of the file." |
| `width > top` (first indented line) — no error, pins unit | (pins `indent_char` and `indent_unit`) |
| `width < top` (dedent) and `width % indent_unit != 0` | "Keep your indentation the same size as the rest of the file." |

**Recovery:** After reporting a uniform-step error, the lexer still emits INDENT/DEDENT via the standard stack algorithm (the stack is not corrupted). This satisfies recover-and-continue (D-04).

**Why separate from the stack:** The standard stack algorithm detects structural inconsistency (unmatched dedent). The uniform-step layer detects pedagogical inconsistency (inconsistent unit size). They can both fire on the same line; both errors should be collected.

### Pattern 3: Skip Blank and Comment-Only Lines

**What:** Before measuring indentation, check if the rest of the line (after leading whitespace) is empty or starts with `#`. If so, skip the entire physical line — no tokens, no stack change, no NEWLINE.

**Example:**
```python
# Source: ARCHITECTURE.md Pattern 3; PITFALLS.md Pitfall 3
stripped = physical_line.lstrip()
if not stripped or stripped.startswith('#'):
    continue  # skip entirely — stack and tokens untouched
```

**Critical invariant:** This check MUST happen before `_handle_indentation()` is called. Getting this wrong is the #1 indentation-lexer bug (PITFALLS.md Pitfall 3).

### Pattern 4: Maximal-Munch for Multi-Character Operators

**What:** When the scanner sees `=`, `!`, `<`, `>`, peek at the next character to decide whether to produce a 2-char token. Longest match wins.

**Operator table for Atena:**

| First char | Peek char | Token | Type |
|------------|-----------|-------|------|
| `=` | `=` | `==` | COMPARISON |
| `=` | other | `=` | ASSIGN |
| `!` | `=` | `!=` | COMPARISON |
| `<` | `=` | `<=` | COMPARISON |
| `>` | `=` | `>=` | COMPARISON |
| `<` | other | `<` | COMPARISON |
| `>` | other | `>` | COMPARISON |
| `!` | other | error (unexpected char) | — |
| `+` `- ` `*` `/` | — | single-char OPERATOR | OPERATOR |

**Note:** `-` is both a unary negation operator (parsed by the parser) and a binary minus. The lexer always emits `OPERATOR` with value `"-"` — disambiguation is the parser's job, not the lexer's.

### Pattern 5: String Scanning

**What:** When `"` is encountered, scan forward consuming characters until a closing `"` or end-of-line. If EOL is reached before a closing `"`, report unterminated string error and recover by advancing past the EOL.

```python
# Recovery: advance pos to end of line so the scanner continues on the next line
start_col = self._col
self._advance()  # consume opening "
buf = []
while self._current() not in ('"', '\n', None):
    buf.append(self._current())
    self._advance()
if self._current() == '"':
    self._advance()  # consume closing "
    self._emit_value(TokenType.STRING, ''.join(buf), start_col)
else:
    self._errors.add(self._line, 'I found a piece of text that was never closed — make sure every " has a matching ".',
                     self._current_source_line)
    # recover: pos is already at \n or None; outer loop handles line advance
```

**String escapes:** v1.0 has none. A `\` inside `"…"` is a literal backslash character. Do not process `\n`, `\"`, or any other escape sequence. [ASSUMED — confirmed as locked scope by CONTEXT.md and REQUIREMENTS.md Out-of-Scope table]

### Pattern 6: Four Teaching Off-Ramps (D-02)

**Decimal numbers off-ramp:**
- Trigger: digit seen, then after scanning integer digits a `.` is found, followed by another digit.
- Action: report error with the specific decimal message; emit the integer portion as a NUMBER token (consume the `.` and fractional digits without emitting tokens); continue scanning.
- Recovery mechanics (Claude's Discretion): consume integer, consume `.`, consume fractional digits — emit only the integer token so parsing can continue meaningfully.

**Single-quote off-ramp:**
- Trigger: `'` character encountered.
- Action: report error; scan forward to the matching `'` (or EOL) to consume the whole single-quoted string; no token emitted for the string itself.
- Recovery mechanics (Claude's Discretion): scan to closing `'` or EOL, discard; advance past it. This prevents a wall of "unexpected char" errors for every character inside a single-quoted string.

**Colon off-ramp:**
- Trigger: `:` character encountered.
- Action: report error; consume the `:` (advance one character); continue scanning.
- Recovery mechanics: consume one character — minimal, always makes progress.

**Semicolon off-ramp:**
- Trigger: `;` character encountered.
- Action: report error; consume the `;`; continue scanning.
- Recovery mechanics: consume one character — minimal, always makes progress.

**Always-make-progress invariant:** Every off-ramp consumes at least one character before returning control to the main loop. This prevents the infinite-loop failure mode described in PITFALLS.md Pitfall 13.

### Pattern 7: EOF Drain

**What:** After the main scan loop exits (all characters consumed), emit one `NEWLINE` if the last logical line had content but no trailing `\n`, then emit one `DEDENT` for every `indent_stack` entry greater than 0, then emit a single `EOF` token.

```python
# Source: PITFALLS.md Pitfall 2; ARCHITECTURE.md Pattern 1
# At end of tokenize():
if self._last_line_had_content and not self._last_emitted_newline:
    self._emit(TokenType.NEWLINE)
while len(self._indent_stack) > 1:
    self._indent_stack.pop()
    self._emit(TokenType.DEDENT)
self._emit(TokenType.EOF)
```

**Why critical:** The INDENT/DEDENT stream must be balanced. The parser's `parse_block()` calls `expect(DEDENT)` — a missing DEDENT at EOF causes the parser to either crash or produce a truncated AST (PITFALLS.md Pitfall 2).

### Anti-Patterns to Avoid

- **Single depth counter instead of stack:** Cannot detect unmatched dedent; breaks on >1 nesting level. Use the stack.
- **Running indentation logic on blank/comment lines:** Corrupts the stack; causes phantom INDENT/DEDENT. Skip before measuring.
- **Emitting NEWLINE for blank lines:** Confuses the parser into ending statements early. Skip entirely.
- **Lookahead without consuming both chars for 2-char tokens:** Emits wrong token or misses second char.
- **Off-ramp recovery that does not consume at least one character:** Causes infinite loop.
- **Reporting uniform-step error without still emitting the INDENT/DEDENT:** Corrupts the stream and prevents subsequent error recovery.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token type definitions | Custom string constants or int enum | `TokenType` from `src/atena/tokens.py` (Phase 0) | Already implemented and tested; 19 members, all correct |
| Token construction | Any alternate struct | `Token` frozen dataclass from `src/atena/tokens.py` (Phase 0) | Already implemented with `line`, `col`, `source_line` fields |
| Error reporting | Custom print/raise | `ErrorCollector.add(line, msg, source_line)` from `src/atena/errors.py` (Phase 0) | The only permitted error channel; formats `Error on line N: …` correctly |
| Keyword lookup | Hand-written if/elif chain | `KEYWORDS` dict from `src/atena/tokens.py` (Phase 0) | Already contains all 19 keywords; O(1) lookup |
| Error format | `f"Error on line {n}: …"` in the lexer | Let `ErrorCollector.report()` format | Format must be centralized in `errors.py` per ARCHITECTURE.md |

**Key insight:** Phase 0 delivered all the shared infrastructure. The lexer's job is scanning and emitting — it should import and use Phase 0 contracts, never redefine them.

---

## Common Pitfalls

### Pitfall 1: Blank/Comment Lines Touch the Indent Stack

**What goes wrong:** An indented blank line or `# comment` line triggers `_handle_indentation()`, pushing/popping the stack and emitting phantom INDENT/DEDENT tokens. The next real line dedents incorrectly.
**Why it happens:** Developers loop over physical lines and run indentation logic on all of them.
**How to avoid:** Check for blank/comment BEFORE calling `_handle_indentation()`. The check is: `stripped = line.lstrip(); if not stripped or stripped.startswith('#'): continue`.
**Warning signs:** Adding a blank line inside a block changes the parse. A comment indented deeper than its context generates an INDENT error.

### Pitfall 2: EOF Drain Missing or Incomplete

**What goes wrong:** File ends with open blocks (stack has entries > 0). Parser sees no matching DEDENT and crashes internally or produces a truncated AST.
**Why it happens:** DEDENT logic only fires when a new line is read; EOF is not a line, so the drain is forgotten.
**How to avoid:** After the main loop, explicitly drain the stack. Also emit a NEWLINE if the last logical line had no trailing `\n` (files without trailing newlines are common).
**Warning signs:** A file ending inside a nested block produces an internal Python error (e.g., `StopIteration`, `IndexError`) instead of a clean parse.

### Pitfall 3: Unmatched Dedent Not Detected

**What goes wrong:** A line dedents to a column never on the stack. The lexer silently continues as if the dedent matched, producing structurally wrong Python.
**Why it happens:** The "pop while top > current" half is implemented but the invariant check ("after popping, top MUST equal current") is omitted.
**How to avoid:** After the pop loop, assert `self._indent_stack[-1] == width`. If not, call `self._errors.add(...)` and do NOT emit the DEDENT (or emit but mark as error). The error message is "This line's indentation doesn't match any block above it."
**Warning signs:** Staircase-dedent test (indent 4, then 8, then dedent to 6) passes instead of erroring.

### Pitfall 4: Uniform-Step Over-Indent Not Caught

**What goes wrong:** A learner accidentally indents two levels at once (`if x\n        show y` jumping from 0→8 instead of 0→4). Under the standard CPython algorithm this is legal; under D-07 it is an error.
**Why it happens:** The uniform-step layer is omitted; only the standard stack algorithm is implemented.
**How to avoid:** After the standard stack push (width > top), check `(width - top) == indent_unit`. If not, emit the over-indent error AND still push the new width (so the stream remains parseable and subsequent errors can be found).
**Warning signs:** A two-unit jump produces valid tokens instead of an error.

### Pitfall 5: Off-Ramp Recovery Does Not Always Make Progress

**What goes wrong:** An off-ramp error is reported but the scanner position is not advanced, so the main loop re-enters with the same character and reports the error again indefinitely.
**Why it happens:** The off-ramp handler reports the error and returns without consuming the offending character(s).
**How to avoid:** Every off-ramp handler must advance `pos` by at least one character. For single-quote and decimal off-ramps, consume to the end of the construct (closing `'` or end of fractional digits).
**Warning signs:** A single `'x'` in source produces dozens of identical errors. Test suite times out on single-quote input.

### Pitfall 6: `=` vs `==` Not Distinguished

**What goes wrong:** `x == 5` is tokenized as `ASSIGN, ASSIGN` instead of `COMPARISON`. Downstream parser produces wrong AST (assignment where comparison expected).
**Why it happens:** The `=` case does not peek at the next character.
**How to avoid:** Pattern 4 (maximal-munch) — when `=` is seen, check `peek() == '='`; if yes, consume both and emit COMPARISON with value `"=="`.
**Warning signs:** An equality test in a condition parses as a double assignment.

### Pitfall 7: Mixed Tabs/Spaces Accepted Silently

**What goes wrong:** A tab-indented line and an 8-space-indented line compare equal by character count (both width 1 vs 8), producing nondeterministic block structure depending on which editor generated the file.
**Why it happens:** `len(leading_whitespace)` is used without checking whether characters are tabs or spaces.
**How to avoid:** On the first indented line, record `indent_char`. On each subsequent indented line with `width > 0`, check that all leading whitespace characters match `indent_char`. If a different character appears, emit the mixed-indentation error. Count character occurrences for width, not `len()`.
**Warning signs:** A file that looks correct in one editor parses differently in another. No test feeds a tab character into the lexer.

### Pitfall 8: Decimal Off-Ramp Triggers on `.` in Identifiers or Dict Access

**What goes wrong:** `student.name` triggers the decimal off-ramp because the lexer sees `student` (identifier), then `.`, then `n` (a letter). The check `digit-dot-digit` must be precise: both the character before and after the dot must be digits.
**Why it happens:** The off-ramp checks only `digit` then `.` without checking what follows the dot.
**How to avoid:** The decimal off-ramp fires when: the scanner is in integer-scanning mode (already consumed at least one digit), the next character is `.`, AND the character after that is also a digit. A `.` followed by a letter is a `DOT` token, not an off-ramp.
**Warning signs:** `student.name` produces a decimal off-ramp error.

---

## Code Examples

Verified patterns from official sources and the project's existing architecture:

### Lexer Class Skeleton

```python
# Source: ARCHITECTURE.md Component Responsibilities + Pattern 1
# File: src/atena/lexer.py
from __future__ import annotations
from atena.tokens import TokenType, Token, KEYWORDS
from atena.errors import ErrorCollector

class Lexer:
    def __init__(self, source: str, errors: ErrorCollector) -> None:
        self._source = source
        self._errors = errors
        self._lines = source.splitlines(keepends=True)
        self._pos = 0
        self._line = 1
        self._col = 0
        self._indent_stack: list[int] = [0]
        self._indent_char: str | None = None
        self._indent_unit: int | None = None
        self._tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        for raw_line in self._lines:
            self._scan_line(raw_line)
        self._drain_at_eof()
        return self._tokens
```

### Indentation Check (combined standard + uniform-step)

```python
# Source: ARCHITECTURE.md Pattern 1 + CONTEXT.md D-05–D-07
def _handle_indentation(self, width: int, source_line: str) -> None:
    top = self._indent_stack[-1]
    if width == top:
        return
    if width > top:
        delta = width - top
        # Uniform-step: pin unit on first indent; validate thereafter
        if self._indent_unit is None:
            self._indent_unit = delta  # first indent pins the unit
        elif delta != self._indent_unit:
            msg = (
                "This line is indented too far — keep each step the same size."
                if delta > self._indent_unit
                else "Keep your indentation the same size as the rest of the file."
            )
            self._errors.add(self._line, msg, source_line)
            # still push to keep stream parseable
        self._indent_stack.append(width)
        self._emit_structural(TokenType.INDENT, source_line)
    else:  # width < top
        while self._indent_stack[-1] > width:
            self._indent_stack.pop()
            self._emit_structural(TokenType.DEDENT, source_line)
        if self._indent_stack[-1] != width:
            self._errors.add(
                self._line,
                "This line's indentation doesn't match any block above it.",
                source_line,
            )
```

### Maximal-Munch for `=`

```python
# Source: ARCHITECTURE.md Pattern 4
if ch == '=':
    if self._peek() == '=':
        self._advance()
        self._emit_token(TokenType.COMPARISON, '==', start_col, source_line)
    else:
        self._emit_token(TokenType.ASSIGN, '=', start_col, source_line)
```

### EOF Drain

```python
# Source: PITFALLS.md Pitfall 2
def _drain_at_eof(self) -> None:
    # Emit a trailing NEWLINE if the last line had content and no \n
    if self._tokens and self._tokens[-1].type not in (
        TokenType.NEWLINE, TokenType.DEDENT, TokenType.INDENT
    ):
        # Use last known source_line; line stays at its last value
        self._emit_structural(TokenType.NEWLINE, self._last_source_line)
    # Drain open blocks
    while len(self._indent_stack) > 1:
        self._indent_stack.pop()
        self._emit_structural(TokenType.DEDENT, "")
    self._emit_structural(TokenType.EOF, "")
```

### Keyword vs Identifier

```python
# Source: ARCHITECTURE.md Component Responsibilities; KEYWORDS dict in tokens.py
if ch.isalpha() or ch == '_':
    start_col = self._col
    buf = []
    while self._current_char() and (self._current_char().isalnum() or self._current_char() == '_'):
        buf.append(self._current_char())
        self._advance()
    word = ''.join(buf)
    tok_type = KEYWORDS.get(word, TokenType.IDENTIFIER)
    self._emit_token(tok_type, word, start_col, source_line)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parser generators for indentation-delimited langs (Lark Indenter) | Hand-rolled lexer with explicit stack | Established in Phase 0 research | Parser generators require hand-written INDENT/DEDENT postlex with known edge-case bugs in comment handling |
| Tab-width normalization (CPython's 1→8-space rule) | Forbid mixing outright; char-count only | Project design decision | Simpler, cleaner error for beginners; avoids tab-stop arithmetic entirely |
| Global error counters / fail-fast on first error | ErrorCollector injection + recover-and-continue | Phase 0 contract | Collect all errors per run; learner sees every problem at once |

**Deprecated/outdated:**
- CPython's tab-stop normalization: not applicable — Atena forbids mixing tabs/spaces outright.
- `astor` for codegen: not applicable to this phase; `ast.unparse()` is the Phase 4 choice.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `#` is the comment marker (not locked in spec text; defaulted from CONTEXT.md Claude's Discretion) | Pattern 3; off-ramp handling | If a different comment marker is chosen, Pattern 3 and off-ramp handling both need a one-line update |
| A2 | String escapes are literal (no `\n`, no `\"`); a backslash inside `"…"` is emitted as-is | Pattern 5 | If v1.0 later decides `\"` should be an off-ramp or an escape, the string scanner needs a new case |
| A3 | Decimal off-ramp recovery: emit the integer part as a NUMBER token, consume and discard `.` and fractional digits | Pattern 6 | If "emit no token" is preferred (don't give the parser partial data), recovery mechanic changes — but always-make-progress invariant is met either way |
| A4 | Single-quote off-ramp recovery: scan to closing `'` or EOL | Pattern 6 | If EOL-only recovery is preferred (stop at line end always), behavior on multi-character single-quoted strings changes |
| A5 | `col` is 0-based character offset within the physical line (matching `Token.col` field convention in `tokens.py` docstring) | All token emission | No test in Phase 0 asserts specific col values; convention is safe assumption |

**If this table is empty:** N/A — there are assumptions; see above.

---

## Open Questions (RESOLVED)

1. **Decimal off-ramp: emit integer token or no token?**
   - What we know: D-04 says recover-and-continue; D-02 says report the error; per-off-ramp recovery mechanics are Claude's Discretion.
   - What's unclear: Should the lexer emit `NUMBER("3")` for the integer part of `3.5`, so the parser can continue? Or emit nothing, to avoid partial-data confusion?
   - Recommendation: Emit the integer token. This gives the parser something to consume and allows further errors to be found downstream. The error message is collected regardless.
   - **RESOLVED:** Emit the integer token. Implemented in Plan 01-02 (`3.5` → collect decimal off-ramp error + emit `NUMBER("3")`, then recover past the fraction).

2. **Uniform-step: should a ragged dedent (width not a clean multiple of unit) produce an additional error beyond the standard unmatched-dedent error?**
   - What we know: D-07 says "ragged width" is an error; Pitfall 1 says unmatched dedent is an error. Both could fire on the same line.
   - What's unclear: Does reporting both confuse the learner? Or does the specific "ragged width" message provide more useful guidance than "doesn't match any block"?
   - Recommendation: Report only the unmatched-dedent error when both conditions hold, since it is the more precise structural description. The uniform-step error fires only when the indent stack *did* match (valid dedent level) but the width arithmetic was ragged.
   - **RESOLVED:** Report only the unmatched-dedent error when both conditions hold. Implemented in Plan 01-03 `_handle_indentation`.

3. **EOF with no trailing newline and no content on last line (empty file or file ending with blank line):**
   - What we know: Pitfall 2 says emit a NEWLINE if the last logical line had no trailing `\n`.
   - What's unclear: An empty file or a file that ends in a blank line should produce only `[EOF]` with no NEWLINE. Need to track whether any logical line content was ever emitted.
   - Recommendation: Track a `_last_had_content: bool` flag; only emit the trailing NEWLINE when this flag is True and the last emitted token was not a NEWLINE.
   - **RESOLVED:** Track last-content state; only emit the trailing NEWLINE when the last emitted token was not already a NEWLINE (empty file / trailing-blank-line → `[EOF]` only). Implemented in Plan 01-03 `_drain_at_eof()`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Lexer implementation | ✓ | 3.12.13 | — |
| pytest | Test runner | ✓ | 9.0.3 | — |
| `src/atena/tokens.py` | Lexer imports | ✓ | Phase 0 deliverable | — |
| `src/atena/errors.py` | Lexer imports | ✓ | Phase 0 deliverable | — |
| `src/atena/pipeline.py` | Not needed by lexer | ✓ (stub) | Phase 0 stub | — |

**Missing dependencies with no fallback:** none

**Phase 0 verification:** `python3 -m pytest tests/ --tb=no -q` → 58 passed in 0.26s. All Phase 0 contracts are green and available to Phase 1. [VERIFIED: local environment]

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` under `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) |
| Quick run command | `python3 -m pytest tests/test_lexer.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Three Test Layers for the Lexer

The cross-cutting three-test-layer principle (PITFALLS.md) applied to the lexer:

**Layer 1: Golden token snapshots** — parametrized tests feeding source strings and asserting the exact `list[Token]` produced. Keep these minimal and targeted (one interesting property per test case) rather than snapshotting entire programs, to avoid brittleness. Examples: keyword recognition, INDENT/DEDENT balance for a simple 2-level nesting, `=` vs `==`.

**Layer 2: Error-path message/count/order assertions** — feed deliberately-broken source and assert: (a) the exact plain-English message, (b) the error count, (c) the line number ordering. These lock in the "collect all errors" guarantee and prevent regression of off-ramp messages. Examples: mixed tabs/spaces, staircase-dedent, decimal literal, single-quoted string, unterminated string, colon, semicolon, over-indent.

**Layer 3: No execution layer for the lexer** — the lexer itself produces tokens, not Python. Execution tests begin at the codegen phase. The lexer does have integration with the parser (in later phases), but Phase 1's standalone tests are layers 1 and 2 only.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LEX-01 | All 19 token types produced for appropriate source | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L1_all_token_types -x` | ❌ Wave 0 |
| LEX-01 | Keywords recognized from KEYWORDS dict | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L1_keyword_recognition -x` | ❌ Wave 0 |
| LEX-01 | Identifiers vs keywords distinguished | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L1_identifier_vs_keyword -x` | ❌ Wave 0 |
| LEX-02 | Nested block produces balanced INDENT/DEDENT | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L2_indent_dedent_balanced -x` | ❌ Wave 0 |
| LEX-02 | EOF drains open blocks (no trailing newline) | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L2_eof_drain_no_trailing_newline -x` | ❌ Wave 0 |
| LEX-02 | EOF drains open blocks (mid-block) | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L2_eof_drain_mid_block -x` | ❌ Wave 0 |
| LEX-03 | Blank lines inside block produce no tokens | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L3_blank_line_no_tokens -x` | ❌ Wave 0 |
| LEX-03 | Comment-only lines produce no tokens | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L3_comment_only_no_tokens -x` | ❌ Wave 0 |
| LEX-03 | Deeply-indented comment does not change parse | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L3_deep_comment_no_indent_effect -x` | ❌ Wave 0 |
| LEX-04 | Mixed tabs/spaces → plain-English error | error-path | `python3 -m pytest tests/test_lexer.py::test_L4_mixed_tabs_spaces_error -x` | ❌ Wave 0 |
| LEX-04 | Staircase-dedent → "doesn't match any block" error | error-path | `python3 -m pytest tests/test_lexer.py::test_L4_staircase_dedent_error -x` | ❌ Wave 0 |
| LEX-04 | Over-indent → "indented too far" error | error-path | `python3 -m pytest tests/test_lexer.py::test_L4_over_indent_error -x` | ❌ Wave 0 |
| LEX-04 | Ragged width → "same size" error | error-path | `python3 -m pytest tests/test_lexer.py::test_L4_ragged_width_error -x` | ❌ Wave 0 |
| LEX-05 | `=` produces ASSIGN | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L5_assign_token -x` | ❌ Wave 0 |
| LEX-05 | `==` produces COMPARISON | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L5_eq_comparison_token -x` | ❌ Wave 0 |
| LEX-05 | `!=` `<` `>` `<=` `>=` produce COMPARISON | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L5_all_comparisons -x` | ❌ Wave 0 |
| LEX-05 | `+` `-` `*` `/` produce OPERATOR | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L5_arithmetic_operators -x` | ❌ Wave 0 |
| LEX-06 | All 19 keywords recognized | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L6_all_19_keywords -x` | ❌ Wave 0 |
| LEX-07 | Double-quoted string tokenized with correct value | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L7_string_literal -x` | ❌ Wave 0 |
| LEX-07 | Integer number tokenized correctly | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L7_number_literal -x` | ❌ Wave 0 |
| LEX-07 | Every token stamped with line and source_line | unit/golden | `python3 -m pytest tests/test_lexer.py::test_L7_token_position_fields -x` | ❌ Wave 0 |
| LEX-08 | Unterminated string → plain-English error | error-path | `python3 -m pytest tests/test_lexer.py::test_L8_unterminated_string -x` | ❌ Wave 0 |
| LEX-08 | Decimal number off-ramp message + recovery | error-path | `python3 -m pytest tests/test_lexer.py::test_L8_decimal_offramp -x` | ❌ Wave 0 |
| LEX-08 | Single-quote off-ramp message + recovery | error-path | `python3 -m pytest tests/test_lexer.py::test_L8_single_quote_offramp -x` | ❌ Wave 0 |
| LEX-08 | Colon off-ramp message + recovery | error-path | `python3 -m pytest tests/test_lexer.py::test_L8_colon_offramp -x` | ❌ Wave 0 |
| LEX-08 | Semicolon off-ramp message + recovery | error-path | `python3 -m pytest tests/test_lexer.py::test_L8_semicolon_offramp -x` | ❌ Wave 0 |
| LEX-08 | Unexpected character → generic error | error-path | `python3 -m pytest tests/test_lexer.py::test_L8_unexpected_char -x` | ❌ Wave 0 |
| LEX-02+LEX-08 | Multiple errors collected in one run (collect-all) | error-path | `python3 -m pytest tests/test_lexer.py::test_Lx_multiple_errors_collected -x` | ❌ Wave 0 |
| LEX-08 | Off-ramp recovery always makes progress (no hang) | error-path | `python3 -m pytest tests/test_lexer.py::test_Lx_offramp_no_infinite_loop -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_lexer.py -x -q` (fail-fast on first failure)
- **Per wave merge:** `python3 -m pytest tests/ -q` (full suite including Phase 0 regression)
- **Phase gate:** Full suite green (`python3 -m pytest tests/ -q`) before `/gsd:verify-work`

### Wave 0 Gaps

All test functions above are new. Wave 0 must create:

- [ ] `tests/test_lexer.py` — the main test file; all test functions listed in the Phase Requirements → Test Map
- [ ] `tests/conftest.py` is already present (empty scaffold); may add fixtures like `make_lexer(source)` → `(list[Token], ErrorCollector)` for DRY test setup
- [ ] `src/atena/lexer.py` — the implementation file (starts as stub for RED phase per TDD)

No new test framework installation is required — pytest 9.0.3 is already installed and configured.

---

## Security Domain

> `security_enforcement` is not explicitly set to `false` in config; section required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (offline CLI tool, no auth) |
| V3 Session Management | no | — (stateless single-run tool) |
| V4 Access Control | no | — (no multi-user, no access control surface) |
| V5 Input Validation | yes | Lexer is the first input boundary; all source text is treated as untrusted user input |
| V6 Cryptography | no | — (no cryptographic operations) |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed source causing Python exception in lexer | Tampering → Spoofing (stack trace reaches user) | Wrap all lexer internals in try/except at the driver level (Phase 0 already does this); lexer itself must not raise |
| Infinite loop on adversarial input | Denial of Service | Always-make-progress invariant (every code path in the scan loop advances `pos` by ≥1); progress guard in the main loop |
| Unbounded token list from extremely large input | Denial of Service | Teaching context makes this low-risk; no mitigation needed for v1.0 |
| Source path traversal (reading wrong file) | Elevation of Privilege | Handled at CLI layer (Phase 0); lexer only receives already-read `str`, never a path |

**Lexer-specific security note:** The lexer receives a raw `str` and must produce only `Token` objects and `ErrorCollector` entries. It must never: raise an uncaught exception, execute any subshell, open any file, or access any resource beyond its two constructor arguments. The always-make-progress invariant and the try/except safety net in the driver are the two controls that keep the "no Python traceback ever reaches the learner" promise.

---

## Sources

### Primary (HIGH confidence)

- `src/atena/tokens.py` (project file) — `TokenType` enum (19 members), `Token` dataclass fields, `KEYWORDS` dict (19 entries). The lexer's exact output contract. [VERIFIED: read directly]
- `src/atena/errors.py` (project file) — `ErrorCollector.add(line, message, source_line)` signature, `ERROR_CAP`, `report()` format. The only error reporting channel. [VERIFIED: read directly]
- `.planning/research/ARCHITECTURE.md` (project file) — Patterns 1–4 (indentation stack, tabs/spaces, blank/comment skip, maximal-munch); Lexer responsibility table; project structure; Contract A. [VERIFIED: read directly]
- `.planning/research/PITFALLS.md` (project file) — Pitfalls 1–4 (unmatched dedent, EOF drain, blank/comment spurious tokens, mixed tabs/spaces); three-test-layer principle; "Looks Done But Isn't" checklist. [VERIFIED: read directly]
- `.planning/research/STACK.md` (project file) — Python 3.11+ floor, stdlib-only, hand-rolled lexer rationale, indentation-stack pattern. [VERIFIED: read directly]
- `.planning/phases/01-lexer/01-CONTEXT.md` (project file) — D-01 through D-08, off-ramps, uniform-step decisions, Claude's Discretion items. [VERIFIED: read directly]
- `tests/test_tokens.py` (project file) — existing test style (plain `assert`, no classes, `test_T{N}_` naming). Style to mirror in `test_lexer.py`. [VERIFIED: read directly]
- `python3 -m pytest tests/ --tb=no -q` — 58 passed, Phase 0 green. [VERIFIED: local environment]

### Secondary (MEDIUM confidence)

- `.planning/phases/00-diagnostics-spine-data-contracts/00-CONTEXT.md` — Phase 0 error voice (D-01 Plain & kind, D-02 internal-error fallback, D-03 problem+guidance); `<specifics>` exemplars as canonical voice reference. [VERIFIED: read directly]
- Python Language Reference §2 Lexical Analysis — INDENT/DEDENT stack algorithm, blank/comment-line handling, EOF DEDENT generation — cited in ARCHITECTURE.md and PITFALLS.md. [CITED: docs.python.org/3/reference/lexical_analysis.html]

### Tertiary (LOW confidence)

None — all claims in this research are verified from project files or cited from official Python documentation.

---

## Metadata

**Confidence breakdown:**
- Standard stack / EOF drain / blank-comment skip: HIGH — CPython algorithm, extensively documented in project research files
- Uniform-step validation layer: HIGH — derived directly from locked decisions D-05/D-06/D-07; logic is straightforward
- Off-ramp detection and recovery mechanics: HIGH (detection) / MEDIUM (exact recovery mechanics — Claude's Discretion items marked [ASSUMED])
- Token contract / ErrorCollector contract: HIGH — verified from Phase 0 source files
- Test coverage plan: HIGH — derives from requirement IDs and the three-test-layer principle

**Research date:** 2026-06-13
**Valid until:** Stable (this is a Phase 0 → Phase 1 internal contract; no external dependency drift)
