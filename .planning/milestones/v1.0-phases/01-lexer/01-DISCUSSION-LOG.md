# Phase 1: Lexer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 1-Lexer
**Areas discussed:** Out-of-scope off-ramps, Indentation strictness

---

## Gray-area selection

Four phase-specific gray areas were presented (multi-select). The user chose to discuss two; the other two were resolved by Claude's discretion.

| Gray area | Description | Discussed |
|-----------|-------------|-----------|
| Comment marker | What character starts a comment (`#`, `//`, …) — never pinned in the spec | — (defaulted to `#`) |
| Out-of-scope off-ramps | Tailored teaching messages for out-of-scope syntax the lexer meets first | ✓ |
| Lexer error wording | Exact text for the 4 new lexer errors | — (drafted in Phase 0 voice) |
| Indentation strictness | Uniform indent width vs. Python-style any-increase | ✓ |

---

## Out-of-scope off-ramps

**Q1 — How hard should the lexer work to catch out-of-scope syntax with teaching messages?**

| Option | Description | Selected |
|--------|-------------|----------|
| Tailored off-ramps | Detect common out-of-scope attempts and emit a specific redirect | ✓ |
| Generic only | One catch-all "I don't understand this character" message | |
| You decide | Claude picks the set | |

**Q2 — Which out-of-scope attempts should get a tailored message?** (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Decimal numbers | `3.5` → "Atena uses whole numbers only" | ✓ |
| Single-quoted strings | `'hello'` → "use double quotes" | ✓ |
| Python-style colon | `if x:` → "Atena doesn't use colons — just indent" | ✓ |
| Semicolons | `a = 1; b = 2` → "Put each step on its own line" | ✓ |

**User's choice:** Tailored off-ramps for all four constructs.
**Notes:** Confirmed (no objection) that off-ramps are collected errors with recover-and-continue, consistent with the locked collect-all-errors principle. Chose "Next area" without further sub-questions.

---

## Indentation strictness

**Q1 — How strict should Atena be about the width of each indentation step?**

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform step (strict) | Every indent the same width across the file | ✓ |
| Any consistent increase | Python-style; only dedents must match an open level (research default) | |
| You decide | Claude weighs and picks | |

**Q2 — How is the required indent width determined for a file?**

| Option | Description | Selected |
|--------|-------------|----------|
| First indent sets it | First indented line pins the unit; parallels the locked tab/space rule | ✓ |
| Fixed 4 spaces / 1 tab | Mandate a specific unit | |
| You decide | Claude picks the cleanest composition | |

**User's choice:** Strict uniform-step; the first indented line sets both the character and the unit width.
**Notes:** Accepted (no objection) that a block opens exactly one unit deeper, and that over-indenting two units at once becomes its own friendly error — the natural reading of "uniform step." Confirmed readiness for context after this area.

---

## Claude's Discretion

- **Comment marker = `#`** (area not selected; defaulted — matches Python and research example; flagged in CONTEXT.md to confirm against the source spec if it surfaces).
- **Exact error wordings** for all new lexer errors — drafted in the Phase 0 voice; starting drafts recorded in CONTEXT.md `<specifics>`.
- **Per-off-ramp recovery mechanics**, `col` precision, and the (no-op) string-escape behavior — left to research/planning.

## Deferred Ideas

None — discussion stayed within phase scope. A `\n`-style string-escape off-ramp is noted as a candidate v2 enhancement (not a v1.0 deferral).
