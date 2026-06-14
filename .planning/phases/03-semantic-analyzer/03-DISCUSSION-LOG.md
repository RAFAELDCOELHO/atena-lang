# Phase 3: Semantic Analyzer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 3-Semantic Analyzer
**Areas discussed:** Unknown-type coercion, Index check timing, Scope around functions

---

## Gray-area selection

Presented four phase-specific gray areas; user selected three to discuss. The fourth — **Type-checks beyond `+`** — was left to the research default (analyzer type-checks `+` only; `- * /` and comparison mismatches are handled by the Phase-5 runtime translation layer). Recorded as D-04 in CONTEXT.md.

---

## Unknown-type coercion

**Q1 — When a `+` has an operand whose type can't be determined at compile time (function return, parameter), how should the analyzer handle it?**

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime concat helper | Route `+` with any UNKNOWN operand through a generated `_atena_concat(a,b)` that decides string-vs-number at runtime; never crashes. Honors "silent coercion never crashes". | ✓ |
| Bare Python + | Emit plain `a + b`; a real type mismatch raises at runtime unless the Phase-5 wrapper reformats it. | |
| Require known types | Error at compile time when a `+` operand's type is unknown; rejects legitimate beginner programs. | |

**User's choice:** Runtime concat helper
**Notes:** STATE.md had flagged this as the open Phase-3 decision; now resolved. Helper *body* is emitted in Phase 4; analyzer only routes.

**Q2 — What type should the analyzer give the result of `ask` (keyboard input)?**

| Option | Description | Selected |
|--------|-------------|----------|
| String | `ask` returns text (Python `input()` → str); `answer + 1` wraps the 1 via `str()`. Honest to runtime; keeps `+` static where possible. | ✓ |
| Unknown | Treat `ask` results as UNKNOWN; any `+` routes through the runtime helper. More uniform but emits the helper even for plain text concat. | |

**User's choice:** String
**Notes:** Known v1.0 limitation accepted — no number-parsing, so math on `ask` input concatenates rather than adds.

---

## Index check timing

**Q1 — Which index forms should the analyzer resolve at compile time vs route to the runtime `_atena_index` helper?**

| Option | Description | Selected |
|--------|-------------|----------|
| Literals incl. -n | Bare number and negated literal (`-3`) handled at analysis time (positive folds to n-1; 0/negative error with line number); variables + all arithmetic → runtime helper. | ✓ |
| Constant-fold too | Also evaluate all-number constant expressions (`2+1`) at analysis time; adds a constant-evaluator. | |
| Bare literal only | Only a plain NumberLiteral is compile-time; `-3` is left to the runtime helper. | |

**User's choice:** Literals incl. -n

**Q2 — For a literal negative index like `items[-3]`, same message as literal-0 or distinct?**

| Option | Description | Selected |
|--------|-------------|----------|
| Same message | Reuse `Lists in Atena start at 1, not 0.` for both. One consistent rule. | |
| Distinct negative message | Separate negatives-specific line; targets the Python from-the-end mental model. | ✓ |

**User's choice:** Distinct negative message
**Notes:** Distinct wording applies to compile-time literal negatives only; the runtime `_atena_index` helper keeps a single unified `i < 1` message.

---

## Scope around functions

**Q1 — How should the analyzer model variable scope (given the generated Python has real function-local scope)?**

| Option | Description | Selected |
|--------|-------------|----------|
| Two-level, read globals | Top-level globals + per-function locals; a function may READ top-level vars defined before it; locals don't leak. Matches Python exactly. | |
| Two-level, params only | Same two levels, but a function may NOT read top-level vars — only its params, locals, and earlier-defined functions. Teaches passing data via parameters. | ✓ |
| Flat single scope | One namespace; any assigned name visible everywhere. Diverges from generated Python; risks analyzer-OK / runtime-crash. | |

**User's choice:** Two-level, params only (pure functions)
**Notes:** Stricter, more teachable model. Payoff: valid programs never rely on Python's implicit global read, so Phase-4 output stays clean.

**Q2 — When a function body references a name that exists only as a top-level variable, what should the learner see?**

| Option | Description | Selected |
|--------|-------------|----------|
| Tailored teaching message | Detect the name exists at top level but isn't reachable; say "A function can only use its own inputs — pass X in as a parameter." | ✓ |
| Standard undefined-name | Reuse the generic "I don't know what X is yet" + "Did you mean?" message. | |

**User's choice:** Tailored teaching message
**Notes:** Fires only when the name exists at top level; a name that exists nowhere still gets the standard undefined-name + suggest() path.

---

## Claude's Discretion

- How decisions are recorded on the AST (FunctionCall-node injection vs flags); symbol-table structure; runtime-helper naming (`_atena_` prefix).
- Reassignment / cross-branch type changes → fall back to UNKNOWN (documented limitation).
- Function-vs-variable name collisions → treat as one namespace to match Python.
- Exact message wordings (drafts in CONTEXT.md `<specifics>`).

## Deferred Ideas

- Compile-time rejection of obviously-disallowed non-`+` literal combos (`"a" - 1`) — future refinement to D-04.
- Number-parsing for `ask` input — out of v1.0 scope (integers-only); v2 candidate.
