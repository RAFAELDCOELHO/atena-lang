# Phase 1: Lexer - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 turns Atena **source text into a correct, balanced token stream** (`list[Token]`) that the Parser can consume — the first real phase of the pipeline, plugging into the Phase 0 diagnostics spine and data contracts.

Concretely it delivers a `Lexer` (`src/atena/lexer.py`) that:

- Char-by-char scans source into the locked `TokenType` set (`tokens.py`), classifying keywords vs identifiers, reading double-quoted strings and integer numbers, and distinguishing `=` from `==` by maximal munch.
- Owns the **indentation stack** and emits balanced `INDENT`/`DEDENT`/`NEWLINE`, draining all open blocks at EOF (even mid-block / no trailing newline).
- **Skips blank and comment-only lines** entirely (no tokens, stack untouched) — measured *before* touching indentation.
- Enforces the indentation policy (tabs OR spaces, not mixed — and, per this discussion, a **uniform step width**) and reports plain-English errors through the shared `ErrorCollector`.
- Stamps every token with `line`, `col`, and the full `source_line` text.

Covers requirements **LEX-01 … LEX-08**.

**In scope:** tokenization, INDENT/DEDENT/NEWLINE emission, blank/comment skipping, indentation policy + uniform-step enforcement, `=`/`==` munch, string/number/keyword/operator recognition, lexer-level error reporting (unterminated string, unexpected character, indentation errors, out-of-scope off-ramps).
**Not in scope:** parsing/AST (Phase 2), any semantic decision (Phase 3), codegen (Phase 4), pipeline wiring + `atena run`/`build` (Phase 5). The lexer never raises to the user — it only `add()`s to the `ErrorCollector` and returns whatever tokens it produced.

</domain>

<decisions>
## Implementation Decisions

### Out-of-scope off-ramps (the LEX-08 error experience)

The lexer is the **first phase a learner's mistake reaches**. When a learner types something deliberately left out of v1.0, the lexer redirects them rather than dead-ending.

- **D-01 — Tailored teaching off-ramps (not generic).** For the out-of-scope constructs it can detect at lex time, the lexer emits a **specific, redirecting** plain-English message — not the generic "unexpected character." Rationale: a concrete redirect turns a dead end into a one-edit fix and serves the teaching mission. Anything *not* in the detected set (e.g. `@`, `$`, `%`, backtick) still falls through to the generic LEX-08 "unexpected character" message.
- **D-02 — The four detected off-ramps** (all confirmed by the user):
  1. **Decimal numbers** — digit-dot-digit, e.g. `3.5`, `3.14` → "Atena uses whole numbers only" + concrete redirect (e.g. "try `3` or `4`"). Floats are explicitly v2/Out-of-Scope, so this is a frequent honest mistake.
  2. **Single-quoted strings** — a `'` opening text, e.g. `'hello'` → "Atena text goes in double quotes" + redirect to `"hello"`.
  3. **Python-style trailing colon** — `:`, e.g. `if x > 1:` → "Atena doesn't use colons — just indent the next line." Highest-value off-ramp: the #1 Python muscle-memory mistake for any learner or teacher who has seen Python.
  4. **Semicolons** — `;`, e.g. `a = 1; b = 2` → "Put each step on its own line." Reinforces the one-statement-per-line model.
- **D-03 — Voice: guide, don't just describe.** Off-ramp messages follow the locked Phase 0 voice (first-person, calm, "Plain & kind"). Because each off-ramp has a *genuine known fix*, each message **guides** toward the v1.0 alternative (Phase 0 D-03's "problem + guidance when clear" — here the cause is never ambiguous, so always guide).
- **D-04 — Collected + recover-and-continue.** Off-ramps are **collected errors** (Atena has no "warning" concept; the run fails and codegen is gated downstream). The lexer **recovers and keeps scanning** after each one so a learner sees every off-ramp in a single run (collect-all-errors, DIAG-02). Per-construct recovery mechanics are Claude's discretion (see below).

### Indentation strictness (LEX-02 / LEX-04)

- **D-05 — Strict uniform-step indentation (stricter than CPython).** Atena enforces a **consistent indent unit**, not merely a consistent relative increase. Rationale: teaches tidy, consistent code and makes block structure visually unambiguous for beginners. This is a deliberate pedagogical choice over the lenient CPython default the research recommended.
- **D-06 — First indented line sets the unit.** The first indented line of a file pins **both** the indent character (tab vs space — already locked by PROJECT.md/research) **and** the unit width (how many of that character). Each file may choose its own unit (2 spaces, 4 spaces, 1 tab); it must then be consistent within that file. This parallels and extends the already-locked "first indented line sets the character" rule.
- **D-07 — One unit per block; over-indent and ragged widths are errors.** A block opens **exactly one unit deeper** than its parent. Each is a friendly plain-English error:
  - **Over-indent** — jumping two-or-more units in one step (or a width that isn't a clean unit step) → "you indented too far / keep your indents the same size."
  - **Ragged width** — a level whose indentation isn't the established unit deeper → friendly error.
  - **Unmatched dedent** — dedent to a level never opened (the "staircase" bug) → "this line's indentation doesn't match any open block." Already required by ROADMAP success criterion #3 (Pitfall 1); uniform-step makes it stricter, never weaker.
- **D-08 — Still built on the standard machinery.** Uniform-step is a *validation layer on top of* — not a replacement for — the indentation **stack** algorithm (ARCHITECTURE Pattern 1), the **EOF drain** (Pitfall 2), and **skip-blank/comment-before-measuring** (Pattern 3). Keep those exactly as researched.

### Claude's Discretion

The user did not constrain these; resolve during research/planning (honor the locked items above):

- **Comment marker = `#`** (the user did not select the "comment marker" area; defaulted here). Single character, matches Python and the FEATURES.md example, familiar. A comment runs from `#` to end of line; comment-only and blank lines are skipped *before* indentation is measured (no NEWLINE/INDENT/DEDENT). If a more beginner-friendly marker is wanted later, it's a one-line change. **Flag for planning:** this is a real language-design default, not a verified spec fact — confirm against the user's source spec if/when it surfaces.
- **Exact wordings** for the new lexer errors (over-/ragged/unmatched indentation, mixed tabs/spaces, unterminated string, unexpected character, and the four off-ramps) — draft in the Phase 0 voice. The Phase 0 `<specifics>` exemplars are the style guide; starting drafts are in `<specifics>` below.
- **Per-off-ramp recovery mechanics** — how far to skip after each detected off-ramp (e.g. decimal: emit the integer part then treat the rest / consume the fraction; single-quote: scan to the closing `'` or end of line; colon/semicolon: skip the one character and continue). Must satisfy the "always make progress / never hang" invariant.
- **`col` precision** — `Token` carries a `col` field (Phase 0 left exact column semantics to later phases); decide how precisely it is populated. Line + `source_line` are mandatory and must be exact.
- **String escapes** — v1.0 has **no** escapes (Out-of-Scope). A backslash inside a `"…"` string is a literal backslash; the lexer does not process `\n`/`\"`. A learner typing `\n` gets a literal backslash-n — acceptable for v1.0, not pinned as an off-ramp (candidate v2 off-ramp).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 1: Lexer" — the 5 success criteria (what must be TRUE), dependency (Phase 0), and the LEX-01…LEX-08 requirement mapping. Note success criterion #3 (staircase-dedent + mixed-tabs/spaces errors) is now *stricter* under D-05/D-07.
- `.planning/REQUIREMENTS.md` §"Lexer" — LEX-01 … LEX-08 verbatim.

### Architecture & contracts (authoritative for HOW)
- `.planning/research/ARCHITECTURE.md` — **the single most relevant doc.** Especially: Pattern 1 (indentation stack), Pattern 2 (tabs-OR-spaces, character-count measure — extend with D-05/D-06 uniform-step), Pattern 3 (skip blank/comment-only lines), Pattern 4 (maximal-munch `=` vs `==`); the Lexer component responsibility table; the project structure (`src/atena/lexer.py`); contract A (the flat, INDENT/DEDENT-balanced token list).
- `.planning/research/PITFALLS.md` — Lexer-owned pitfalls **1** (unmatched-level dedent → assert new top equals current), **2** (EOF drains open blocks; emit final NEWLINE if missing), **3** (blank/comment lines must NOT touch the stack or emit tokens), **4** (mixed tabs/spaces) — plus the cross-cutting three-test-layer principle and the "Looks Done But Isn't" lexer checklist items.
- `.planning/research/STACK.md` — Python 3.11+ floor, stdlib-only, hand-rolled lexer rationale (why not Lark), the standard line-by-line indentation-stack pattern, `keyword.kwlist` as stdlib keyword source.
- `.planning/PROJECT.md` §Constraints / §Key Decisions — indentation-delimited blocks; **consistent tabs OR spaces, not mixed**; double-quoted strings + integers only; collect-all-errors over fail-fast; no traceback ever; TDD + per-phase feature branch (`feat/lexer`); one phase 100% green before advancing.

### Diagnostics spine the lexer plugs into (locked Phase 0 contracts)
- `.planning/phases/00-diagnostics-spine-data-contracts/00-CONTEXT.md` — the **error voice** (D-01 "Plain & kind", D-02 internal-error fallback, D-03 problem+guidance) the lexer's messages MUST match; the `<specifics>` exemplars are the canonical voice.
- `src/atena/tokens.py` — `TokenType` enum (19 members), frozen `Token` dataclass (`type, value, line, col, source_line`), `KEYWORDS` map (19 words). The lexer's output contract — do not redefine.
- `src/atena/errors.py` — `ErrorCollector.add(line, message, source_line)` (the only way the lexer reports), `ATENA_KEYWORDS` list, `suggest(name, candidates)` (available if the lexer ever needs a keyword-typo hint).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/atena/tokens.py`** — `TokenType` (all token kinds incl. INDENT/DEDENT/NEWLINE/EOF), the frozen `Token` dataclass, and the `KEYWORDS` dict are the lexer's exact output contract. The lexer constructs `Token`s and looks identifier-shaped text up in `KEYWORDS` (hit → KEYWORD, miss → IDENTIFIER).
- **`src/atena/errors.py`** — inject the shared `ErrorCollector` into the `Lexer` constructor; report every lexer error via `add(line, message, source_line)`. `ATENA_KEYWORDS`/`suggest()` are available for keyword-typo suggestions if desired (optional for the lexer).
- **`tests/test_tokens.py`** — existing token-contract tests show the construction/usage conventions; mirror its style in a new `tests/test_lexer.py`.

### Established Patterns
- **Pure data modules stay dependency-free** — `tokens.py` imports nothing sibling; the lexer imports `tokens` + `errors` only. Keep `lexer.py` self-contained otherwise.
- **ErrorCollector is injected, never global** — the lexer takes it as a constructor arg (Phase 0 / ARCHITECTURE boundary).
- **TDD per PROJECT.md** — failing test first, commit after each task, work on `feat/lexer` (never `main`). Three test layers apply: golden token snapshots, plus error-path tests asserting exact message / count / line order. (No "execution" layer for the lexer specifically — that begins at codegen.)
- **`errors.py` owns the `Error on line {N}: … → {source}` format** — the lexer supplies only the plain-English `message`; it never formats.

### Integration Points
- **Lexer → Parser (contract A):** a fully-materialized `list[Token]` (not a generator) with balanced INDENT/DEDENT and a trailing EOF, so the Phase 2 parser can peek/lookahead freely.
- **Lexer → ErrorCollector:** the cross-cutting injection point; the driver (Phase 5) will inspect `is_empty()` between phases.
- **`src/atena/lexer.py` does not exist yet** — Phase 1 creates it (and `tests/test_lexer.py`). `pipeline.py` wiring is Phase 5, not here.

</code_context>

<specifics>
## Specific Ideas

Draft message exemplars surfaced during discussion — **starting drafts**, to be refined into the exact Phase 0 voice during planning/implementation (match `00-CONTEXT.md` `<specifics>` for tone). All guide toward the v1.0 fix:

- Decimal off-ramp: `Atena works with whole numbers only — try 3 or 4 instead of 3.5.`
- Single-quote off-ramp: `Atena text goes inside double quotes — try "hello".`
- Colon off-ramp: `Atena doesn't use colons — just indent the next line to start the block.`
- Semicolon off-ramp: `Put each step on its own line.`
- Over-indent: `This line is indented too far — keep each step the same size.`
- Ragged/inconsistent indent: `Keep your indentation the same size as the rest of the file.`
- Unmatched dedent (already required): `This line's indentation doesn't match any block above it.`
- Mixed tabs/spaces (already required): `Don't mix tabs and spaces for indentation — pick one and use it everywhere.`

These are guidance drafts, not locked strings — the *decisions* (which off-ramps, strict uniform-step, guide-don't-describe) are locked; the exact wording is Claude's discretion within the Phase 0 voice.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (String-escape handling and float numbers are existing Out-of-Scope items, not new deferrals; a `\n`-style off-ramp message is noted as a candidate v2 enhancement under Claude's Discretion, not a v1.0 deferral.)

</deferred>

---

*Phase: 1-Lexer*
*Context gathered: 2026-06-13*
