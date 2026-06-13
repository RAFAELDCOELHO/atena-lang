# Project Research Summary

**Project:** Atena Language
**Domain:** Teaching-oriented source-to-source transpiler (Atena → Python 3), single-pass 4-phase pipeline for complete non-programmers
**Researched:** 2026-06-13
**Confidence:** HIGH

## Executive Summary

Atena is a textbook compiler front-end with a trivial back-end: a single-pass Lexer → Parser → Semantic Analyzer → Code Generator pipeline that turns an indentation-delimited, plain-English teaching language into runnable Python 3. The architecture is *fixed* by the spec; the research question was never "what to build" but "how to build each phase well, what the inter-phase contracts are, and where the bugs hide." The answer from all four research streams converges hard: lean entirely on the Python standard library (`dataclasses` for the AST, `ast` + `ast.unparse()` for codegen, `argparse` for the CLI), hand-roll the lexer and recursive-descent/Pratt parser (no parser generator), and treat the *error experience* — not the transpiler's correctness — as the actual product.

The single most important architectural insight, surfaced independently by the Architecture, Features, and Pitfalls research, is that **the product's core value lives in a cross-cutting diagnostics spine, not in any one phase.** A shared `ErrorCollector` and the `Error on line {N}: ... → {source}` format must be established as a Phase 0 *before* the lexer, because every phase plugs into it and the "never a Python stack trace, collect all errors" promise is the thing that makes Atena a teaching tool rather than just a working compiler. Two more threads run end-to-end alongside it: source-position threading (line + raw source-line text stamped on every token from the lexer onward, since every human-error feature depends on it) and a clean Analyzer→Generator contract where the Analyzer *decides* every semantic transformation and the Generator emits *verbatim*.

The key risks are concentrated and well-understood. The worst class of bug produces *runnable Python that gives wrong answers*: the 1-indexed variable-subscript shift (`items[i]` where `i` is `0` or negative must error at runtime, not silently wrap to Python's last-element negative-index semantics) and double-shifting when the index-rewrite ownership boundary is fuzzy. Both are mitigated by the same discipline — the Analyzer owns the 1→0 rewrite exactly once (idempotent, tagged), dynamic indices route through a generated runtime helper (`_atena_index`) that raises an Atena error, and the Generator never touches index math. The second risk cluster is the off-side-rule lexer (unmatched dedents, EOF not draining open blocks, blank/comment lines corrupting the indent stack) — handled by copying CPython's exact indentation-stack algorithm. Mitigation for all of it is the same testing discipline: testing is a *per-phase gate* (golden + execution + error-path, with an `ast.parse()` self-check on every generated program), never a final phase.

## Key Findings

### Recommended Stack

Standard library only for the transpiler core, with exactly two dev-time dependencies. The transpiler ships with **zero runtime dependencies**, which eliminates the entire class of version-conflict problems for the learners installing it. Two facts drive the whole stack: `ast.unparse()` has been in the stdlib since Python 3.9 (obsoleting the abandoned `astor`), and INDENT/DEDENT is an inherently stateful pre-pass that no parser generator handles cleanly — even Lark's hand-managed `Indenter` has documented bugs exactly where Atena lives (comments inside indentation-sensitive regions). See [STACK.md](./STACK.md).

**Core technologies:**
- **Python 3.11+** (floor; tested 3.11–3.14): mature `match` for token/node dispatch, comfortable EOL runway (Oct 2027); the emitted code is conservative Python 3 that runs on an even wider range.
- **`dataclasses` (stdlib)**: AST nodes — mutable (the analyzer rewrites in place), typed, free `__repr__`/`__eq__` (makes parser tests trivial), carry `line`/`col` directly. Chosen over `NamedTuple` precisely because the analyzer mutates nodes.
- **`ast` + `ast.unparse()` (stdlib)**: codegen strategy A — build a Python AST, `fix_missing_locations()`, `unparse()`. Correct precedence/parenthesization/indentation for free. (Strategy B, string emission, is a legitimate fallback — see Flagged Decisions.)
- **`argparse` (stdlib)**: two-verb CLI (`run`/`build`); Click/Typer would be over-engineering and a runtime dependency.
- **`pytest` 9.1.0 + `hatchling` 1.30.1 (dev only)**: de-facto test framework (plain `assert`, `parametrize`, fixtures) and modern zero-config PEP 517 build backend. `src/atena/` layout, `[project.scripts]` console entry point (`atena = "atena.cli:main"`).
- **Hand-rolled lexer + recursive-descent/Pratt parser** (NOT lark/ply/sly/ANTLR): error recovery and friendly line-numbered messages fight generated parsers; the grammar is tiny and LL(1); the readable hand-written parser is itself a teaching artifact.

### Expected Features

Atena's *language* feature set is fixed by PROJECT.md. The feature research is entirely about the **product wrapper** that makes the locked language a good teaching tool: error quality, error recovery, CLI ergonomics, curriculum. Anti-features map 1:1 to the PROJECT.md Out-of-Scope list. See [FEATURES.md](./FEATURES.md).

**Must have (table stakes — the teaching value collapses without these):**
- **No raw Python stack trace ever reaches the learner** — compile-time *and* runtime errors translated to Atena terms with the Atena line.
- **`Error on line N: <plain explanation> → <source line>` format, exactly** — plain English, zero compiler jargon ("token", "AST", "DEDENT", "arity", "NoneType" must never appear).
- **Collect all errors in one run (error recovery), not fail-fast** — the hardest table-stake; needs the diagnostics spine + parser synchronization.
- **Named undefined-variable + human-terms arity errors + the deliberate 1-indexed `[0]` teaching error** ("Lists in Atena start at 1, not 0").
- **`atena run` / `atena build`** with friendly file-not-found handling; **pip-installable `atena` entry point**; **`examples/` concept ladder + getting-started README**.

**Should have (differentiators — fold in early, most are near-free):**
- **First-person, encouraging compiler voice** (Elm-style, one warm sentence — not paternalistic paragraphs). Pure wording, zero engineering cost.
- **"Did you mean…?" suggestions** via stdlib `difflib.get_close_matches` over the symbol table and fixed keyword list. Catches the #1 beginner mistake for near-zero cost.
- **Cascading-error dedup + a sensible error cap** ("…and N more").
- **`atena build` reveals the generated Python** (including the injected `str()` coercion) — the "my `repeat 3 times` became a `for` loop" teaching moment. Codegen readability is therefore a *feature*, not just correctness.

**Defer (v2+):**
- Localized/translated keywords & messages (Hedy-style) — large surface area; validate the English product first.
- Floats, then maybe `elif`/slicing — each is an Out-of-Scope decision with a stated rationale; revisit only on proven learner demand.
- REPL / IDE-LSP integration — REPL structurally conflicts with the DEDENT-delimited block model.

### Architecture Approach

A four-phase pipeline driven by a thin CLI over a `transpile(source, filename) -> str | None` function, with one module per phase mirroring the four-phase contract exactly (`lexer.py`, `parser.py`, `analyzer.py`, `codegen.py`), plus pure-data contract modules (`tokens.py`, `ast_nodes.py`) and the all-important `errors.py` as the single source of truth for the message format. The inter-phase contracts are: tokens (flat list, INDENT/DEDENT balanced, every token carries line + source-line text) → AST (position-bearing dataclass nodes, possibly partial) → analyzed AST (same tree, mutated in place) → Python source string. Codegen is a **hard gate**: it runs *only* when the `ErrorCollector` is empty. See [ARCHITECTURE.md](./ARCHITECTURE.md).

**Major components:**
1. **ErrorCollector (cross-cutting spine)** — shared instance injected into every phase; phases only ever `add(line, message, source_line)`, never raise or print to the user. The driver inspects it *between* phases to decide flow. This is the product's core value in code form.
2. **Lexer** — char scanner owning the indentation stack (CPython algorithm); emits INDENT/DEDENT/NEWLINE, skips blank/comment-only lines, enforces tabs-OR-spaces, stamps every token with line/col/source-line text. Highest-risk phase.
3. **Parser** — recursive descent for statements, Pratt/precedence-climbing for expressions (the precedence table is living documentation of the spec ladder); error recovery synchronizes on NEWLINE/DEDENT (a natural, reliable sync token that brace/semicolon languages lack).
4. **Semantic Analyzer** — single forward pass over the AST: flat global symbol table, lightweight "abstract-interpretation-lite" type inference (tiny lattice: number/str/bool/list/dict/unknown), `str()` coercion injection, the 1→0 index rewrite, no-hoisting defined-before-called + arity checks. **Decides everything; mutates in place.**
5. **Code Generator** — dumb, faithful tree-walk that reads the analyzed tree and emits Python verbatim. Touches `ast` only here; never re-derives coercion or index math.

### Critical Pitfalls

The pitfalls are ordered by cost-once-shipped. The worst produce runnable-but-wrong Python (the learner runs code that lies). See [PITFALLS.md](./PITFALLS.md) for all 21.

1. **Variable index shift breaks "negatives-are-errors" (Pitfall 5)** — `items[i]` emitted as bare `items[i - 1]` means `i == 0` silently returns Python's *last* element and negative `i` silently does from-the-end indexing, both of which Atena must reject. **Avoid:** generate a runtime helper `_atena_index(seq, i)` that raises an Atena error on `i < 1`; route every variable subscript (read + write) through it; literal `0`/negatives still rejected at analysis time.
2. **Double-shifting the index (Pitfall 6)** — fuzzy ownership of the 1→0 rewrite lets two passes both subtract 1 (`items[2]` → `items[0]`). **Avoid:** the Analyzer owns the rewrite as a single idempotent step, tags converted nodes, and the Generator emits indices verbatim. Test nested `grid[2][3]` → `grid[1][2]`.
3. **Off-side-rule lexer bugs (Pitfalls 1–4)** — unmatched dedents silently accepted, EOF not draining open blocks, blank/comment lines corrupting the indent stack, mixed tabs/spaces measured inconsistently. **Avoid:** copy CPython's exact indentation-stack algorithm — push `0`; after popping on dedent the new top *must equal* current indentation (else error); drain the stack at EOF; skip blank/comment-only lines *before* measuring; record the indent char on the first indented line and reject the other thereafter.
4. **Coercion wraps the wrong operand / can't decide statically / breaks on chains (Pitfalls 10–11)** — `"a" + 1 + 2` must yield `"a12"`, `1 + "x"` must wrap the `1`, `x + 1` (both numbers) must stay untouched, and disallowed pairs must produce a plain-English error not a runtime `TypeError`. **Avoid:** give every expression node an inferred result type, evaluate coercion **bottom-up** so result types propagate up chains, make the coercion function *total* (no silent fall-through), and route UNKNOWN-typed operands through a runtime concat helper so they never crash.
5. **Invalid generated Python reaches the learner (Pitfalls 15–18)** — bad indentation, a missing trailing colon (`else:`!), reused `_i` in nested `repeat`, or an Atena identifier that's a Python keyword (`class`, `import`) all surface a Python stack trace — the one thing the product promises never happens. **Avoid:** paired enter/exit indent tracking + centralized block-header emission, unique generated loop variables, keyword mangling via `keyword.kwlist`, and an **`ast.parse()` self-check on every generated program** (a failure is an internal bug caught in tests, never shown to the user).

## Implications for Roadmap

Based on combined research, the suggested phase structure follows the pipeline build order — each phase is the input contract for the next, and PROJECT.md mandates "one phase at a time, 100% green before advancing." The non-obvious recommendation, made independently by three of the four researchers, is that **the diagnostics spine is a real Phase 0, not lexer setup.**

### Phase 0: Diagnostics Spine + Data Contracts + CLI Skeleton
**Rationale:** Everything depends on `ErrorCollector`, the `Token`/AST data, and the `Error on line {N}: ... → {source}` format. Establishing the spine first prevents each phase from inventing its own error style and bakes source-position threading into the data model from day one (it's far cheaper than retrofitting it into every phase later). This is the product's core value in code form.
**Delivers:** `errors.py` (the single source of truth for the message format, with line-sort + cap), `tokens.py` and `ast_nodes.py` (pure-data contracts, dependency-free so every test can import them), and a stubbed `atena run`/`atena build` CLI + `pipeline.py` skeleton wired to the collector.
**Addresses:** the `Error on line N` format, no-stack-traces promise, pip-installable entry point (skeleton).
**Avoids:** Pitfall 14 (error ordering/cap) by centralizing formatting; pre-empts the whole "leaked Python traceback" class by establishing the collect-don't-raise discipline.

### Phase 1: Lexer
**Rationale:** Produces contract A (tokens); nothing else is testable without real tokens. It is the **highest-risk phase** — INDENT/DEDENT, blank/comment skipping, and tab/space policy are the classic "works on my file, breaks on yours" bugs.
**Delivers:** source string → balanced token list with INDENT/DEDENT/NEWLINE, blank/comment lines skipped, `=`/`==` distinguished by maximal-munch, every token stamped with line/col/source-line text, tab/space-mix errors collected.
**Uses:** the CPython indentation-stack algorithm (STACK.md / ARCHITECTURE.md Pattern 1).
**Avoids:** Pitfalls 1–4 (unmatched dedent, EOF drain, blank/comment spurious tokens, mixed tabs/spaces).

### Phase 2: Parser
**Rationale:** Consumes contract A, produces contract B (AST); cannot exist before tokens. Error recovery (synchronization) is a sub-feature with its own test surface that's easy to defer and regret.
**Delivers:** recursive-descent statement parsing + Pratt expression parsing honoring the full precedence/associativity ladder; blocks consume INDENT…DEDENT; multiple syntax errors collected via synchronization on NEWLINE/DEDENT.
**Implements:** ARCHITECTURE Patterns 5–9 (recursive descent + Pratt, block parsing, panic-mode recovery, postfix chaining).
**Avoids:** Pitfalls 7–9 (unary vs binary minus, precedence/associativity, postfix chaining), 12–13 (cascading errors, infinite-loop-on-error via a progress invariant + loop guard).

### Phase 3: Semantic Analyzer
**Rationale:** Consumes contract B, produces contract C (analyzed AST); needs a complete AST to walk. This phase **owns every semantic decision** — the Analyzer→Generator contract means it decides and the Generator emits verbatim. Splitting these risks double-shift and double-coercion.
**Delivers:** flat symbol table, lightweight type inference, bottom-up `str()` coercion injection, the single idempotent 1→0 index rewrite (with helper-routing decision for dynamic indices), no-hoisting defined-before-called + arity checks, poisoned-symbol suppression for clean error counts.
**Implements:** ARCHITECTURE Patterns 10–12.
**Avoids:** Pitfalls 5–6 (index shift/double-shift — decides the helper), 10–12 (coercion correctness + cascade suppression), 18–21 (keyword mangling assignment, dict dot normalization, call-before-def, arity, top-level `return`).

### Phase 4: Code Generator
**Rationale:** Consumes contract C, produces contract D (Python); last because it relies on a *fully analyzed* tree and runs only when the collector is empty (hard gate). Low-risk but its acceptance test is the golden example, and its output readability is a teaching feature.
**Delivers:** faithful tree-walk emitting valid, *readable* Python 3 — verbatim indices/coercions from the analyzed tree, the `_atena_index` helper, unique `repeat` loop variables, mangled keyword identifiers, trailing colons, and an `ast.parse()` self-check on every output.
**Uses:** `ast` + `ast.unparse()` (strategy A) — see Flagged Decisions for the strategy-B alternative.
**Avoids:** Pitfalls 15–17 (invalid indentation, missing colons, `_i` collision); the runtime-error mapping for `atena run` (see Flagged Decisions).

### Phase 5: Pipeline Integration + Packaging + Curriculum
**Rationale:** Ties the four phases under the driver, then ships the packaging/docs/examples that deliver the *product* (a correct compiler nobody can install or learn from delivers zero value).
**Delivers:** end-to-end golden fixture (`school.atena` → `school.expected.py`) passing AND executing; `pip install` entry point working; friendly file-not-found handling; runtime-error translation for `atena run`; the `examples/` concept ladder + getting-started README; optionally the early differentiators (encouraging voice, "Did you mean…?", `--show` flag).
**Addresses:** the full table-stakes CLI + teaching deliverables.
**Avoids:** Pitfall 6 (runtime traceback escaping `atena run`) by wrapping execution and mapping leaked Python exceptions back to Atena lines.

### Phase Ordering Rationale

- **Build order is forced by the pipeline contracts** — each phase is the literal input to the next, so the only valid order is data-spine → lexer → parser → analyzer → codegen → integration. PROJECT.md's "one phase at a time, 100% green" gate maps onto this directly.
- **Phase 0 exists because the diagnostics spine and source-position threading are cross-cutting**, not lexer-local. Folding them into the lexer is the tempting mistake; doing so means every later phase improvises its own error style and you retrofit positions everywhere.
- **The Analyzer/Generator split is a contract, not just a phase boundary** — keeping all semantic decisions (1→0 rewrite, coercion, arity) in the Analyzer and making the Generator a verbatim emitter is what prevents the two worst bugs (double-shift, double-coercion). The roadmap should treat "Generator must not re-transform" as an explicit acceptance criterion of Phase 4.
- **Testing is woven into every phase, not appended as a final phase.** Each phase is "green" only with three test layers: golden snapshots (kept minimal/non-brittle), **execution tests** that run the generated Python and assert output (catch index/coercion/codegen-semantics bugs text snapshots miss), and **error-path tests** that assert exact plain-English errors, their count, and their line order. The `ast.parse()` self-check rides on every codegen test.

### Research Flags

Phases likely needing deeper research during planning (`/gsd:plan-phase --research-phase <N>`):
- **Phase 1 (Lexer):** the highest-risk phase. INDENT/DEDENT + EOF drain + blank/comment skipping + tab-space policy have many subtle edge cases; worth deeper test-case enumeration even though the algorithm itself is well-documented.
- **Phase 3 (Analyzer):** the densest correctness surface — the index-helper decision (where exactly the runtime `_atena_index` boundary falls), bottom-up coercion with the UNKNOWN/runtime-helper policy, and cascade suppression each warrant careful design before coding.

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 0:** straightforward dataclasses + a formatter + an argparse skeleton.
- **Phase 2 (Parser):** recursive descent + Pratt and panic-mode synchronization are canonical, well-sourced techniques.
- **Phase 4 (Generator):** a faithful tree-walk with an `ast.parse()` self-check; low-risk once the analyzer is trusted.
- **Phase 5:** PEP 621 packaging + content work; established patterns.

### Flagged Decision Points (resolve during planning)

Two decisions were deliberately left open by the research because either choice is defensible:

1. **Codegen strategy: `ast.unparse()` (A) vs. string emission (B).** Strategy A gives correct precedence/parenthesization/indentation for free and is the recommended default for correctness. Strategy B (emit Python source as strings) is more transparent as a teaching artifact — the generated Python reads like obvious, line-by-line output a student can trace — at the cost of hand-managing indentation/precedence. Atena's tiny grammar makes B tractable. **Decide in Phase 4 planning.** Either way: do not add `astor`, and run the `ast.parse()` self-check regardless.
2. **Runtime-error-to-line mapping for `atena run`.** The `no-stack-trace` promise extends to *runtime* errors from the executed Python (`KeyError`, the index helper, etc.). Open question: how the runtime error maps back to the original Atena line — inject line markers/helpers, use `exec` vs a subprocess for cleaner interception, etc. The Architecture research notes a subprocess isolates the learner's program and makes runtime errors easier to intercept and re-phrase. **Decide in Phase 4/5 planning.**

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified against PyPI/devguide; `ast.unparse()` round-trip verified locally; hand-roll-vs-generator reasoning tied directly to Atena's constraints. Zero runtime deps removes version-conflict risk entirely. |
| Features | HIGH (MEDIUM on curriculum sequencing) | Error-message and CLI patterns grounded in Elm, Rust, Python 3.10+, Hedy, Scratch, and peer-reviewed novice-error research. Only the exact curriculum/example ladder ordering is convention rather than standard. |
| Architecture | HIGH (MEDIUM-HIGH on coercion inference) | Every pattern maps to a verified classic (CPython tokenizer algorithm, recursive-descent + Pratt, panic-mode recovery, visitor walk). The one judgment call is the permissive-UNKNOWN default in coercion inference — a deliberate product-friendliness choice, not a verified fact. |
| Pitfalls | HIGH | Core compiler-construction failure modes are well-documented; CPython INDENT/DEDENT, unary-vs-binary minus (Pratt nud/led), and Python negative-index semantics verified against official docs. |

**Overall confidence:** HIGH

### Gaps to Address

- **Index-helper boundary (where dynamic vs literal subscripts split):** the Analyzer must decide which subscripts are statically checkable (literal → fold/reject at analysis time) vs which route through the runtime `_atena_index` helper. Resolve in Phase 3 planning with explicit `i=0`/negative/nested test cases written first.
- **Coercion policy for UNKNOWN-typed operands:** the spec wants silent coercion to *never crash*, which argues for a runtime concat helper for un-inferable operands rather than a static reject. Confirm this policy in Phase 3 planning and document the "under-coerce rather than over-reject" stance.
- **Runtime-error-to-line mapping for `atena run`** (flagged decision #2): needs a concrete design — `exec` vs subprocess, line-marker injection — before Phase 4/5 is "done."
- **Codegen strategy A vs B** (flagged decision #1): pick during Phase 4 planning based on whether maximal correctness or maximal teaching-transparency of the emitted Python wins.
- **Curriculum/example sequencing** is convention, not standard (MEDIUM confidence) — validate the concept ladder against real beginner feedback post-launch; the golden `school.atena` doubles as the capstone example.

## Sources

### Primary (HIGH confidence)
- Python Language Reference — Lexical Analysis (INDENT/DEDENT stack algorithm, blank/comment-line handling, EOF DEDENT generation, tab/space rules): https://docs.python.org/3/reference/lexical_analysis.html
- Python `ast` docs (`lineno`/`col_offset`, `fix_missing_locations`, `unparse`): https://docs.python.org/3/library/ast.html — plus local stdlib verification of `ast.unparse()` round-tripping a built AST.
- devguide.python.org/versions + endoflife.date — Python version support/EOL (3.11 recommended floor, 3.14.6 latest).
- PyPI JSON API — verified current versions: pytest 9.1.0, hatchling 1.30.1, setuptools 82.0.1, lark 1.3.1, astor 0.8.1 (abandoned, last upload 2019-12-10).
- "Pratt Parsers: Expression Parsing Made Easy" (Bob Nystrom) + Eli Bendersky's top-down operator precedence — nud/led split for unary/binary minus, precedence/associativity via binding power.
- Panic-mode / synchronization error recovery (Dragon Book lineage) — restart on statement-boundary tokens.
- Novice error-message research (CHI 2021 "Readability and its Constituent Factors"; Becker et al.) — show-the-code, plain-English, anti-jargon findings.

### Secondary (MEDIUM confidence)
- Elm "Compilers as Assistants" + Elm error-message critiques — first-person warm voice, and the verbosity/paternalism caution.
- Rust diagnostics (RFC 1644, rustc-dev-guide) — primary/secondary labels, suggestion applicability.
- Python 3.10–3.12 "Better Error Messages" + Hedy design/localization papers + Scratch block-based prevention — competitor error-UX landscape.
- clig.dev + jmmv.dev — CLI error-reporting, friendly file-not-found phrasing, subcommand design.
- Go by Example / Tour of Go / Dlang Tour — "by example" annotated-runnable curriculum model.
- Lark `indenter.py` + indented-tree docs — confirms parser-generator INDENT/DEDENT still needs hand-written postlex logic with comment-interaction bugs.
- "A Deep Dive into Python's Tokenizer" (Benjamin Woodruff) — CPython moving indentation into the tokenizer.

### Tertiary (LOW confidence)
- Exact curriculum/example sequencing — convention, not standard; validate with real beginner feedback post-launch.

---
*Research completed: 2026-06-13*
*Ready for roadmap: yes*
