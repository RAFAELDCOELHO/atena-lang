# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-06-15
**Phases:** 7 (0–6) | **Plans:** 28 | **Tasks:** 32 | **Commits:** 182 over 3 days

### What Was Built
- A complete teaching transpiler: Atena source → runnable Python 3 via a single-pass Lexer → Parser → Analyzer → Generator pipeline (~3,500 LOC Python, stdlib only).
- A shared diagnostics spine (Phase 0) delivering the product's core promise — plain-English `Error on line N → source` messages, collected across a run, never a Python traceback — exercised by every later phase and verified end-to-end.
- A two-verb `atena run` / `atena build` CLI with runtime-error translation that names the learner's real Atena line, pip-installable with zero runtime dependencies.
- A 9-rung concept-ladder curriculum (`examples/`) + `school.atena` capstone and a full getting-started README that takes a non-programmer from install to first program.

### What Worked
- **Forced build order by pipeline contract.** Each phase was the literal input to the next (source → tokens → AST → analyzed AST → Python). The "100% green before advancing" gate prevented compounding bugs downstream.
- **TDD discipline (RED → GREEN) caught and contained real defects.** Multiple phases recorded failing-test-first commits; the discipline made the Phase 6 floor-division fix (CR-01) a clean, regression-proof change.
- **The analyzer-owns-every-decision contract.** Making the generator emit the analyzer's marks verbatim (1→0 index, `str()` coercion) kept codegen dumb and bug-light — no double-transforms.
- **Code review as a real gate, not a rubber stamp.** Two milestone-significant bugs were caught by review that per-phase verification missed (Phase 5 line-provenance, Phase 6 integers-only violation).

### What Was Inefficient
- **SUMMARY.md `requirements-completed` frontmatter was inconsistently populated** (many empty `[]`), so the milestone audit's auto-extraction of accomplishments produced noise ("One-liner:", "Fixed at:") that had to be hand-curated. The traceability table carried the real signal.
- **A core-contract bug ("integers only") survived all per-phase verification** because no phase's must-haves encoded it — it only surfaced when the curriculum examples demonstrated the float. Per-phase verification checks the phase's own must-haves, not cross-cutting language invariants.
- **Quick-task filename convention drift** (`{slug}-PLAN.md` vs bare `PLAN.md`) produced false "missing" flags at milestone close.

### Patterns Established
- **Plain-English errors, never a traceback** — enforced via `ErrorCollector` + AST line-stamping + `compile_for_run` so tracebacks name the real Atena line; helper frames (`_atena_index`/`_atena_concat`) skipped in provenance.
- **Integers-only is a codegen invariant**, not just a doc claim: `/` maps to `ast.FloorDiv()`.
- **Cross-cutting contracts deserve their own tests**, asserted at the example/curriculum level, not just per-phase must-haves.

### Key Lessons
1. **Encode cross-cutting language invariants as explicit, example-level tests.** Per-phase verification confirms a phase's own must-haves; it will not catch a global contract (like "no floats") that no single phase owns. The strengthened example tests now reject float output directly.
2. **Test the real pipeline, not a monkeypatched stand-in.** The Phase 5 line-provenance bug was masked by tests that patched `compile_for_run`; the Phase 6 example tests run the real installed CLI via subprocess and would have caught it.
3. **Keep tracking-file conventions uniform.** Bare `PLAN.md`/`SUMMARY.md` and consistently-filled frontmatter would have removed audit noise and false-positive flags at close.

### Cost Observations
- Model mix: orchestration on Opus; executors/verifier/reviewer on Sonnet.
- Sessions: milestone delivered across a small number of focused sessions over 3 calendar days.
- Notable: wave-based execution was effectively sequential here (`parallelization: false`), so the win came from fresh-context subagents per plan rather than concurrency.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 7 | 28 | Baseline: pipeline-contract build order, TDD gating, code-review-as-gate |

### Cumulative Quality

| Milestone | Tests | Runtime Deps | Source LOC |
|-----------|-------|--------------|------------|
| v1.0 | 298 passing | 0 | ~3,500 (Python, stdlib only) |

### Top Lessons (Verified Across Milestones)

1. Cross-cutting contracts need example-level tests — per-phase must-haves miss global invariants. *(v1.0)*
2. Test the real pipeline; monkeypatched stand-ins hide integration bugs. *(v1.0)*
