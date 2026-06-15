# Phase 6: Packaging & Curriculum - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 6-Packaging & Curriculum
**Areas discussed:** Concept-ladder shape, README scope & voice

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Concept-ladder shape | Granularity, structure, naming, theme of the example programs | ✓ |
| README scope & voice | Depth, tone, structure of the getting-started guide | ✓ |
| Packaging polish & version | pyproject metadata, version bump, install method, PyPI vs repo | (deferred to Claude's Discretion) |
| Example testability & input | Execution tests per example; interactive `ask` handling | (deferred to Claude's Discretion) |

---

## Concept-ladder shape

### Q1 — How should the examples relate to each other?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone rungs + capstone | Each numbered file isolates ONE concept; school.atena is the capstone | ✓ |
| Cumulative themed story | Examples share a theme and grow step-by-step into school.atena | |
| Independent, no theme | Tiny isolated snippets, no shared domain | |

**User's choice:** Standalone rungs + capstone

### Q2 — How granular should the rungs be?

| Option | Description | Selected |
|--------|-------------|----------|
| Finer climb (~8-9 rungs) | Roadmap order, but split distinct constructs (while/repeat, show/ask); one idea per file | ✓ |
| Exactly the roadmap's 7 | One file per listed concept; loops file shows while + repeat together | |
| You decide the breakdown | Claude chooses | |

**User's choice:** Finer climb (~8-9 rungs)

### Q3 — How much explanation inside each file (`#` comments)?

| Option | Description | Selected |
|--------|-------------|----------|
| Teaching comments | Short header naming the concept + a few inline notes; file teaches itself | ✓ |
| Light header only | One or two comment lines at top; clean code below | |
| No comments, clean code | All explanation lives in the README | |

**User's choice:** Teaching comments

### Q4 — Include an interactive `ask` (input) example?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — teach show + ask | Include an `ask` rung; prepares the learner for school.atena | ✓ |
| Output-only, ask in capstone | Keep all rungs non-interactive; `ask` only in school.atena | |
| You decide | Claude chooses | |

**User's choice:** Yes — teach show + ask

---

## README scope & voice

### Q1 — How deep should the README go?

| Option | Description | Selected |
|--------|-------------|----------|
| Full getting-started guide | Install → verbs → first-program walkthrough → language-basics cheatsheet → examples pointer | ✓ |
| Quickstart + link to examples | Install, run/build, hello-world, then "see examples/" | |
| You decide the depth | Claude chooses | |

**User's choice:** Full getting-started guide

### Q2 — What voice should the README use?

| Option | Description | Selected |
|--------|-------------|----------|
| Warm, beginner-first | Same friendly plain-English voice as Atena's errors; zero-background assumed | ✓ |
| Neutral technical docs | Standard concise README voice; assumes some technical familiarity | |
| You decide | Claude chooses | |

**User's choice:** Warm, beginner-first

### Q3 — Showcase Atena's plain-English error experience?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — "when you make a mistake" | A buggy program + the gentle line-numbered Atena error it produces | ✓ |
| Mention briefly in intro | One sentence, no worked example | |
| Skip it | Focus on install, syntax, running | |

**User's choice:** Yes — "when you make a mistake"

### Q4 — How should the README open?

| Option | Description | Selected |
|--------|-------------|----------|
| Brief "what & why" hook | 2-3 sentences on what/who/transpiles-to-Python, then install | ✓ |
| Straight to install/usage | Minimal preamble | |
| You decide | Claude chooses | |

**User's choice:** Brief "what & why" hook

---

## Additional decision (user free-text, at the "ready for context" gate)

**User added:** The README must include a **"For teachers"** section — one paragraph on how to use the ~9-rung ladder as a classroom curriculum (one concept per class, ~50 minutes each). The user framed this as the differentiator that turns Atena from a tool into a curriculum. Captured as D-09.

---

## Claude's Discretion

- **Packaging polish & version (PKG-01):** pyproject metadata fleshed out (readme, license, authors, education classifiers, keywords, URLs); version `0.1.0` → `1.0.0`; keep zero deps. (D-10)
- **Install story (PKG-01):** document repo-install (`pip install .`, `pip install -e .`, optional wheel); PyPI not required for v1.0; verify the entry point runs. (D-11)
- **Example testability (DOCS-01):** an execution test per example; canned stdin for the `ask` rung(s) and school.atena. (D-12)
- **Rung list / naming / theme:** planner finalizes exact rungs, file-naming convention, and any light theme, honoring roadmap order and ~8-9 count. (D-13)

## Deferred Ideas

- PyPI publishing — optional/later (repo-install satisfies v1.0).
- v2 language & tooling — elif, floats, string escaping, slicing, localized keywords, REPL, editor/LSP.
- Untyped-parameter limitation — brief honest mention if README covers functions deeply; full fix is v1.1.
