# Atena Language

## What This Is

Atena v1.0 is a teaching programming language that transpiles to runnable Python 3. It strips away syntactic noise — no colons, no braces — and uses indentation-delimited blocks with plain English keywords (`show`, `ask`, `repeat`, `function`). It is built for complete non-programmers learning algorithmic logic, while still exposing real engineering concepts: functions, control flow, lists, and dictionaries. The transpiler is a single-pass pipeline of four sequential phases — Lexer → Parser → Semantic Analyzer → Code Generator — written in Python 3.

## Core Value

A complete non-programmer can write real algorithmic logic (functions, control flow, lists, dicts) without ever fighting syntax, and never sees a Python stack trace — only plain-English errors that name the line and show the offending code.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Lexer tokenizes Atena source into a token stream with INDENT/DEDENT emission, skipping blank and comment-only lines
- [ ] Parser builds a complete AST from the token stream honoring the defined operator precedence
- [ ] Semantic analyzer injects type coercion (`str()` wrapping), converts 1-indexed access to 0-indexed, and detects undefined variables and function arity errors
- [ ] Code generator emits valid, runnable Python 3 from the analyzed AST
- [ ] All plain-English errors follow the `Error on line {N}: ... → {source}` format with no stack traces or jargon
- [ ] Errors are collected across a run (error recovery), not halted at the first one
- [ ] CLI: `atena run file.atena` executes the program; `atena build file.atena` emits the `.py` file
- [ ] Packaging (pip-installable entry point) and user-facing docs/tutorial
- [ ] Teaching curriculum: a set of example `.atena` programs demonstrating each language concept

### Out of Scope

<!-- Explicit boundaries for v1.0. Includes reasoning to prevent re-adding. -->

- `elif` — use nested if/else; keeps control-flow grammar minimal for learners
- Float numbers — integers only in v1.0; avoids precision/formatting teaching detours
- String escaping (`\"`, `\n`) — double-quoted literals only; reduces lexer complexity
- Negative list indices — Atena is 1-indexed; negatives would confuse the mental model
- List slicing — beyond v1.0 scope; not needed for foundational logic
- Default function parameters — keeps the function model simple
- Nested functions / closures — flat scope only; closures are an advanced concept
- Classes / OOP — v1.0 teaches procedural logic only
- Module imports — single-program model in v1.0
- Multi-file programs — one `.atena` file per run
- REPL / interactive mode — file-based transpilation only

## Context

- **Pedagogical framing:** Every design choice serves the goal of teaching algorithmic thinking to people who have never programmed. Syntactic noise is the enemy; readability of both the language and its errors is paramount.
- **Reference spec:** The user provided a complete language specification — grammar reference, type coercion rules, error message format, a complete example program with its expected Python 3 output, and the four-phase transpiler architecture. This spec is the source of truth for v1.0 behavior.
- **1-indexing:** `items[1]` is the first element and transpiles to `items[0]`. `items[0]` is a deliberate error ("Lists in Atena start at 1, not 0"). The analyzer owns the 1→0 rewrite.
- **Silent type coercion:** `string + number` and `string + boolean` auto-wrap the non-string side in `str()` so mixed-type concatenation never crashes. `number + number` and `string + string` are untouched. Other combinations are a plain-English error.
- **Golden example:** The spec's complete test script (`school.atena`-style) and its expected Python output form the canonical end-to-end integration fixture.

## Constraints

- **Tech stack**: Python 3 — the transpiler is written in Python 3 and emits Python 3. Standard library only unless a dependency proves necessary.
- **Architecture**: Four sequential phases (Lexer → Parser → Analyzer → Generator). Build one phase at a time; do not advance until the current phase is 100% green.
- **Process**: TDD — write the failing test first, then implement. Commit after every completed task. Feature branch per phase (`feat/lexer`, `feat/parser`, …); never work directly on `main`.
- **Indentation**: Blocks are indentation-delimited. A single file must use consistent tabs OR spaces (not mixed).
- **Errors**: All user-facing errors are plain English with line number and offending source line. No Python stack traces ever reach the learner. Errors are collected across a run, not fail-fast.
- **Strings/Numbers (v1.0)**: Double-quoted strings only; integers only.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Collect all errors (error recovery) over fail-fast | Friendlier for non-programmers — surface every problem in one run instead of one-at-a-time; each phase gathers what it can, codegen runs only when zero errors remain | — Pending |
| `atena run` executes, `atena build` emits `.py` | Learners can run immediately (`run`) or inspect the generated Python (`build`) to connect Atena to real code | — Pending |
| Ship packaging + docs + teaching curriculum, not just the transpiler | The product is a learning tool; a correct compiler nobody can install or learn from doesn't deliver the core value | — Pending |
| 1-indexed lists, `[0]` is an error | Matches the human mental model of "first, second, third"; the deliberate `[0]` error teaches the convention | — Pending |
| Silent string coercion via `str()` injection | Mixed-type concatenation should never crash a beginner's program | — Pending |
| Four sequential phases, one at a time, TDD-gated | Each phase has a clean contract (tokens → AST → analyzed AST → Python); 100%-green gate prevents compounding bugs downstream | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-13 after initialization*
