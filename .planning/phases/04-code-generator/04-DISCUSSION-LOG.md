# Phase 4: Code Generator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 4-Code Generator
**Areas discussed:** Codegen strategy (A vs B), Golden school.atena source

---

## Gray-area selection

| Area | Description | Selected |
|------|-------------|----------|
| Codegen strategy A vs B | ast.unparse() vs hand-rolled strings; drives output readability & golden control | ✓ |
| Golden school.atena source | Where the canonical golden program comes from + how exhaustive | ✓ |
| Output readability & helpers | Helper preamble always vs on-demand; blank lines / header | |
| Visible naming conventions | Keyword mangling scheme + nested-repeat loop-var naming | |

**Notes:** Construct mappings, the zero-error gate, verbatim emission, and the ast.parse() self-check were treated as already-locked by GEN-01..GEN-06 and not presented as gray areas.

---

## Codegen strategy (A vs B)

### Q1 — Which code-generation strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| ast.unparse() (A) — recommended | Map nodes → CPython ast, fix_missing_locations, unparse. Correct precedence/parens/indentation for free; output is unparse's canonical style. | |
| Hand-rolled strings (B) | Tree-walk emitting Python into a line buffer. Total control / byte-exact goldens / double quotes, at the cost of owning precedence + indentation. | |
| A as spine + readability patches | ast.unparse() for correctness, then a small post-pass for the teaching-readability gaps. | ✓ |

**User's choice:** A as spine + readability patches.
**Notes:** Framed around the project's worst bug class — "runnable Python that gives wrong answers" (precedence/parenthesization), which the ast.parse() self-check cannot catch. Strategy A removes that class structurally; the hybrid recovers readability without reintroducing it.

### Q2 — Which readability patches should the post-pass apply?

| Option | Description | Selected |
|--------|-------------|----------|
| Double-quoted strings | Restore "…" to match the learner's source (unparse defaults to single quotes). Fragile patch — flagged for planner. | ✓ |
| Blank lines between functions | Idiomatic spacing; trivial/safe. | ✓ |
| Header comment | `# Generated from school.atena by Atena` at top; pure addition. | ✓ |
| Accept unparse style (no patches) | Collapse back to pure strategy A. | |

**User's choice:** All three patches (double quotes + blank lines + header comment).
**Notes:** Shown Python is a teaching artifact via `--show` (CLI-06), so readability is a product feature. Double-quote patch flagged as the one needing careful (non-naive) handling.

### Continue-check

**User's choice:** Move to Golden school.atena (declined the optional helper-body-cleanliness sub-question; left as Claude's Discretion).

---

## Golden school.atena source

### Q1 — Where does the canonical school.atena come from?

| Option | Description | Selected |
|--------|-------------|----------|
| I author it — recommended | No spec exists; Claude designs a school/grades program, user reviews. | ✓ |
| I'll provide a spec/program | User supplies a reference program used verbatim as a locked canonical ref. | |
| Co-design it now | Sketch the program's shape together in discussion. | |

**User's choice:** Claude authors it.
**Notes:** Flagged that no `school.atena` (or any `.atena`) exists in the repo, despite GEN-06 naming it the headline acceptance test. Under strategy A the expected `.py` is a derived snapshot, so the real decision is the Atena program itself.

### Q2 — How exhaustive should school.atena be?

| Option | Description | Selected |
|--------|-------------|----------|
| Maximal capstone — recommended | Full construct set; doubles as Phase 6 curriculum flagship; backed by small targeted fixtures for edge cases. | ✓ |
| Focused smoke test | Small school.atena; every construct/edge case in single-purpose fixtures. | |

**User's choice:** Maximal capstone (+ targeted-fixture battery).

### Q3 — Should the capstone use `ask`, given v1.0's string-only ask + deterministic execution test?

| Option | Description | Selected |
|--------|-------------|----------|
| Ask for a name only — recommended | Asks one string (name) + greeting; grades as literal data so numeric logic works; canned stdin → deterministic. | ✓ |
| Non-interactive capstone | Zero input; ask→input coverage moves to a separate fixture. | |
| Ask for name + grades | Fuller flow, but v1.0 asked grades are strings — would demonstrate the limitation rather than hide it. | |

**User's choice:** Ask for a name only.
**Notes:** Surfaced the Phase-3 D-03 limitation (ask returns str, no number parsing) — asking for numeric grades would silently string-concat. Name-only keeps the capstone idiomatic and the execution test deterministic.

### Final readiness check

**User's choice:** Ready for context (left helper-emission policy, keyword mangling, and nested-repeat loop-var naming as Claude's Discretion with recommendations noted).

---

## Claude's Discretion

- **Runtime-helper emission policy** — recommendation: on-demand (only when referenced) for clean output.
- **Keyword-mangling scheme** — recommendation: trailing-underscore (`class`→`class_`) over `keyword.kwlist` minimum.
- **Nested-repeat loop-variable naming** — recommendation: collision-proof `_atena_`-prefixed unique var per nesting level.
- **Execution-test harness mechanics** — subprocess `input=` vs monkeypatch `input` + capsys; planner's call.

## Deferred Ideas

- "Always-preamble" helper emission and exhaustive builtin-shadowing mangling — candidate refinements, not v1.0 defaults.
- Number-parsing for `ask` (interactive numeric grades) — locked v1.0 limitation; a v2 item.
- (Cross-phase, not deferrals: examples/ ladder + README → Phase 6; runtime-error→Atena-line translation → Phase 5.)
</content>
