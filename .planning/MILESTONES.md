# Milestones

## v1.0 MVP (Shipped: 2026-06-15)

**Delivered:** A complete teaching transpiler — a non-programmer can install `atena`, write indentation-based, English-keyword programs (no colons/braces), run or build them to Python 3, and only ever see plain-English errors that name their line.

**Phases completed:** 7 phases, 28 plans, 32 tasks
**Stats:** 182 commits over 3 days (2026-06-13 → 2026-06-15) · ~3,500 LOC Python (stdlib only) + ~5,200 LOC tests · 298 tests green · zero runtime dependencies

**Key accomplishments:**

- **Diagnostics spine (Phase 0, DIAG-01..06):** shared `ErrorCollector` with the canonical `Error on line N: {msg} → {source}` format, errors collected/sorted/deduped/capped across a run, "Did you mean…?" suggestions, and a CLI fallback guaranteeing no Python traceback ever reaches the learner — the product's core value, established first and exercised by every later phase.
- **Lexer (Phase 1, LEX-01..08):** single-pass character scanner + off-side-rule indentation engine producing a balanced INDENT/DEDENT/NEWLINE stream; 19-keyword set, double-quoted strings, integers, and plain-English errors for mixed tabs/spaces, staircase dedents, and teaching off-ramps.
- **Parser (Phase 2, PARSE-01..06):** hand-rolled recursive-descent + Pratt expression parser with the full precedence ladder and indentation-delimited blocks, turning tokens into a complete `Program` AST with collect-all-errors recovery and Python-ism redirects.
- **Semantic analyzer (Phase 3, SEM-01..07):** in-place AST enrichment — `str()` coercion injection, 1→0 index rewrite, undefined-variable detection with teaching hints, and defined-before-called + exact-arity enforcement — emitted verbatim by the generator.
- **Code generator (Phase 4, GEN-01..06):** analyzed AST → runnable Python 3 via `ast.unparse()` + post-patches, emitting the analyzer's marks verbatim; golden `school.atena` → `school.expected.py` round-trips byte-for-byte and executes.
- **CLI runtime, packaging & curriculum (Phases 5–6, CLI-01..06, PKG-01, DOCS-01, DOCS-02):** two-verb `atena run`/`atena build` CLI with runtime-error translation that names the learner's real Atena line (never a traceback); pip-installable package; a 9-rung concept-ladder + `school.atena` capstone; and a full getting-started README.
- **Integers-only contract enforced end-to-end:** milestone code review caught `/` emitting floats (`10/3 → 3.333…`) on rung 3 of the curriculum; fixed under TDD by mapping `/` to floor division, with the golden snapshot and example/README assertions updated to lock integer output.

**Known deferred items at close:** 1 cosmetic tech-debt item (blank-line formatting after on-demand helpers in `build` output — output is valid and runnable). See `milestones/v1.0-MILESTONE-AUDIT.md`.

---
