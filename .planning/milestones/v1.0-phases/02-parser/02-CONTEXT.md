# Phase 2: Parser - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 turns the lexer's **balanced token stream (`list[Token]`) into a complete `Program` AST** that the Semantic Analyzer can consume — the second real phase of the pipeline (contract A → contract B).

Concretely it delivers a `Parser` (`src/atena/parser.py`) that:

- **Recursive descent** for statements (a `statement()` dispatcher → `parse_if`/`parse_while`/`parse_repeat`/`parse_function_def`/`parse_show`/`parse_ask`/`parse_return`/`parse_list_op`, falling through to assignment / call), and **Pratt / precedence-climbing** for expressions, driven by a single precedence table that encodes the locked ladder: `or → and → not → comparison → +/- → */ → unary - → postfix []/./()`.
- Parses **indentation-delimited blocks** by consuming the lexer's already-balanced `INDENT … DEDENT` (never counts columns) for `if/else`, `while`, `repeat`, and `function` bodies, to arbitrary nesting depth.
- Constructs the 22 locked `@dataclass` AST nodes in `src/atena/ast_nodes.py`, copying each triggering token's `line`/`source_line` onto the node.
- **Recovers from syntax errors by synchronizing** on the next statement boundary (`NEWLINE` / `DEDENT`), so one run surfaces every syntax error (one per bad statement, not per-token spam), and **never hangs** (progress invariant: every recovery path consumes ≥1 token).
- Reports every syntax error in plain English through the injected `ErrorCollector`; it never raises to the user and never formats the `Error on line {N}: …` envelope itself.

Covers requirements **PARSE-01 … PARSE-06**.

**In scope:** statement dispatch, Pratt expression parsing honoring the full precedence/associativity ladder, INDENT/DEDENT block parsing, construction of all AST node types, `add … to …` / `remove … from …` statements, list/dict literals, index/dot/call postfix chains, function defs + `return`, the **`ask` surface grammar** (decided below), the **curated parser-level Python-ism redirects** (decided below), synchronization-based error recovery with the progress invariant, and plain-English syntax-error reporting.

**Not in scope:** any semantic decision — undefined-name checks, arity checks, scope/hoisting, `str()` coercion, the 1→0 index rewrite (all Phase 3); codegen (Phase 4); pipeline wiring + `atena run`/`build` (Phase 5). The parser may produce a *partial* AST when errors exist — that is fine, because the driver gates later phases on `ErrorCollector.is_empty()`.

</domain>

<decisions>
## Implementation Decisions

### `ask` input syntax (PARSE-04)

- **D-01 — Surface form is assignment-style: `name = ask "prompt"`.** A learner reads keyboard input by assigning the result of `ask` to a variable, e.g. `name = ask "What is your name?"`. Chosen over positional (`ask "..." name`) and a connector word (`ask "..." to name`) because it reads as "name gets the answer" and reuses the assignment shape the learner already knows. The `prompt` is a **string literal** (the `Ask` node's `prompt` field is a `str`, not a `Node`) — an expression prompt is not supported in v1.0.
- **D-02 — `ask` is a dedicated statement form, allowed only as an assignment right-hand side — NOT a general expression.** `name = ask "..."` is the *only* valid shape. `ask` may not appear inside arithmetic, conditions, or `show` (`show ask "..."`, `x = ask "..." + "!"`, `if ask "..." == "y"` are all errors). Rationale: one teachable shape; input always lands in a named variable; clean error messages. When `ask` is used outside an assignment RHS, the parser emits a friendly redirect (draft in `<specifics>`).
  - **AST representation — Claude's discretion at planning:** the `Ask` node carries both `prompt` and `target`, so `name = ask "..."` maps naturally to `Ask(prompt="...", target="name")` (assignment-flavored surface, dedicated node). Whether the parser emits a bare `Ask(target=...)` or an `Assign` wrapping an `Ask` is left to planning — both satisfy contract B; pick the one that keeps the analyzer/generator simplest. Confirm against the user's reference spec if one surfaces.

### Python-ism redirects — the parser-level teaching off-ramps (PARSE-06)

The parser is the **next phase a learner's mistake reaches** after the lexer. It extends the Phase-1 off-ramp pattern (`01-CONTEXT.md` D-01/D-02) from *lexable* out-of-scope syntax to *token-valid-but-grammatically-wrong* Python habits.

- **D-03 — Curated tailored set, generic fallback (mirrors Phase-1 D-01 exactly).** A **known set** of high-value Python-isms each get a **specific, redirecting** plain-English message. Everything outside the set still gets a **generic** plain-English syntax error (never silence, never a Python exception). Chosen over "generic only" (too little teaching) and "maximal" (large table, risk of firing on innocent identifiers).
- **D-04 — The curated set (three categories the user selected):**
  1. **Out-of-scope Python keywords** — `def` → "Atena uses `function`"; `elif` → "use nested `if`/`else`"; `for … in …` → "use `repeat N times` or `while`"; `class` → "Atena has no classes"; `import` / `from … import` → "an Atena program is a single file." All break the grammar, so the parser reliably catches them (they lex as plain identifiers, then fail statement dispatch).
  2. **`==` used as an assignment** — a standalone statement like `x == 5` (intending to store) → "Did you mean `x = 5`? Use one `=` to save a value, `==` to compare." The classic `=`/`==` beginner slip.
  3. **Top-level `return`** — `return` written outside any function body → "`return` only works inside a function." **The parser owns this message** (it tracks function-nesting context), rather than deferring it to the Phase-3 analyzer's scope checks.
- **D-05 — Capitalized `True`/`False`/`None` are deliberately OUT of the parser set — owned by Phase 3.** These are name-shaped, so the analyzer's case-only "Did you mean?" (`00-CONTEXT.md` D-06) already maps `True`→`true`/`False`→`false`, and undefined-name handling covers `None`. Keeping them out of the parser avoids duplicated, possibly-conflicting messages. **Clean boundary: the parser owns *structural* Python-isms; the analyzer's suggestion engine owns *name-shaped* ones.**
- **D-06 — Redirects are collected + recover-and-continue.** Like the lexer off-ramps, each redirect is a **collected error** (no "warning" concept; the run fails and codegen is gated). The parser **synchronizes and keeps parsing** after each one (progress invariant) so a learner sees every redirect in one run. Per-construct skip distance is Claude's discretion (must satisfy "always make progress / never hang").

### Voice & message structure (carried forward, not re-decided)

- All parser messages follow the locked Phase-0 voice: **"Plain & kind"**, first-person, **problem + guidance when the cause is clear** (`00-CONTEXT.md` D-01/D-03). For Python-isms and the `ask`/`==` slips the cause is unambiguous, so each message **guides** toward the v1.0 fix. For a genuinely shapeless syntax error (unexpected token with no obvious intent), describe-only is acceptable.

### Claude's Discretion

The user did not constrain these; resolve during research/planning (honor the locked items above):

- **Parsing technique** — Pratt vs. precedence-table-of-methods. Research recommends **Pratt** (`ARCHITECTURE.md` Pattern 5) because the precedence table doubles as living documentation of the spec ladder. Either is acceptable; both O(n).
- **Synchronization mechanics** — exact sync tokens (`NEWLINE`/`DEDENT`), how `ParseError` is caught at the statement boundary, and the loop-guard backstop that enforces the progress invariant (`PITFALLS.md` 12/13). Build the happy path first, then add recovery before declaring the phase green.
- **Bare-expression-statement policy (implied by D-04.2).** To catch `x == 5`-as-assignment, the parser lets a comparison reach statement position and then redirects it. The clean resolution: **no meaningless bare-expression statements** — only assignments, function calls (`greet()`), the keyword statements, and `add`/`remove` are valid statements; a bare value or bare comparison at statement position is an error (a tailored one for `==`, generic otherwise). Confirm/refine in planning.
- **Empty blocks / empty program** — whether an `if`/`while`/`repeat`/`function` with no body, or an empty file, is a friendly error or a no-op. Lean toward a friendly "this block needs at least one indented line" message; finalize in planning.
- **`col` precision on AST nodes** — `line` + `source_line` are mandatory and must be exact (copied from the triggering token). Column precision is optional (Phase 0/1 left exact column semantics to later phases).
- **Exact message wordings** — the redirects, the `ask`-misuse message, the `==`-slip message, unclosed-bracket / missing-`times` / empty-body errors, and the generic fallback — draft in the Phase-0 voice (`<specifics>` has starting drafts).
- **Syntax-error guidance specificity (unpicked gray area)** — for structural slips the user did not pick (unclosed `(`/`[`/`{`, `repeat N` missing `times`, function header missing `()`), how tailored vs. generic each message is. Follow the locked "problem + guidance when clear" rule; tailor the high-frequency cases.
- **Recovery aggressiveness on a broken compound header (unpicked gray area)** — when an `if`/`while`/`repeat`/`function` header is malformed, whether to skip the whole indented block (fewer, cleaner errors) or still parse its body. Default to the choice that yields **one-mistake ≈ one-error** for beginners; finalize in planning per `PITFALLS.md` Pitfall 12.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 2: Parser" — the 5 success criteria (what must be TRUE), dependency (Phase 1), and the PARSE-01…PARSE-06 requirement mapping. Note criterion #2 (precedence/associativity), #4 (3 bad statements → 3 errors, no per-token spam), #5 (no infinite loop, no Python exception).
- `.planning/REQUIREMENTS.md` §"Parser" — PARSE-01 … PARSE-06 verbatim (node set, precedence ladder, INDENT/DEDENT blocks, function/return/call/literals/index/dot/add/remove, synchronization recovery, plain-English malformed-statement errors + no infinite loop).

### Architecture & contracts (authoritative for HOW)
- `.planning/research/ARCHITECTURE.md` — **the single most relevant doc.** Especially: **Pattern 5** (recursive descent for statements + Pratt/precedence-climbing for expressions; the precedence table and binding powers), **Pattern 6** (block parsing: `expect(INDENT)` → loop `parse_statement()` until `DEDENT` → `expect(DEDENT)`; parser never counts columns), **Pattern 7** (error recovery via synchronization on `NEWLINE`/`DEDENT` — classic panic-mode, collect-don't-fail-fast); the Parser component responsibility row (`current`/`peek`/`advance`/`expect`/`match` helpers); the project structure (`src/atena/parser.py`, `tests/test_parser.py`); contracts A (token list in) and B (`Program` AST out, same object mutated downstream); source-position threading (copy triggering token's `line` onto each node); the gating rule (codegen is the hard gate; lexer+parser errors both collected).
- `.planning/research/PITFALLS.md` — Parser-owned pitfalls: **7** (unary `-` vs binary `-` via Pratt nud/led split — `-` prefix = high-binding negation, `-` infix = additive subtraction), **8** (precedence/associativity: one binding-power table as source of truth; left-assoc parses right operand with `bp + 1`; golden test per precedence boundary), **9** (postfix `[]`/`.`/`()` left-associate and bind tighter than any binary op — tight postfix loop after primary), **12** (cascading errors → sync points so one bad line = one error), **13** (infinite loop → progress invariant: every recovery path consumes ≥1 token; loop guard tracks position and force-advances). Plus the cross-cutting three-test-layer principle and the "Looks Done But Isn't" parser checklist.
- `.planning/research/FEATURES.md` — MVP "collect-all-errors recovery with **parser synchronization**" is a locked v1.0 launch item and the defining beginner-UX difference; dependency note: Atena's line-oriented, indentation-delimited grammar gives a clean natural sync token (statement/line boundary, DEDENT) — exploit it.
- `.planning/PROJECT.md` §Constraints / §Key Decisions — collect-all-errors over fail-fast; no traceback ever; double-quoted strings + integers only; TDD + per-phase feature branch (`feat/parser`); one phase 100% green (golden snapshots + error-path tests; execution tests begin at codegen) before advancing.

### Diagnostics spine & data contracts the parser plugs into (locked, do not redefine)
- `src/atena/ast_nodes.py` — **contract B.** The 22 mutable `@dataclass` nodes the parser must construct: `Program, Assign, Show, Ask, If, While, Repeat, FunctionDef, Return, FunctionCall, BinOp, UnaryOp, ListLiteral, DictLiteral, IndexAccess, DotAccess, ListAdd, ListRemove, Identifier, NumberLiteral, StringLiteral, BoolLiteral`. Note field shapes: `Ask(prompt: str, target: str)` (literal prompt; see D-01/D-02), `BinOp(op, left, right)`, `UnaryOp(op, operand)`, `DictLiteral.pairs: list[tuple[str, Node]]`, `IndexAccess.index_converted` (Phase-3 flag — parser leaves it `False`).
- `src/atena/tokens.py` — **contract A.** `TokenType` enum (incl. `INDENT`/`DEDENT`/`NEWLINE`/`EOF`), frozen `Token(type, value, line, col, source_line)`, `KEYWORDS` (19 words). The parser peeks/advances over a fully-materialized `list[Token]`.
- `src/atena/errors.py` — `ErrorCollector.add(line, message, source_line)` is the ONLY way the parser reports; it never formats the envelope. `ATENA_KEYWORDS` / `suggest()` available if a keyword-typo hint helps (optional for the parser).
- `src/atena/lexer.py` — the upstream producer; the parser consumes its output. Already drains open blocks at EOF and emits a trailing `NEWLINE`/`EOF`, so the parser's `expect(DEDENT)`/EOF paths are uniform.

### Error voice the parser MUST match (locked Phase 0/1 contracts)
- `.planning/phases/00-diagnostics-spine-data-contracts/00-CONTEXT.md` — error voice **D-01** ("Plain & kind"), **D-03** ("problem + guidance when clear"); the `<specifics>` exemplars are the canonical tone. Also **D-06** (case-only "Did you mean?") — the boundary that owns capitalized `True`/`False` (see D-05).
- `.planning/phases/01-lexer/01-CONTEXT.md` — the teaching off-ramp pattern (**D-01…D-04**) the parser-level redirects extend (tailored for a known set, generic fallback, collected + recover-and-continue, guide-don't-just-describe).

**No standalone reference-spec file exists in the repo** — the "reference spec" named in `PROJECT.md` is captured through the four research docs above + the locked code contracts. The `ask` grammar (D-01/D-02) and the redirect set (D-04/D-05) were decided in this discussion because they were not pinned elsewhere; confirm against the user's source spec if it later surfaces.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/atena/ast_nodes.py`** — the exact output contract; the parser constructs these nodes. Mutable dataclasses give free `__eq__`/`__repr__`, so parser tests assert `produced_node == expected_node` literals (`ARCHITECTURE.md` Pattern 8). Attach `line`/`source_line` from the triggering token at construction.
- **`src/atena/tokens.py`** — the input contract; `TokenType` drives statement dispatch and the Pratt operator table (operator tokens carry their `value`, e.g. `"+"`, `"=="`). `KEYWORDS` distinguishes keyword statements from identifier-led assignments/calls.
- **`src/atena/errors.py`** — inject the shared `ErrorCollector` into the `Parser` constructor (never global); report every syntax error / redirect via `add(line, message, source_line)`.
- **`tests/test_lexer.py`, `tests/test_tokens.py`** — show the construction/usage conventions and three-test-layer style to mirror in a new `tests/test_parser.py` (golden AST snapshots + error-path tests asserting exact message / count / line order).

### Established Patterns
- **ErrorCollector is injected, never global** — `Parser(tokens, errors)` per the Phase-0/ARCHITECTURE boundary.
- **Pure data modules stay dependency-free** — `tokens.py`/`ast_nodes.py` import nothing sibling; `parser.py` imports `tokens` + `ast_nodes` + `errors` only.
- **`errors.py` owns the `Error on line {N}: … → {source}` format** — the parser supplies only the plain-English `message`.
- **TDD per PROJECT.md** — failing test first, commit after each task, work on `feat/parser` (never `main`). Build the happy-path parser first, then add synchronization recovery before declaring the phase green (recovery is a sub-feature with its own test surface — easy to defer and regret).

### Integration Points
- **Lexer → Parser (contract A):** a fully-materialized `list[Token]` with balanced INDENT/DEDENT and a trailing EOF — the parser peeks/lookaheads freely.
- **Parser → Analyzer (contract B):** the same `Program` object handed forward and mutated in place (Phase 3 sets `index_converted`, injects `str()`, etc.). The parser must leave `IndexAccess.index_converted = False`.
- **Parser → ErrorCollector:** the cross-cutting injection point; the Phase-5 driver inspects `is_empty()` between phases and gates codegen.
- **`src/atena/parser.py` and `tests/test_parser.py` do not exist yet** — Phase 2 creates them. `pipeline.py` wiring is Phase 5, not here.

</code_context>

<specifics>
## Specific Ideas

Draft message exemplars surfaced during discussion — **starting drafts**, to be refined into the exact Phase-0 voice during planning/implementation (match `00-CONTEXT.md` `<specifics>` for tone). All guide toward the v1.0 fix:

- `ask` misused (not an assignment RHS): `ask needs to save its answer into a name — try: answer = ask "What is your name?".`
- `def` redirect: `Atena uses "function", not "def" — try: function greet(name).`
- `elif` redirect: `Atena doesn't have elif — use a nested if/else inside the else.`
- `for` redirect: `Atena loops with "repeat N times" or "while" — there's no "for" loop.`
- `class` redirect: `Atena doesn't have classes — it's for step-by-step logic, not objects.`
- `import` redirect: `An Atena program is a single file — there's nothing to import.`
- `==` used as assignment: `Did you mean "x = 5"? Use one "=" to save a value, and "==" only to compare two things.`
- Top-level `return`: `"return" only works inside a function.`
- Unclosed paren (generic-but-guided): `I reached the end of the line still waiting for a ")".`
- `repeat` missing `times`: `"repeat" needs the word "times" — try: repeat 5 times.`
- Generic fallback (no clear intent): `I didn't expect "<token>" here.`

These are guidance drafts, not locked strings — the *decisions* (assignment-style `ask`, RHS-only, the curated redirect set, structural-vs-name-shaped boundary) are locked; exact wording is Claude's discretion within the Phase-0 voice.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

Two items are **cross-phase boundaries, not deferrals:** (1) redirecting name-shaped Python literals/builtins (`True`/`False`/`None`, `print`/`input`/`len`) belongs to the **Phase-3 analyzer** (undefined-name + case-only "Did you mean?"), by design (D-05) — not a dropped idea. (2) The two unpicked gray areas (syntax-error guidance specificity; recovery aggressiveness on a broken compound block) are **in scope for Phase 2** but left to Claude's discretion under the locked voice + research recovery design (see `<decisions>` Claude's Discretion), not deferred to a later phase.

</deferred>

---

*Phase: 2-Parser*
*Context gathered: 2026-06-14*
