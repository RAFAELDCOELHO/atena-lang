# Phase 4: Code Generator - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 takes the **fully-analyzed `Program` AST (contract C)** and translates it into **valid, runnable, readable Python 3 source (contract D)** — the final transform phase of the pipeline. It is a tree-walk that **emits VERBATIM** from the analyzed tree (it never re-derives indices or coercion — ARCHITECTURE anti-pattern 4), runs **only when `ErrorCollector.is_empty()`** (the hard gate, GEN-03), and **self-checks every output with `ast.parse()`** (GEN-05). Covers requirements **GEN-01 … GEN-06**.

Concretely it delivers a `CodeGenerator` (`src/atena/codegen.py`) that maps each analyzed Atena node to a Python construct and produces a Python source string, plus the canonical golden fixture and a targeted-fixture battery.

**In scope:**
- Construct mapping: `show`→`print`, `ask`→`input`, `repeat N times`→`for <loopvar> in range(N)`, `while`, `if`/`else` (with colons), `true`/`false`→`True`/`False`, `and`/`or`/`not`, arithmetic/comparison/boolean expressions (GEN-01).
- List/dict ops: `add`→`.append`, `remove`→`.remove`, `length`→`len`, dict literal `{name = "Ana"}`→`{"name": "Ana"}`, dict dot access for **read** (`student.name`→`student["name"]`) and **write** (`student.grade = 10`→`student["grade"] = 10`) (GEN-02).
- The runtime helper **bodies** (`_atena_concat`, `_atena_index` — names locked upstream), Python-keyword identifier **mangling**, **unique** nested-`repeat` loop variables (GEN-04).
- The zero-error hard gate (GEN-03) and the `ast.parse()` self-check on every output (GEN-05).
- The golden `school.atena` fixture + its derived `school.expected.py` snapshot + a battery of small targeted fixtures (GEN-06).

**Not in scope:**
- Any **semantic decision** — Phase 3 already injected coercion (`str()`/`_atena_concat`), folded literal indices (`index_converted`), routed dynamic indices (`_atena_index`), and did scope/arity. The generator **emits these marks verbatim**; it never re-shifts or re-wraps (anti-pattern 4).
- Pipeline wiring, the two-verb CLI, and the runtime-error→Atena-line translation — **Phase 5** (CLI-01…CLI-06). `pipeline.py` is a stub today.
- The `examples/` concept ladder beyond `school.atena` and the getting-started README — **Phase 6** (DOCS-01/02). Packaging entry point — **Phase 6** (PKG-01).

</domain>

<decisions>
## Implementation Decisions

### Codegen strategy (discussed)

- **D-01 — Strategy A (`ast.unparse()`) as the spine.** Map each analyzed Atena node to the corresponding CPython `ast` node (`ast.Assign`, `ast.For`, `ast.Call`, `ast.Subscript`, `ast.If`, `ast.While`, `ast.FunctionDef`, `ast.Return`, `ast.BinOp`, `ast.Compare`, `ast.BoolOp`, `ast.UnaryOp`, `ast.List`, `ast.Dict`, literals), call `ast.fix_missing_locations(module)`, then `ast.unparse(module)`. **Chosen over hand-rolled string emission (B)** because the project's worst bug class is *"runnable Python that gives wrong answers"* — operator-precedence/parenthesization bugs that the `ast.parse()` self-check **cannot** catch (the output parses fine; it's just wrong). Strategy A makes that entire class **structurally impossible** (correct precedence, parenthesization, and indentation for free). Zero new dependencies. *(Resolves the STATE.md-flagged Phase-4 "A vs B" decision. Note: ARCHITECTURE.md sketched strategy B — a string-emitting visitor — but STACK.md/SUMMARY.md recommended A; A wins.)*
- **D-02 — Hybrid: a small post-pass recovers the teaching-readability gaps pure `unparse()` loses.** Because learners **read** the generated Python via `--show` (CLI-06), output readability is a product feature. Three patches are **locked**:
  1. **Double-quoted strings** — `ast.unparse()` defaults to single quotes (`'Ana'`); the learner typed double quotes (`"Ana"`), so restore `"…"` to match their source.
  2. **Blank lines between top-level functions.**
  3. **Header comment** at the top of the file (e.g. `# Generated from school.atena by Atena`).
  - *Planner note:* the double-quote patch is the fragile one (strings already containing a quote char — `unparse` itself switches to double quotes when a string contains a single quote), so do **not** use a naive global string replace; handle it carefully. Blank-lines and header are trivial/safe. The `ast.parse()` self-check runs **after** the patches.

### Golden `school.atena` (discussed)

- **D-03 — Claude authors `school.atena`** as the canonical example (no spec file or `.atena` exists in the repo today). A coherent **school/grades** program; the **user reviews** the final program before it is locked.
- **D-04 — Maximal capstone.** `school.atena` exercises the **full construct set**: I/O, variables, `if`/`else`, `while`, **nested** `repeat`, functions + `return`, lists (`add`/`remove`/`length`/index, incl. nested), dicts (literal + dot **read** + dot **write**), `str()` coercion, and the precedence ladder. It **doubles as the Phase 6 curriculum flagship** (DOCS-01). Backed by a **battery of small, single-purpose targeted fixtures** for edge cases the capstone can't isolate cleanly: keyword-collision mangling, nested-`repeat` loop-var uniqueness, dynamic-index `_atena_index` routing, the `_atena_concat` path, dict dot-write, etc.
- **D-05 — `ask` is string-only and used for a name only.** The capstone asks for **one string** (e.g. student name) and shows a personalized greeting — the idiomatic v1.0 use of `ask` (Phase-3 D-03: `ask` returns `str`, no number parsing). **Grades live as list/dict literal data** so numeric logic (averages, pass/fail) works correctly. This exercises `ask`→`input` without hitting the no-number-parsing limitation. The **execution test feeds canned stdin** so output stays deterministic (ROADMAP criterion #1: generated Python must *execute* to expected output, not just text-match).
- **D-06 — The expected output is a derived, reviewed snapshot — not hand-authored.** Because strategy A is locked, `school.expected.py` = whatever the pipeline emits (`unparse()` + the three D-02 patches). It is generated **once**, reviewed for correctness, and locked as the golden snapshot. GEN-06's "exactly matching expected Python output" is a **text-match against that snapshot AND an execution test** (run it with canned stdin, assert stdout).

### Claude's Discretion
The user explicitly **declined to lock** these (they are technical/implementation choices). Resolve in research/planning, honoring the recommendations below and the locked items above.

- **Runtime-helper emission policy** — emit the `_atena_index` / `_atena_concat` helper **bodies** always (fixed preamble on every file) vs **only when the program references them**. **Recommendation: on-demand** (only when used) for clean learner-facing output — a program with no lists / no unknown-typed concat shouldn't carry helper noise. Helper **names are locked** (`_atena_concat`, `_atena_index`, `_atena_` prefix per 03-CONTEXT); bodies must be collision-proof and raise plain-English Atena errors (`_atena_index` keeps the single unified `i < 1` message — 03-CONTEXT D-06).
- **Keyword-mangling scheme (GEN-04)** — **Recommendation: trailing-underscore** (`class`→`class_`, `import`→`import_`) over Python's `keyword.kwlist`. Decide whether to also guard soft keywords (`match`/`case`/`type`) and shadowed builtins (`print`/`list`/`len`); the **minimum** is `keyword.kwlist` so the output parses. Apply the mangle **consistently at every reference** of a mangled name.
- **Nested-`repeat` loop-variable naming (GEN-04)** — **Recommendation: a collision-proof `_atena_`-prefixed unique var per nested `repeat`** (e.g. `_atena_i0`, `_atena_i1` by depth, or a monotonic counter), consistent with the `_atena_` prefix convention. Must be unique across nesting so an inner loop never shadows an outer loop var.
- **Execution-test harness mechanics** — how the golden's execution test feeds canned stdin and captures stdout (subprocess with `input=…` vs monkeypatching `input` + `capsys`). Planner's call; either is fine. *(The `exec`-vs-`subprocess` decision for `atena run` itself is Phase 5, not here.)*
- **`ast`/`unparse` compatibility** — emit via the stdlib `ast` on the floor Python (3.11); avoid version-specific node fields.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 4 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 4: Code Generator" — the 5 success criteria (golden round-trip **text + execution**; construct + list/dict mappings; **verbatim** emission with no double-shift / no re-wrap; correct indentation + unique nested-`repeat` var + keyword mangling; `ast.parse()` self-check + zero-error gate), dependency on Phase 3, and the GEN-01…GEN-06 mapping.
- `.planning/REQUIREMENTS.md` §"Code Generator" — GEN-01 … GEN-06 verbatim.

### Codegen strategy & pitfalls (authoritative for HOW)
- `.planning/research/STACK.md` §"Code generation — RECOMMEND `ast.unparse()`" (+ "Stack Patterns by Variant", "Testing") — strategy A vs B, the fixture convention (`tests/fixtures/<name>.atena` + `<name>.expected.py`, parametrized), `syrupy` deferred, the `ast.parse()` self-check. **We locked A + the three D-02 patches.**
- `.planning/research/ARCHITECTURE.md` — the codegen module sketch (`codegen.py` → `CodeGenerator: Program -> python source string`; "a visitor returning strings" — note this **leaned B and is superseded by D-01's A choice**), the Data-Flow **contract D**, the **hard-gate rule** (codegen runs only when `is_empty()`), **anti-pattern 4** (NO coercion/indexing logic in codegen — emit verbatim), **anti-pattern 7** (no codegen on an errored tree). The `exec`-vs-`subprocess` table there is Phase-5 relevant, not this phase.
- `.planning/research/PITFALLS.md` — codegen-relevant items: the **verbatim-emission discipline** (don't re-shift indices the analyzer already folded; don't `str()`-wrap a number-only `x + 1`), **nested-`repeat` loop-var uniqueness**, **keyword mangling**, and the **three-test-layer gate** (golden snapshot + **execution test that runs the generated Python** + `ast.parse()` self-check). Index/coercion bugs are *runnable-but-wrong* — execution tests are mandatory.
- `.planning/research/SUMMARY.md` §"Flagged Decisions" #1 (codegen A vs B — **now resolved as A + patches**) and the "output readability is a teaching feature" framing; the `school.atena` → `school.expected.py` end-to-end fixture is the canonical golden.

### Data contract the generator consumes (read-only — emit verbatim)
- `src/atena/ast_nodes.py` — contract C/D: the 22 `@dataclass` nodes. The generator **reads, never mutates**: `IndexAccess(target, index, index_converted)` — literal indices already folded; `BinOp`/`UnaryOp` — coercion already injected as `FunctionCall(name="str"/"_atena_concat"/"_atena_index")` nodes; `DictLiteral.pairs` `(k, v)` → `ast.Dict` with string keys; `DotAccess(target, name)` → `ast.Subscript` with a string-constant key (read AND write); `ListAdd`/`ListRemove` → `.append`/`.remove` calls; `Repeat(count, body)` → `ast.For` with a generated loop var; `Ask(prompt, target)` → assignment of `input(prompt)`; `Show(value)` → `print(...)`; `FunctionDef`/`FunctionCall`/`Return`; `BoolLiteral`→`True`/`False`.
- `src/atena/analyzer.py` — the upstream producer (contract C). **Note `[03-02]`: a `BinOp` is converted in place to a `FunctionCall` via `__class__` reassignment for `_atena_concat`** — so the generator sees a `FunctionCall` node (not a `BinOp`) for routed concats, and emits it as a plain call to the helper.
- `src/atena/errors.py` — `ErrorCollector.is_empty()` is the hard gate the (Phase-5) driver checks **before** invoking codegen. The generator itself adds no errors; a GEN-05 self-check failure is an internal bug surfaced in tests, never via the collector or to the learner.

### Cross-phase boundaries (locked)
- `.planning/phases/03-semantic-analyzer/03-CONTEXT.md` — the Analyzer→Generator contract: the analyzer **marks/routes**, the generator **emits verbatim**. Explicitly **Phase-4's to emit** (analyzer only routed): the runtime helper **bodies** (`_atena_concat`, `_atena_index`), Python-keyword identifier **mangling** (GEN-04), and **dict-dot→subscript** emission (GEN-02). Helper-routing nodes are `FunctionCall(name="_atena_concat"/"_atena_index"/"str")`.
- `.planning/PROJECT.md` §Constraints / §Key Decisions — 1-indexing is already handled upstream (**don't re-shift**), integers / double-quoted strings only, **no traceback ever**, collect-all-errors, TDD + per-phase feature branch (`feat/codegen` / `feat/generator`, never `main`), one phase 100% green before advancing, the three-test-layer gate.

*No standalone reference-spec file exists in the repo — the "spec's golden `school.atena`" named in GEN-06/PROJECT.md does not yet exist and is authored in this phase (D-03/D-04). The decisions here were pinned because they were the open Phase-4 items flagged in STATE.md.*

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/atena/ast_nodes.py`** — mutable `@dataclass` nodes (free `__eq__`/`__repr__`); the generator treats them as **read-only**. The node→`ast` mapping is mechanical and one-to-one for almost every node.
- **`src/atena/errors.py`** — `is_empty()` is the gate; `suggest()`/`ATENA_KEYWORDS` are not needed in this phase.
- **`tests/` (test_lexer.py, test_parser.py, test_analyzer.py, conftest.py)** — the three-test-layer style to mirror in a new **`tests/test_codegen.py`** + **`tests/fixtures/`**. Plain file-fixture goldens + `assert` (zero deps); `syrupy` stays deferred.
- **Python stdlib `ast` + `ast.unparse()`** (3.9+, floor 3.11) — the codegen engine; `ast.parse()` for the self-check. Zero runtime dependencies preserved.

### Established Patterns
- **`ErrorCollector` is injected, never global**; pure data modules import only `ast_nodes`/`errors`/stdlib. `codegen.py` imports `ast_nodes` + stdlib `ast` — **never** the lexer/parser/analyzer.
- **TDD per PROJECT.md** — failing test first, commit per task, `feat/` branch (never `main`). Build happy-path construct emission first (toward the golden), then the mangling / loop-var / helper-body / self-check edge fixtures.
- **Three-test-layer gate is mandatory before "green":** golden snapshot (text match) + **execution test** (run the generated Python, assert stdout — catches index/coercion bugs text can't) + `ast.parse()` self-check on every output.

### Integration Points
- **Analyzer → Generator (contract C→D):** the same fully-analyzed `Program`, **read-only**; emit verbatim. Helper-routed concats/indices arrive as `FunctionCall` nodes.
- **Generator → (Phase 5) driver:** the driver checks `errors.is_empty()`, then calls `CodeGenerator(program).generate()` → a Python source string (contract D). `pipeline.py` wiring is **Phase 5**, not here (`pipeline.py` is currently a stub that raises `NotImplementedError`).
- **`src/atena/codegen.py`, `tests/test_codegen.py`, `tests/fixtures/`, and `examples/school.atena` do not exist yet** — Phase 4 creates them.

</code_context>

<specifics>
## Specific Ideas

- **Header-comment draft:** `# Generated from school.atena by Atena` (exact wording is discretion — keep a friendly, plain tone).
- **`school.atena` shape:** a school/grades program — asks for a **student name** interactively (string), keeps **grades as literal list/dict data**, computes an **average + pass/fail**, and shows a **personalized greeting**. The exact program is Claude's to author; the **user reviews** before it locks.
- **The `school.expected.py` golden is a derived snapshot** (unparse + the 3 patches), reviewed once, then locked — not hand-authored independently.

</specifics>

<deferred>
## Deferred Ideas

- **"Always-preamble" helper-emission mode** and **exhaustive builtin-shadowing mangling** — candidate refinements; the v1.0 defaults are the Claude's-Discretion recommendations above (on-demand helpers, `keyword.kwlist` minimum).
- **Number-parsing for `ask`** (so `age = ask "..."` yields a number, enabling an interactive grades flow) — the locked Phase-3 D-03 v1.0 limitation; a natural **v2** item (alongside float support).

**Cross-phase boundaries (not deferrals):** (1) the `examples/` concept ladder beyond `school.atena` and the getting-started README belong to **Phase 6** (DOCS-01/02). (2) The runtime-error→Atena-line translation that rephrases a *leaked* Python runtime error belongs to **Phase 5** (CLI-04). This phase only emits the Python and self-checks it.

Discussion stayed within phase scope — no scope creep to redirect.

</deferred>

---

*Phase: 4-Code Generator*
*Context gathered: 2026-06-14*
</content>
</invoke>
