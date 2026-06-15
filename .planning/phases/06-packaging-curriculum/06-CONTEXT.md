# Phase 6: Packaging & Curriculum - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 ships the already-complete transpiler as a **real, learnable product** — the final phase of the v1.0 milestone. Three deliverables:

1. **Packaging (PKG-01):** a working `pip install` (from the repo) that exposes the `atena` console entry point, built from `pyproject.toml` + `src/` layout with **zero runtime dependencies**.
2. **Concept-ladder (DOCS-01):** an `examples/` directory of `.atena` programs walking I/O → variables → conditionals → loops → functions → lists → dicts, each of which runs to completion via `atena run`, culminating in the golden `school.atena`.
3. **Getting-started README (DOCS-02):** a guide a complete non-programmer can follow from install to running their first program, covering installation, `atena run` / `atena build`, and the language basics.

**In scope:** packaging metadata polish + install verification; the full example ladder; the README rewrite.

**Not in scope (v2):** PyPI publishing (repo-install satisfies the criterion), localized keywords, REPL, editor/LSP, and all v2 language features (elif, floats, string escaping, slicing). No new language capabilities — Phase 6 is docs/examples/packaging only.

</domain>

<decisions>
## Implementation Decisions

### Concept-ladder shape (DOCS-01)
- **D-01 — Standalone rungs + capstone.** Each numbered example isolates exactly **ONE** concept with minimal noise; `school.atena` stays the **capstone** that combines everything. Not a cumulative story and not theme-less snippets — clean, referenceable rungs where the new idea is never buried under earlier ones.
- **D-02 — Finer climb (~8-9 rungs).** Keep the roadmap's concept order but give genuinely-distinct constructs their **own** rung: split `while` vs `repeat`, and `show` vs `ask`. Principle: **one new idea per file**.
- **D-03 — Teaching comments inside each file.** Each example opens with a short `#` header naming the concept and uses a few inline `#` notes narrating the key lines, so the file **teaches itself top-to-bottom** even before the learner opens the README. Friendly and clear — not heavy clutter.
- **D-04 — Include an interactive `ask` (input) rung.** The ladder teaches both `show` (output) and `ask` (input); it prepares the learner for `school.atena`, which uses `ask`. (Test-harness handling of interactive input → D-12.)

### README scope & voice (DOCS-02)
- **D-05 — Full getting-started guide** (not a bare quickstart). Section flow: brief "what & why" hook → install → the two verbs (`run` / `build` / `--show`) → a **"write your first program" walkthrough** → a **compact language-basics cheatsheet** (`show`, `ask`, `if`/`else`, `while`, `repeat`, `function`/`return`, lists with **1-indexing**, dicts with dot access, plus **automatic string coercion**) → pointer to `examples/`. A new user goes **install-to-first-program** from this one file (DOCS-02 success bar).
- **D-06 — Warm, beginner-first voice.** The same friendly, plain-English voice as Atena's errors (DIAG-04): assumes zero programming background, speaks directly to the learner ("you'll write…"), and explains any unavoidable jargon.
- **D-07 — A "when you make a mistake" error showcase.** A tiny deliberately-buggy program and the gentle, line-numbered Atena error it produces (**no Python stack trace**), so newcomers see the safety net up front. This is the product's core value made visible.
- **D-08 — Open with a brief "what & why" hook.** 2-3 sentences on what Atena is, who it's for, and that it transpiles to Python you can actually see (`build --show`), then straight to install — motivate before mechanics, no wall of text.

### Additional decisions (user-requested)
- **D-09 — README includes a "For teachers" section.** One paragraph on using the ~9-rung ladder as a **classroom curriculum** — one concept ≈ one ~50-minute class. This is the differentiator that turns Atena from a tool into a curriculum. *(User-specified; lands in DOCS-02.)*

### Claude's Discretion
The user did **not** select "Packaging polish & version" or "Example testability & input" for discussion. Resolve in research/planning with these sensible defaults:

- **D-10 — Packaging metadata polish (PKG-01).** `pyproject.toml` already wires the essentials (`atena = atena.cli:main`, `src/` layout, `requires-python >=3.11`, `dependencies = []`, hatchling). Flesh out metadata: `readme = "README.md"`, `license` pointer (a `LICENSE` already exists), `authors`, education-oriented classifiers (Development Status, `Intended Audience :: Education`, `Topic :: Education`, Python 3.11+), keywords, and project URLs if available. **Bump version `0.1.0` → `1.0.0`** to mark the v1.0 milestone (ties to a CLI `--version` if one landed in Phase 5). **Keep ZERO runtime dependencies.**
- **D-11 — Install story (PKG-01).** Document **repo-install** per the ROADMAP wording ("pip install from the repo"): `pip install .` for users, `pip install -e .` (editable) for contributors, optionally `python -m build` for a wheel. **PyPI publishing is NOT required for v1.0.** Verify the installed `atena` console entry point actually runs end-to-end (e.g. `atena run examples/…`).
- **D-12 — Example testability (DOCS-01 "each runs to completion").** Add an **execution test per example** so "runs to completion via `atena run`" is an enforced green test, consistent with the project's three-test-layers ethos. For the interactive `ask` rung(s) and `school.atena`, feed **canned stdin** via the established harness (subprocess `input=` / monkeypatched `input` + `capsys`, mirroring `tests/test_cli.py`). Examples live in `examples/` and are exercised by tests, not duplicated.
- **D-13 — Rung list, file naming, theme (you decide).** Planner finalizes the exact rung list, the numbered file-naming convention (e.g. `01-show.atena`, `02-ask.atena`, …), and any light shared theme. Honor the roadmap concept order, "one new idea per file," and the ~8-9 count. The **1-indexing** beat lands naturally in the lists rung and **string coercion** in the I/O / strings beat.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 6 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 6: Packaging & Curriculum" — the 3 success criteria (pip install exposes a working `atena` entry point from `pyproject.toml` + `src/` with zero deps; `examples/` concept-ladder runs to completion including golden `school.atena`; getting-started README takes a new user from install to first program), the PKG-01 / DOCS-01 / DOCS-02 mapping, and dependency on Phase 5.
- `.planning/REQUIREMENTS.md` §"Packaging" + §"Curriculum & Docs" — PKG-01, DOCS-01, DOCS-02 verbatim.

### Locked constraints & product identity
- `.planning/PROJECT.md` §"Core Value" + §Constraints + §"Key Decisions" — the **no-traceback / plain-English-errors** core value the README must showcase (D-07); **stdlib-only / zero runtime deps** (D-10); integers & double-quoted strings only; the "ship packaging + docs + curriculum, not just the transpiler" decision; the encouraging first-person error voice (DIAG-04) the README and example comments adopt (D-06).

### Language surface — keep the cheatsheet & examples exact (read-only)
- `.planning/REQUIREMENTS.md` §Lexer/§Parser/§Analyzer/§Generator (LEX/PARSE/SEM/GEN) — authoritative keyword set, 1-indexing rule, string-coercion rule, and construct→Python mappings to document accurately.
- `src/atena/tokens.py` — the canonical 19-keyword list (`show, ask, if, else, while, repeat, times, and, or, not, function, return, add, to, remove, from, length, true, false`) so the cheatsheet stays exact.

### Reusable assets to wire/verify (read, don't rebuild)
- `pyproject.toml` — already declares `[project.scripts] atena = "atena.cli:main"`, `src/` layout, `requires-python >=3.11`, `dependencies = []`, hatchling `packages = ["src/atena"]`. Phase 6 = metadata polish + version bump + install verification.
- `examples/school.atena` — the golden capstone the ladder builds toward; the run target for ROADMAP criterion #1; uses `ask` (interactive input).
- `src/atena/cli.py` — the `run` / `build` / `--show` verbs the README documents; CLI ergonomics (bare-verb default, `--version`) were left to the Phase 5 planner — **confirm what actually landed before documenting**.
- `tests/test_cli.py` + `tests/conftest.py` — established subprocess + monkeypatch / canned-stdin styles to mirror for per-example execution tests (D-12).
- `README.md` — currently a 1-line stub (`# atena-lang`) to replace with the full guide.
- `LICENSE` — exists; reference it from `pyproject.toml` metadata (D-10).

### Cross-phase context (locked)
- `.planning/phases/05-cli-runtime-pipeline-integration/05-CONTEXT.md` — `run` = exec-in-memory / `build` = write `.py` / `--show` reveals Python; runtime-error translation; and the CLI ergonomics (bare-verb default, `--version`) left to planner discretion — relevant because the README documents the CLI and `--version` ties to the packaging version bump (D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`pyproject.toml`** — entry point, `src/` layout, and zero-deps already wired; Phase 6 is metadata polish + version bump + install verification, **not** build-from-scratch.
- **`examples/school.atena`** — the golden capstone and the canonical `atena run` smoke target.
- **`src/atena/cli.py`** — the `run` / `build` / `--show` verbs the README walks through.
- **`tests/test_cli.py` + `tests/conftest.py`** — the canned-stdin / subprocess harness to mirror for example execution tests (handles the `ask` rungs).
- **`LICENSE`** — present; reference it from packaging metadata.

### Established Patterns
- **Stdlib-only, zero runtime dependencies** — packaging must preserve this.
- **100% green across three test layers** (golden, execution, error-path) — examples should be **execution-tested**, not just hand-run (D-12).
- **Encouraging, first-person, plain-English voice** (DIAG-04) — README and example comments adopt it (D-06).
- **TDD, commit per task, `feat/` branch** (e.g. `feat/packaging`), never `main`; phase 100% green before the milestone closes.

### Integration Points
- `pip install .` → `atena` console script (`atena.cli:main`) → runs `examples/*.atena`.
- `examples/*.atena` exercised by execution tests (canned stdin for `ask` rungs) — proves DOCS-01 "runs to completion."
- README documents the **actual** `cli.py` verbs/flags — confirm the `--version` / bare-verb behavior that landed in Phase 5 before writing it up.

</code_context>

<specifics>
## Specific Ideas

- **"For teachers" section (D-09):** one paragraph framing the ~9-rung ladder as a classroom syllabus — **one concept ≈ one ~50-minute class** — positioning Atena as a curriculum, not just a tool. The user called this out as the key differentiator.
- **Error showcase (D-07):** a tiny deliberately-buggy program + its gentle, line-numbered Atena error — e.g. an undefined variable (`I don't know what "xyz" is. Did you mean …?`) or the 1-indexing `[0]` mistake (`Lists in Atena start at 1, not 0.`). Concrete, beginner-relatable.
- **`school.atena` is the capstone** the whole ladder culminates in.
- **Version bump `0.1.0` → `1.0.0`** marks the v1.0 milestone close.

</specifics>

<deferred>
## Deferred Ideas

This is the **final v1.0 phase** — discussion stayed within scope; the user-requested "For teachers" section is DOCS-02 README content, not scope creep.

Out of scope, tracked for the future:
- **PyPI publishing** — repo-install satisfies PKG-01 for v1.0; publishing is optional/later.
- **v2 language & tooling** — `elif`, floats, string escaping, list slicing (LANG-V2-*), localized/translated keywords (TOOL-V2-01), REPL (TOOL-V2-02), editor/LSP (TOOL-V2-03).
- **Untyped-parameter limitation** (no compile-time coercion inside function bodies) — documented in STATE.md; planned v1.1 fix (typed parameters). Worth a brief honest mention in any "known limitations" note if the README covers functions deeply, otherwise leave to v1.1.

</deferred>

---

*Phase: 6-Packaging & Curriculum*
*Context gathered: 2026-06-15*
