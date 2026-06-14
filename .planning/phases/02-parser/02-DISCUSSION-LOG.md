# Phase 2: Parser - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 2-Parser
**Areas discussed:** ask input syntax, Python-ism redirects

**Areas offered but not selected by the user:** Syntax-error guidance specificity; Recovery aggressiveness on a broken compound block — both left to Claude's discretion under the locked Phase-0 voice + research synchronization design.

---

## ask input syntax

### Q1 — How does a learner read keyboard input into a variable?

| Option | Description | Selected |
|--------|-------------|----------|
| `ask "Q?" name` (positional) | Matches the AST node exactly (prompt + target filled); no new keyword; two bare tokens in a row reads less like English | |
| `name = ask "Q?"` (assignment) | Reads like "name gets the answer"; reuses familiar assignment; makes ask a value-expression, node's target field folds into an Assign | ✓ |
| `ask "Q?" to name` (reuse `to`) | Connector using the existing `to` keyword; reads as English, no new keyword; mild overload of `to` (destination of an add) | |

**User's choice:** `name = ask "Q?"` (assignment style)

### Q2 — Where is `ask` allowed to appear in a program?

| Option | Description | Selected |
|--------|-------------|----------|
| Assignment RHS only | `name = ask "..."` is the ONLY form; dedicated statement; input always lands in a name; misuse elsewhere is a friendly error | ✓ |
| Any expression | ask works anywhere a value does (`show ask "..."`, arithmetic, conditions); maximally composable but invites confusing one-liners | |
| RHS + bare statement | Allow `name = ask "..."` plus a standalone `ask "..."` that discards the answer (press-enter pause) | |

**User's choice:** Assignment RHS only
**Notes:** Resolves the grammar — `ask` is a dedicated statement form. Exact AST node construction (Assign-wrapping-Ask vs. Ask-with-target) left to planning; both satisfy contract B.

---

## Python-ism redirects

### Q1 — How should the parser respond to token-valid but grammatically-wrong Python habits?

| Option | Description | Selected |
|--------|-------------|----------|
| Curated tailored set | Known Python-isms get specific redirects; generic plain-English syntax error otherwise. Mirrors Phase-1 off-ramp pattern. | ✓ |
| Generic only | Only generic syntax errors; lean on the analyzer's undefined-name + "Did you mean?" for name-shaped mistakes | |
| Tailored, maximal | Redirect every recognizable Python construct the parser can detect; most coverage, larger table, more false-fire risk | |

**User's choice:** Curated tailored set

### Q2 — Which Python-ism categories earn a tailored redirect? (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Out-of-scope keywords | def→function, elif→nested if/else, for…in→repeat/while, class→no classes, import→single file | ✓ |
| `==` used as assignment | Standalone `x == 5` → "Did you mean x = 5? One = saves, == compares" | ✓ |
| Top-level `return` | `return` outside a function → "return only works inside a function"; parser owns the message via nesting tracking | ✓ |
| Capitalized true/false/None | Map True/False/None to true/false; name-shaped, normally caught by analyzer case-only "Did you mean?" | |

**User's choice:** Out-of-scope keywords, `==` used as assignment, Top-level return
**Notes:** Capitalized `True`/`False`/`None` deliberately left to the Phase-3 analyzer — clean boundary: parser owns *structural* Python-isms, analyzer's suggestion engine owns *name-shaped* ones. Catching `==`-as-assignment implies the parser disallows meaningless bare-expression statements (only assignments, calls, keyword statements, add/remove are valid) — flagged for the planner.

---

## Claude's Discretion

- Parsing technique (Pratt recommended) and synchronization mechanics / progress-invariant loop guard.
- Bare-expression-statement policy (implied by `==`-redirect): no meaningless bare expressions at statement position.
- Empty blocks / empty program handling (lean: friendly "needs an indented line").
- `col` precision on AST nodes (line + source_line mandatory and exact).
- Exact message wordings for all redirects and syntax errors (drafts in CONTEXT.md `<specifics>`).
- The two unpicked gray areas: syntax-error guidance specificity, and recovery aggressiveness on a broken compound header (one-mistake ≈ one-error bias).

## Deferred Ideas

None — discussion stayed within phase scope. (Name-shaped Python literals/builtins → Phase-3 analyzer by design, not a deferral.)
