# Phase 5: CLI Runtime & Pipeline Integration - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 wires the four already-built phases (**Lexer → Parser → Analyzer → Generator**) into a single `transpile()` driver in `src/atena/pipeline.py`, and finishes the two-verb CLI (`atena run` / `atena build`) in `src/atena/cli.py`, so a learner can **run** or **build** an Atena program. The cross-cutting promise — **no Python traceback ever reaches the learner** — must hold end-to-end, now extended to **runtime** errors during `atena run` (an out-of-range index, divide-by-zero, etc.), which are translated to plain-English Atena messages with the Atena line number. Covers requirements **CLI-01 … CLI-06** (CLI-05 is already complete).

**In scope:**
- The `transpile(source, filename) -> str | None` driver: instantiate one shared `ErrorCollector`, run the four phases in order, gate between phases on error count, and return the generated Python string (or `None` when errors were collected) (CLI-01, CLI-02, CLI-03).
- `atena run`: transpile then **execute** the generated Python; print expected program output (CLI-01).
- `atena build`: transpile and emit the generated Python 3 **without executing**; reveal the Python so learners connect Atena to real Python (CLI-02, CLI-06).
- On transpile failure: both verbs print collected Atena errors (never a traceback) and exit non-zero (CLI-03).
- Runtime-error translation during `run`: a Python exception from the learner's program → plain-English Atena message with the Atena line, never a traceback (CLI-04).
- Missing/unreadable `.atena` file → friendly plain-English message (CLI-05 — **already done** in `cli.py`; preserve it).

**Not in scope (Phase 6):**
- Packaging / pip-installable entry point (PKG-01) — though `pyproject.toml` already declares `[project.scripts] atena = "atena.cli:main"`.
- The `examples/` concept-ladder beyond `school.atena` (DOCS-01) and the getting-started README (DOCS-02).

**Out of scope (v2):** number-parsing for `ask`, float support, string escaping (locked elsewhere).

</domain>

<decisions>
## Implementation Decisions

### Run execution model
- **D-01 — `atena run` execs the generated Python in-process via `exec()`** (chosen over subprocess). Rationale: simplest, zero process overhead, and an in-process crash hands us the **live Python exception object** (its type + traceback) directly — which makes curated per-error messages (D-03) and Atena-line recovery (D-07) cleaner than parsing a subprocess's stderr traceback string. *Resolves the exec-vs-subprocess decision explicitly deferred from 04-CONTEXT.* Security risk is low per PITFALLS (the learner's own code, on their own machine; codegen builds Python from a typed AST and never string-interpolates user source, so there is no injection path).
- **D-02 — `atena run` is purely in-memory; it never writes a `.py` to disk.** `build` is the only verb that emits a file. Keeps the learner's folder clean and makes `run` feel like "just run my program."

### Runtime-error translation (CLI-04)
- **D-03 — Curated, gentle per-error messages + a gentle generic fallback.** Specific friendly messages for the common beginner runtime crashes — **out-of-range list index** (`IndexError`), **divide-by-zero** (`ZeroDivisionError`; `/` maps to `ast.Div()`), **missing dict key** (`KeyError` from `student.missing` → `student["missing"]`), **removing an item not in the list** (`ValueError` from `.remove`). Each names the Atena line and is framed about *the learner's program* (e.g. `Error on line 12: that list has 3 items, so there's no position 5.`). Anything uncurated falls back to a gentle generic runtime message — still no traceback, still line-numbered where possible.
- **D-04 — Split learner-program runtime errors from transpiler-internal errors.** The existing `_internal_error_message` ("Something went wrong inside Atena — this isn't your fault. Please share your program…") stays for **genuine internal bugs only**. A learner's own runtime error gets the friendly, line-numbered CLI-04 message instead. **This changes the current C-14 test** (`tests/test_cli.py`), which today asserts the *internal* wording for a divide-by-zero in learner code — the planner must rewrite C-14's expectation under TDD (RED first).
- **D-05 — Runtime errors use the same canonical format as compile-time errors:** `Error on line {N}: {plain English} → {offending Atena source line}`, **including the `→ source` line**. One consistent error language — the learner never perceives a "compile vs runtime" divide. Requires keeping the Atena source lines available at run time so the `→ source` line can be shown.
- **D-06 — Helper-raised errors must carry the Atena line too.** `_atena_index` currently raises `IndexError("List positions in Atena start at 1.")` with **no line number** (and `_atena_concat` similarly raises its own Atena-phrased message). The runtime catch layer (or the helpers themselves) must attach the Atena line so these match D-05's format, and must not double-wrap an already-Atena-phrased message into a generic one.

### Claude's Discretion
The user said "you decide" on these (and on the two un-discussed areas) — resolve in research/planning honoring the guidance below.

- **D-07 — Line-number precision mechanism ("you decide"):** *aim to pin the exact Atena line* for every runtime error, via whatever mapping is cleanest — e.g. setting the emitted AST node `lineno`s to the Atena source lines, maintaining a Python-lineno→Atena-lineno table, and/or injecting line-marker structure. Fall back to **best-effort** (omit the line, "while running your program") **only where exact mapping proves genuinely impractical**. Never risk pointing at the wrong line.
- **Cross-phase error gating (pre-decided by research, confirmed — not re-litigated):** run each phase to completion so it collects the maximum errors *for that phase* (collect-all **within** a phase), but **stop between phases when errors exist** — never feed a broken token stream / partial AST forward, and **never run codegen unless `errors.is_empty()`** (GEN-03). The driver decides flow *between* phases, not inside them (ARCHITECTURE.md).
- **`build` output behavior (CLI-02/CLI-06) — un-discussed, standard defaults:** keep the current `cli.py` behavior — write `file.py` next to the source and print `Built "file.py".`; expose a `--show` (and/or `build`-prints) path that reveals the generated Python for CLI-06. Decide overwrite/`-o` ergonomics with sensible defaults.
- **CLI ergonomics — un-discussed, standard defaults:** whether bare `atena file.atena` (no verb) defaults to `run`, a `--version` flag, and learner-facing help/usage wording — planner's call with sensible, beginner-friendly defaults. (No-subcommand currently prints help and exits 0 — acceptable baseline.)
- **exec mechanics:** the `compile()` target filename, the exec namespace (`{"__name__": "__main__"}` vs bare `{}`), interactive stdin for `ask`/`input()` (in-process exec reads the terminal naturally — desired), and the execution-test harness (canned stdin via subprocess `input=…` or monkeypatched `input` + `capsys`) — planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 5 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 5: CLI Runtime & Pipeline Integration" — the 5 success criteria (run executes & prints expected output; build emits Python without executing + `--show`; transpile failure → collected errors, no traceback, exit non-zero; runtime error → plain-English Atena message + Atena line; missing/unreadable file → friendly message), dependency on Phase 4, and the CLI-01…CLI-06 mapping.
- `.planning/REQUIREMENTS.md` §"CLI & Runtime" — CLI-01 … CLI-06 verbatim (CLI-05 already Complete).

### Architecture & pitfalls (authoritative for HOW)
- `.planning/research/ARCHITECTURE.md` — the **driver/pipeline shape** (`transpile(source, filename) -> str | None`, `pipeline.py` separate from `cli.py` so the whole transpiler is callable as a plain function in tests); the **between-phases gating flow** (run a phase to completion, then `if errors not empty: report all, STOP — never run codegen`); the **exec-vs-subprocess table** ("`exec` is simplest; subprocess isolates the learner's program… prefer subprocess only if you'd otherwise parse tracebacks" — **we chose exec, D-01**); **run = exec the string / build = write `.py` next to source**; the **no-traceback wrap** (any uncaught internal error → generic plain-English message).
- `.planning/research/PITFALLS.md` — **runtime-error mapping** ("wrap execution; map any leaked Python exception to a plain-English Atena error, ideally tied back to an Atena line via injected line markers/helpers" — informs D-05/D-06/D-07); the **`_atena_index` helper** contract (raises an *Atena* error, never a raw `IndexError`, for the 1-indexed contract); **merge all phases' errors and sort by `(line, column)`**, cap with "…and N more"; the **`exec()` security note** (generated Python comes from a typed AST — never `f"…{user_source}…"` — so no injection); the no-`NoneType`/`IndentationError`/`Traceback` jargon rule.
- `.planning/research/STACK.md` — the **`argparse` CLI** (two verbs `run`/`build`, auto `--help`, zero deps), `[project.scripts]` entry point, and the rule that `main()` must catch collected errors and print plain English — **no traceback may escape**; expected vs internal error handling.
- `.planning/research/SUMMARY.md` — milestone overview / flagged decisions framing.

### Locked constraints
- `.planning/PROJECT.md` §Constraints / §Key Decisions — **no traceback ever**; **collect-all-errors** (recovery, not fail-fast); `atena run` **executes**, `atena build` **emits `.py`**; TDD (failing test first), commit per task, **feature branch** (`feat/cli` / `feat/runtime`, never `main`), one phase **100% green** before advancing; integers / double-quoted strings only.

### Data contracts the driver wires (read-only — call, don't modify)
- `src/atena/lexer.py` — `Lexer(source, errors).tokenize() -> list[Token]`.
- `src/atena/parser.py` — `Parser(tokens, errors).parse() -> Program`.
- `src/atena/analyzer.py` — `SemanticAnalyzer(program, errors).analyze() -> Program`.
- `src/atena/codegen.py` — `CodeGenerator(program).generate() -> str` (no `errors` param — runs **only** when `errors.is_empty()`). Helper bodies live here: `_atena_index(i)` raises `IndexError("List positions in Atena start at 1.")` (**no line yet** — see D-06); `_atena_concat(a, b)` raises its own Atena-phrased message.
- `src/atena/errors.py` — `ErrorCollector.add(line, message, source_line)` / `.is_empty()` / `.report()`. The gate the driver checks before codegen; runtime errors should route through the **same** format (D-05).
- `src/atena/ast_nodes.py` — the 22 `@dataclass` nodes carry line numbers — the basis for the Python→Atena line mapping (D-07).

### The pieces Phase 5 finishes (not read-only)
- `src/atena/pipeline.py` — currently a **stub** raising `NotImplementedError`; Phase 5 implements the four-phase wiring + between-phase gating here.
- `src/atena/cli.py` — the **existing CLI scaffold** to finish: argparse `run`/`build`, `_read_file`, `_file_error_message` (CLI-05 ✓), `_internal_error_message` (keep for internal bugs only — D-04), the `exec()` run path (keep — D-01), and the build-write path. Refine the exec-error branch to do CLI-04 translation instead of routing learner errors through the internal message.
- `tests/test_cli.py` — existing **C-1…C-14** (subprocess + monkeypatch styles to mirror). **C-14 must be rewritten** (D-04). Add tests for CLI-01 (run prints output), CLI-02/CLI-06 (build emits/show), CLI-03 (transpile errors), CLI-04 (each curated runtime error → line-numbered plain-English message, no traceback).
- `examples/school.atena` — the golden run target: `atena run examples/school.atena` must transpile, execute, and print the expected output (ROADMAP criterion #1).

### Cross-phase context (locked)
- `.planning/phases/04-code-generator/04-CONTEXT.md` — **exec-vs-subprocess was explicitly deferred to Phase 5** (now D-01); helper **names/bodies** (`_atena_index`/`_atena_concat`) and the `# Generated from school.atena by Atena` header; the execution-test harness (canned stdin) approach; `ask` is **string-only**.
- `.planning/phases/03-semantic-analyzer/03-CONTEXT.md` — the unified `_atena_index` **i<1 message** (D-06) and the `_atena_` prefix convention.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/atena/cli.py`** — most of the CLI already exists: argparse with `run`/`build` subparsers, robust file-read + plain-English file errors (CLI-05 done, C-3/C-4/C-11/C-12/C-13 green), the `_internal_error_message` fallback, the `exec()` run path, and the build `.py`-write path. Phase 5 fills `transpile()` and refines the exec-error branch.
- **`src/atena/errors.py`** — `ErrorCollector` is the single shared collector + the canonical `report()` formatter; reuse it for runtime errors too (D-05).
- **The four phase modules** — clean, uniform constructors (`(input, errors)` → method), so the driver is a short, mechanical sequence.
- **`tests/test_cli.py` + `tests/conftest.py`** — established subprocess (`python -m atena …`) and monkeypatch styles to mirror for the new CLI-01…CLI-04 tests; `examples/school.atena` is the end-to-end fixture.
- **Python stdlib only** — `exec`/`compile` for run, `argparse` for the CLI, `traceback`/`sys.exc_info` for line recovery. Zero runtime dependencies preserved.

### Established Patterns
- **`ErrorCollector` is injected, never global**; the driver owns the one instance and threads it through all phases.
- **Errors to stderr, exit non-zero; program output to stdout** (per existing cli.py + DIAG format).
- **TDD per PROJECT.md** — failing test first, commit per task, `feat/` branch (never `main`); phase 100% green before advancing.

### Integration Points
- **`cli.main()` → `pipeline.transpile()` → four phases → `result` string** → `run` execs it (in-memory, D-02) / `build` writes `file.py`.
- **Runtime catch layer** wraps the `exec()` call: maps the caught exception (type + traceback) → curated/generic Atena message + Atena line (D-03…D-07), distinct from the internal-bug path (D-04).
- **`pyproject.toml`** already declares the `atena` console script → `atena.cli:main` (packaging *install* is Phase 6, but the entry wiring exists today).

</code_context>

<specifics>
## Specific Ideas

- **C-14 rewrite is a known, concrete task:** `tests/test_cli.py::test_c14_exec_runtime_error_no_traceback` currently asserts `"Something went wrong inside Atena"` for a learner divide-by-zero. Under D-04 it must instead expect the friendly, line-numbered runtime message (and still assert no `"Traceback"` / no raw exception class name). Do RED first.
- **Curated runtime-error catalog (seed):** `IndexError` (out-of-range index), `ZeroDivisionError` (÷0), `KeyError` (missing dict key), `ValueError` (remove-not-found). `_atena_index` already owns the i<1 "List positions in Atena start at 1." message — extend it to carry the line (D-06).
- **Criterion-#1 smoke:** `atena run examples/school.atena` must print the expected output — the canonical end-to-end check.
- **Error wording tone:** gentle, specific, actionable, about *the learner's program* — e.g. "that list has 3 items, so there's no position 5" — never "NoneType"/"IndexError"/"Traceback", and never the "not your fault, share your program" wording (that's for internal bugs only).

</specifics>

<deferred>
## Deferred Ideas

- **`build` output behavior** (write `.py` vs print-to-stdout, `--show` semantics, overwrite/`-o`) and **CLI ergonomics** (bare `atena file.atena` default verb, `--version`, learner-facing help wording) — **in Phase 5 scope but not deep-dived**; left to research/planning with sensible defaults (captured under Claude's Discretion above). Not a deferral to a later phase.
- **Packaging / pip entry point (PKG-01), the `examples/` concept-ladder beyond `school.atena` (DOCS-01), and the getting-started README (DOCS-02)** — **Phase 6**.
- **Number-parsing for `ask`** (interactive numeric input) and **float support** — **v2** (locked in Phase 3 / PROJECT Out of Scope).

Discussion stayed within phase scope — no scope creep to redirect.

</deferred>

---

*Phase: 5-CLI Runtime & Pipeline Integration*
*Context gathered: 2026-06-14*
</content>
</invoke>
