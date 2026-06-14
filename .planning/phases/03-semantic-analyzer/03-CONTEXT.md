# Phase 3: Semantic Analyzer - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 takes the parser's **`Program` AST (contract B) and enriches it in place** with every semantic decision, producing the **analyzed AST (contract C)** the Phase-4 generator emits *verbatim* — the third real phase of the pipeline. It is a tree-walk (`visit_<NodeType>` dispatch, ARCHITECTURE Pattern 9) that **mutates nodes** and reads/writes the shared `ErrorCollector`; it never raises to the user and never builds a parallel tree.

Concretely it delivers a `SemanticAnalyzer` (`src/atena/analyzer.py`) that:

- **Injects `str()` coercion** for `string + (number|boolean)`, evaluated **bottom-up** so result types propagate up `+` chains (`"a" + 1 + 2` → `"a12"`), and reports a plain-English **"Cannot combine [type] and [type]"** error for disallowed `+` combinations (SEM-01/SEM-02).
- **Rewrites 1-indexed access to 0-indexed**, idempotently via the existing `IndexAccess.index_converted` flag, for both flat and nested subscripts (`grid[2][3]` → `grid[1][2]`); rejects a literal `0` / literal negative with a line-numbered error; routes **variable / expression** indices through a runtime index helper (SEM-03/SEM-04/SEM-05).
- **Detects undefined names** in plain English and **poisons** them (one mistake → one error), enforces **defined-before-called (no hoisting)** for functions, and checks **call arity** (SEM-06/SEM-07).
- Owns a **lightweight forward type inference** over a tiny lattice (`number / str / bool / list / dict / unknown`), *not* a real type system — just enough to decide "is this `+` a string concat?" (ARCHITECTURE Pattern 10).

Covers requirements **SEM-01 … SEM-07**.

**In scope:** type inference + `str()` coercion injection + the runtime concat decision; the "Cannot combine" error for `+`; the 1→0 rewrite + literal-bounds errors + the dynamic-index runtime-helper routing; undefined-variable detection + symbol poisoning; two-level scope resolution; defined-before-called + arity checks; the symbol table (built and consumed entirely within this single pass — it does not cross a phase boundary).

**Not in scope:** parsing / AST construction (Phase 2); **top-level `return`** (already owned by the Phase-2 parser, `02-CONTEXT.md` D-04.3 — do NOT re-handle it here); code emission of any kind, including the bodies of the `_atena_concat` / `_atena_index` runtime helpers and Python-keyword identifier mangling (GEN-04) and dict-dot→subscript emission (GEN-02) — all Phase 4; pipeline wiring + the runtime error→Atena-line translation (CLI-04, Phase 5). The analyzer **marks** nodes / records decisions; the generator reads them.

</domain>

<decisions>
## Implementation Decisions

### Type coercion & `str()` injection (SEM-01 / SEM-02)

- **D-01 — Lightweight bottom-up inference, under-coerce rather than over-reject (locked foundation).** Every expression node gets an inferred type from the tiny lattice. Literals are known (`StringLiteral`→`str`, `NumberLiteral`→`number`, `BoolLiteral`→`bool`, `ListLiteral`→`list`, `DictLiteral`→`dict`). `+` result-type propagates bottom-up so chains coerce correctly. The coercion function is **total** — every (left-type, right-type) pair maps to exactly one outcome (no-coerce / coerce-left / coerce-right / error), no silent fall-through (PITFALLS 10/11). This is locked by research (ARCHITECTURE Pattern 10, anti-pattern 5) and PROJECT.md; restated here as the basis for D-02/D-03.
- **D-02 — UNKNOWN-typed `+` operand → a runtime concat helper, NOT a static decision or a rejection.** When either side of a `+` has type `unknown` (a function-call result, a parameter — and more broadly anything the analyzer can't prove), the analyzer routes the `+` through a generated `_atena_concat(a, b)` runtime helper that decides string-vs-number **at runtime** and never crashes. Chosen over bare `a + b` (could leak a runtime `TypeError`) and over compile-time rejection (would reject legitimate beginner concatenation involving a function result/parameter — violates under-coerce). This makes the spec's "silent coercion never crashes" promise hold even where types are invisible. *(STATE.md flagged this as the open Phase-3 decision; now decided.)*
- **D-03 — `ask` results are typed `str`.** `answer = ask "..."` makes `answer` a `STRING` in the symbol table (Python `input()` returns text). So `answer + "!"` is plain static concat and `answer + 1` statically wraps the `1` via `str()` — both decided at analysis time, no runtime helper needed. **Known v1.0 limitation (document, don't fix):** there is no number-parsing, so `age = ask "..."` followed by arithmetic on `age` concatenates as text rather than adding — consistent with "integers only, no input coercion" being out of v1.0 scope.
- **D-04 — Analysis-time type-checking is scoped to `+` only (resolved by research default; this gray area was not selected for discussion).** The "Cannot combine [type] and [type]" error fires **only for `+`**. Mismatched string/number operands under `-`, `*`, `/`, and comparisons are **not** type-checked at analysis time (the requirements scope coercion + the combine-error to `+`; SEM-01/SEM-02). Any resulting runtime error (e.g. `name - 1`) is caught and re-phrased by the **Phase-5 runtime translation layer** (CLI-04), not by this phase. Rationale: stays within SEM scope, honors under-coerce, avoids inventing new compile-time rejections. *(A future enhancement could catch obviously-disallowed combos where both literal types are known, e.g. `"a" - 1` — noted under Deferred, not v1.0.)*

### 1→0 index rewrite & bounds (SEM-03 / SEM-04 / SEM-05)

- **D-05 — Literal boundary = bare `NumberLiteral` and a negated literal (`-n`); everything else is dynamic.** A bare `NumberLiteral` index and a `UnaryOp("-", NumberLiteral)` (i.e. `items[-3]`) are resolved **at compile time**: a positive literal `n` is folded in place to `n-1` (idempotent — guarded by `IndexAccess.index_converted`, set once, asserted never twice; nested `grid[2][3]` → `grid[1][2]`); a literal `0` or a literal negative is a **line-numbered compile error** with no rewrite. Every **other** index form — a variable (`items[i]`), or *any* arithmetic (`items[i+1]`, and deliberately also the constant-looking `items[2+1]`) — is treated as **dynamic** and routed to the runtime `_atena_index` helper. Chosen over constant-folding pure-number expressions (rejected: adds a constant-evaluator for marginal extra catches) and over bare-literal-only (rejected: would push `-3` to runtime instead of giving it a line number). Clean, predictable: "a plain number or its negation is checked now; anything with a variable or operator is checked when it runs."
- **D-06 — Literal negative index gets its OWN message, distinct from the literal-`0` message.** A compile-time literal `0` keeps the canonical `Lists in Atena start at 1, not 0.`; a compile-time literal negative (`items[-3]`) gets a separate negatives-specific line (draft in `<specifics>`) that teaches against Python's from-the-end mental model. **The runtime `_atena_index` helper, which can't distinguish the source form, keeps a single unified `i < 1` message** (PITFALLS 5) — the distinct wording is a *compile-time literal* affordance only.

### Scope & name resolution (SEM-06 / SEM-07)

- **D-07 — Two-level scope, "pure functions": a function body may NOT read top-level variables.** Two scopes only (no nesting/closures — already out of scope): a **top-level/global** scope, and **one local scope per function** (its parameters + the variables it assigns in its body). A function body resolves a name against: its params, its own locals, and the set of **function names defined before it** (so it can still *call* earlier functions). It **cannot** see top-level *variables*; its own locals/params **do not leak** to the top level or into sibling functions. Top-level code resolves against globals + earlier-defined function names. **No hoisting** anywhere — a single top-to-bottom pass; a name used before it is assigned/defined is undefined (variables and functions both). Chosen over flat single-scope (rejected: diverges from the generated Python's real function-local scope → the analyzer would green-light programs that `NameError` at runtime) and over "two-level, functions read globals" (the user chose the stricter, more teachable model). **Payoff:** because the analyzer rejects function-reads-global, valid programs never rely on Python's implicit global read, so the Phase-4 output is naturally clean.
- **D-08 — Reaching for an outer variable from inside a function gets a TAILORED teaching message.** When a function body references a name that the analyzer finds **exists at top level but is not reachable in this scope**, it does not emit the generic undefined-name error — it emits a scope-specific teaching message: *"A function can only use its own inputs — pass "X" in as a parameter."* (draft in `<specifics>`). This turns the D-07 restriction into the lesson it's meant to be. A name that exists **nowhere** still gets the standard undefined-name + `suggest()` "Did you mean?" path (D-09).
- **D-09 — Undefined names are poisoned; functions checked for defined-before-called + arity; reuse `suggest()` (carried/locked).** First undefined use of a name reports once and records the name as a poisoned `UNKNOWN` entry so later uses don't re-report and don't trigger downstream coercion errors (PITFALLS 12). The undefined-name message reuses the locked Phase-0 voice and the existing `errors.suggest(name, candidates)` engine — candidates = in-scope names + `ATENA_KEYWORDS`; the case-only "Did you mean?" already maps `True`→`true` etc. (the **name-shaped** Python-isms the parser deliberately left to this phase, `02-CONTEXT.md` D-05). Functions register `name → arity` as reached; a call to an unregistered name is "called before defined", a registered one is arity-checked (human-terms message naming the function, expected, and given counts).

### Claude's Discretion
The user did not constrain these; resolve during research/planning (honor the locked items above):

- **How decisions are recorded on the AST.** Whether `str()` wrapping is represented by injecting a `FunctionCall(name="str", args=[operand])` node, the runtime helpers by `FunctionCall(name="_atena_concat"/"_atena_index", ...)` nodes, or by new boolean flags on `BinOp`/`IndexAccess` — both keep codegen a dumb emitter. Node-injection reuses existing contract-B nodes (see `<code_context>`); flag-addition mutates the dataclass. Pick whichever keeps Phase 4 simplest; keep it idempotent. (`IndexAccess.index_converted` already exists and is the one mandated marker.)
- **Symbol-table structure** — e.g. a `dict[str, Type]` for globals + a pushed/popped `dict` per function for locals, plus a separate `dict[str, int]` for function arities. Single forward pass; no fixpoint.
- **Reassignment / flow-sensitive type changes** — last-assignment-wins is acceptable; when a variable's inferred type differs across branches (`if … x = 5 else x = "hi"`), fall back to `UNKNOWN` (safe — routes any later `+` through the runtime helper) rather than guessing. Document the limitation (ARCHITECTURE Pattern 10 explicitly permits mis-inference here because the worst case is an extra/missed `str()` wrap, never a crash).
- **Function-vs-variable name collisions** — Python uses one namespace for both; the analyzer should not green-light a program where a variable shadows a function it later calls (or vice versa). Default to treating names as a single namespace to match the generated Python; finalize in planning.
- **Runtime-helper naming** — use a collision-proof prefix users can't produce (e.g. `_atena_concat`, `_atena_index`), consistent with the `_atena_`-prefixed loop vars planned for Phase 4. The helper *bodies* are emitted in Phase 4; this phase only decides *which nodes route through them*.
- **Exact message wordings** — the "Cannot combine" text, the distinct literal-negative line, the tailored function-scope line, the arity message — draft in the Phase-0 voice; `<specifics>` has starting drafts. The *decisions* are locked; the strings are discretion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 3 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 3: Semantic Analyzer" — the 5 success criteria (what must be TRUE), dependency (Phase 2), and the SEM-01…SEM-07 mapping. Note criterion #1 (bottom-up coercion + "Cannot combine"), #2 (idempotent 1→0, nested, literal-0 error), #3 (variable index via runtime helper, no silent negative wrap), #4 (undefined → poison, one-error), #5 (no-hoisting call-before-def + arity).
- `.planning/REQUIREMENTS.md` §"Semantic Analyzer" — SEM-01 … SEM-07 verbatim.

### Architecture & pitfalls (authoritative for HOW)
- `.planning/research/ARCHITECTURE.md` — **the single most relevant doc.** Especially: **Pattern 9** (visitor/tree-walk, `visit_<NodeType>`; analyzer mutates, codegen reads), **Pattern 10** (coercion without a real type system — the lattice, bottom-up `+` propagation, the **permissive-UNKNOWN → runtime helper** policy that D-02 selects), **Pattern 11** (1→0 rewrite owned by the analyzer; literal fold vs dynamic `-1`; `index_converted`), **Pattern 12** (no hoisting; defined-before-called single forward pass); the Data-Flow **contract C** (same `Program` mutated in place) and the **gating rule** (codegen is the hard gate on `is_empty()`); anti-patterns 4 (no coercion/indexing in codegen), 5 (no full type system), 6 (no Python exception to the user), 7 (no codegen on an errored tree).
- `.planning/research/PITFALLS.md` — Analyzer-owned pitfalls: **5** (variable index shift — never emit bare `[i-1]`; route through `_atena_index`; `i==0`→last-element trap), **6** (double-shift — single idempotent step, tag converted nodes, nested-subscript test), **10** (coercion operand/chain — inferred type per node, bottom-up, `"a"+1+2`="a12", wrap the correct side), **11** (the "Cannot combine" path must be total, human type names in source order), **12** (cascading errors — poisoned symbols + UNKNOWN suppression), **20** (defined-before-called, do NOT pre-scan defs), **21** (arity + `return`-outside-function — note `return` is Phase-2's per `02-CONTEXT.md`). Plus the "Looks Done But Isn't" analyzer checklist items and the **three-test-layer** principle (golden snapshots + **execution tests that run the generated Python** + error-path tests asserting exact message/count/line order). Note: index & coercion bugs are *runnable-but-wrong-output* — execution tests are mandatory, but they begin once Phase 4 exists; for Phase 3, assert on the **mutated AST** (folded indices, injected `str()`/helper markers, inferred types) and on error message/count/line order.
- `.planning/PROJECT.md` §Constraints / §Key Decisions / §Context — 1-indexed (`[0]` is a deliberate error), silent `str()` coercion for string+number/boolean (others error), collect-all-errors over fail-fast, no traceback ever, integers/double-quoted only, TDD + per-phase feature branch (`feat/analyzer` / `feat/semantic-analyzer`), one phase 100% green before advancing.

### Data contracts the analyzer mutates (locked — do not redefine)
- `src/atena/ast_nodes.py` — **contracts B (in) and C (out).** The 22 mutable `@dataclass` nodes. Key fields the analyzer touches: `IndexAccess(target, index, index_converted=False)` — the mandated idempotency marker; `BinOp(op, left, right)` — the coercion site; `UnaryOp(op, operand)` — recognise `("-", NumberLiteral)` as a literal-negative index; `Ask(prompt, target)` — `target` becomes a `str`-typed symbol (D-03); `FunctionDef(name, params, body)` / `FunctionCall(name, args)` — arity source/check; literal nodes carry their static types.
- `src/atena/errors.py` — `ErrorCollector.add(line, message, source_line)` is the ONLY reporting path (never formats the envelope). **`suggest(name, candidates)`** (fuzzy + case-only "Did you mean?", D-06 capitalization rule fires first) and **`ATENA_KEYWORDS`** (19 words) are the undefined-name affordances. `ERROR_CAP`/dedup/sort are handled at `report()` time — the analyzer just `add()`s.
- `src/atena/parser.py` — the upstream producer; consumes its `Program` (may be *partial* if parse errors were collected — analyze whatever AST exists, the driver gates codegen on `is_empty()`). `src/atena/tokens.py` for any `TokenType`/`KEYWORDS` reference.

### Error voice & cross-phase boundaries (locked Phase 0/1/2 contracts)
- `.planning/phases/00-diagnostics-spine-data-contracts/00-CONTEXT.md` — the **error voice** (D-01 "Plain & kind", D-03 "problem + guidance when clear", D-06 case-only "Did you mean?"); the `<specifics>` exemplars (incl. the canonical `I don't know what "score" is yet. Did you forget to create it first?`) are the tone to match.
- `.planning/phases/02-parser/02-CONTEXT.md` — the boundary split this phase inherits: the **parser owns structural Python-isms and top-level `return`** (D-04); the **analyzer owns name-shaped Python-isms** (`True`/`False`/`None`, `print`/`input`/`len`) via undefined-name + case-only suggest (D-05). Do not re-handle `return` here.

**No standalone reference-spec file exists in the repo** — the "reference spec" named in `PROJECT.md` is captured through the four research docs + the locked code contracts above. The decisions in this discussion (UNKNOWN→runtime helper, literal-index boundary, pure-function scope) were pinned here because they were left to phase planning; confirm against the user's source spec if it later surfaces.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/atena/ast_nodes.py`** — mutable dataclasses (free `__eq__`/`__repr__`) mean analyzer tests assert `analyzed_node == expected_node` literals after the pass. `IndexAccess.index_converted` is the ready-made idempotency flag for the 1→0 rewrite. **Node-injection insight:** `str()` wrapping and the runtime helpers can be represented by reusing the existing `FunctionCall` node (`FunctionCall(name="str"|"_atena_concat"|"_atena_index", args=[…])`) rather than adding new node types or flags — keeps the contract stable and Phase-4 codegen a faithful emitter (see Claude's Discretion).
- **`src/atena/errors.py`** — inject the shared `ErrorCollector` into the `SemanticAnalyzer` constructor (never global). `suggest()` + `ATENA_KEYWORDS` give the "Did you mean?" + case-only capitalization behavior for free; build candidates as `in_scope_names + ATENA_KEYWORDS`.
- **`tests/test_parser.py`, `tests/test_lexer.py`** — show the three-test-layer style to mirror in a new `tests/test_analyzer.py` (golden mutated-AST snapshots + error-path tests asserting exact message / count / line order). `tests/conftest.py` for shared fixtures.

### Established Patterns
- **ErrorCollector is injected, never global** — `SemanticAnalyzer(program, errors)` per the Phase-0/ARCHITECTURE boundary; report every semantic error via `add(line, message, source_line)` using `node.line` / `node.source_line`.
- **Pure data modules stay dependency-free** — `analyzer.py` imports `ast_nodes` + `errors` (+ stdlib) only; it never imports the lexer/parser.
- **`errors.py` owns the `Error on line {N}: … → {source}` format** — the analyzer supplies only the plain-English `message`.
- **TDD per PROJECT.md** — failing test first, commit after each task, work on a `feat/` branch (never `main`). Build the happy-path passes first (inference → coercion → index rewrite → scope/arity), then the error/poisoning paths before declaring the phase green.

### Integration Points
- **Parser → Analyzer (contract B):** the same `Program` object handed forward; the analyzer mutates it (sets `index_converted`, injects coercion/helper markers, folds literal indices). It must accept a partial AST without crashing.
- **Analyzer → Generator (contract C):** the same `Program`, now fully analyzed; the generator treats it as **read-only** and emits verbatim (it never re-derives indices or coercion — anti-pattern 4). The helper *bodies* (`_atena_concat`, `_atena_index`) and Python-keyword mangling are emitted in Phase 4; this phase only marks/routes.
- **Analyzer → ErrorCollector:** the cross-cutting injection point; the Phase-5 driver inspects `is_empty()` after this phase and **hard-gates codegen** on zero errors.
- **`src/atena/analyzer.py` and `tests/test_analyzer.py` do not exist yet** — Phase 3 creates them. `pipeline.py` wiring is Phase 5, not here.

</code_context>

<specifics>
## Specific Ideas

Draft message exemplars surfaced during discussion — **starting drafts**, to be refined into the exact Phase-0 voice during planning/implementation (match `00-CONTEXT.md` `<specifics>` for tone). All guide toward the fix:

- Cannot combine (disallowed `+`): `I can't add a [type] and a [type] together — try making them the same kind first.`
- Literal `items[0]` (locked canonical): `Lists in Atena start at 1, not 0.`
- Literal negative index (D-06, distinct): `Atena lists count from 1 — there are no negative positions. The last item is at length, not -1.`
- Runtime index helper, `i < 1` (single unified message): `Lists in Atena start at 1, not 0.`
- Undefined variable (locked canonical from Phase 0): `I don't know what "score" is yet. Did you forget to create it first?`
- Function reads an outer variable (D-08, tailored): `A function can only use its own inputs — pass "total" in as a parameter.`
- Called before defined: `I don't know a function called "greet" yet — define it above this line first.`
- Wrong arity: `"greet" expects 1 value, but you gave 2.`

These are guidance drafts, not locked strings — the *decisions* (UNKNOWN→runtime `_atena_concat`; `ask`=str; literal-incl-`-n` index boundary with a distinct negative message; pure-function two-level scope with a tailored outer-variable message) are locked; exact wording is Claude's discretion within the Phase-0 voice.

</specifics>

<deferred>
## Deferred Ideas

- **Compile-time rejection of obviously-disallowed non-`+` literal combos** (e.g. `"a" - 1`, `"a" * "b"` where both literal types are known) — a future enhancement to D-04. In v1.0 only `+` is type-checked at analysis time; other mismatches surface through the Phase-5 runtime translation layer. Not a dropped requirement — a candidate refinement.
- **Number-parsing for `ask` input** (so `age = ask "..."` yields a number) — explicitly out of v1.0 scope (integers-only, no input coercion); the D-03 known limitation. A natural v2 item alongside float support.

Two items are **cross-phase boundaries, not deferrals:** (1) the runtime helper *bodies* (`_atena_concat`, `_atena_index`), Python-keyword identifier mangling (GEN-04), and dict-dot→subscript emission (GEN-02) belong to **Phase 4** — this phase only marks/routes. (2) The runtime error→Atena-line translation that re-phrases a leaked Python error (e.g. a non-`+` type mismatch, an out-of-range dynamic index) belongs to **Phase 5** (CLI-04).

</deferred>

---

*Phase: 3-Semantic Analyzer*
*Context gathered: 2026-06-14*
