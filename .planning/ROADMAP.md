# Roadmap: Atena Language

## Overview

Atena is a teaching transpiler (Atena → Python 3) built as a single-pass pipeline. The journey runs in forced build order, because each phase is the literal input contract for the next: a shared diagnostics spine is established first (Phase 0), then source becomes tokens (Lexer), tokens become an AST (Parser), the AST is enriched with every semantic decision (Analyzer), the analyzed tree becomes runnable Python (Generator), the four phases are wired under a CLI that runs/builds programs without ever leaking a Python traceback (Runtime), and finally the transpiler is packaged and wrapped in a concept-ladder curriculum and getting-started docs so a complete non-programmer can install it and learn (Packaging & Curriculum). The product's core value — plain-English errors, never a Python stack trace, all errors collected in one run — is not any single phase; it is the cross-cutting spine built in Phase 0 and exercised in every phase after. No phase advances until it is 100% green across three test layers: golden snapshots, execution tests (run the generated Python), and error-path tests (assert exact message, count, and line order).

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 0: Diagnostics Spine & Data Contracts** - Shared ErrorCollector, exact error format, position-bearing Token/AST contracts, stub CLI (completed 2026-06-13)
- [x] **Phase 1: Lexer** - Source → balanced token stream with INDENT/DEDENT, blank/comment skipping, tab-space policy (completed 2026-06-13)
- [x] **Phase 2: Parser** - Token stream → AST honoring the precedence ladder, with syntax-error recovery (completed 2026-06-14)
- [ ] **Phase 3: Semantic Analyzer** - Coercion injection, 1→0 index rewrite, undefined/arity checks — owns every semantic decision
- [ ] **Phase 4: Code Generator** - Analyzed AST → valid, runnable Python 3, emitted verbatim, with `ast.parse()` self-check
- [ ] **Phase 5: CLI Runtime & Pipeline Integration** - `atena run` / `atena build` wired end-to-end with plain-English runtime errors
- [ ] **Phase 6: Packaging & Curriculum** - Pip-installable entry point, concept-ladder examples, getting-started README

## Phase Details

### Phase 0: Diagnostics Spine & Data Contracts

**Goal**: The cross-cutting diagnostics spine and inter-phase data contracts exist, so every later phase plugs into one shared error system and source positions are baked into the data model from day one.
**Depends on**: Nothing (first phase)
**Requirements**: DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05, DIAG-06
**Success Criteria** (what must be TRUE):

  1. Given a list of collected errors, the reporter prints each as `Error on line {N}: {plain English}` followed by `→ {offending source line}`, sorted by line number, with no Python jargon ("token", "AST", "DEDENT", "arity", "NoneType") in any message.
  2. A run that collects three errors on different lines reports all three, ordered by line, instead of stopping at the first.
  3. A long collected-error list is capped with a trailing "…and N more", and duplicate errors sharing a line and message are collapsed to one.
  4. Given a known symbol set, an unknown-name error appends a "Did you mean …?" suggestion for the closest known name, and error text reads in a first-person, encouraging voice.
  5. The `Token` and AST node data types carry a line number and the offending source-line text, and any uncaught internal error is converted to a plain-English message — a raw Python traceback never reaches the user.

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 00-01-PLAN.md — Project skeleton: pyproject.toml, src/atena/ layout, stub modules, pytest config

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 00-02-PLAN.md — ErrorCollector core: add/is_empty/report, format template, dedup, sort, cap
- [x] 00-03-PLAN.md — Token + AST node data contracts: TokenType enum, Token dataclass, 22 AST node dataclasses

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 00-04-PLAN.md — Suggestion engine: suggest() with difflib fuzzy matching and case-only detection

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 00-05-PLAN.md — Stub CLI + internal-error fallback: argparse, file-error handling, no-traceback promise

### Phase 1: Lexer

**Goal**: Atena source text is tokenized into a correct, balanced token stream that downstream phases can consume, with the off-side-rule edge cases handled exactly.
**Depends on**: Phase 0
**Requirements**: LEX-01, LEX-02, LEX-03, LEX-04, LEX-05, LEX-06, LEX-07, LEX-08
**Success Criteria** (what must be TRUE):

  1. Lexing a nested-block program produces a balanced INDENT/DEDENT token stream (every INDENT has a matching DEDENT), with all open blocks drained at end of file even when the file ends mid-block or without a trailing newline.
  2. Indented blank lines and deeply-indented comment-only lines produce no tokens and do not change the parse of surrounding code (the indent stack is untouched).
  3. A staircase-dedent file (indent 4, then 8, then dedent to 6) reports a plain-English "indentation doesn't match any open block" error, and a file mixing tabs and spaces reports a plain-English "don't mix tabs and spaces" error.
  4. Every token is stamped with its line number and source-line text; `=` and `==` are distinguished by maximal munch; all operators, comparisons, and the full keyword set (show, ask, if, else, while, repeat, times, and, or, not, function, return, add, to, remove, from, length, true, false) are recognized.
  5. An unterminated double-quoted string or an unexpected character produces a plain-English error, never a Python exception.

**Plans**: 3 plans

Plans:
**Wave 0** *(TDD RED — must run first)*

- [x] 01-01-PLAN.md — TDD RED: all 28 test_lexer.py stubs + Lexer stub (imports succeed, all tests fail)

**Wave 1** *(blocked on Wave 0 completion)*

- [x] 01-02-PLAN.md — Core character scanner: identifiers/keywords, strings, numbers, operators, maximal-munch = vs ==, off-ramps for decimal/single-quote/colon/semicolon (LEX-01/05/06/07/08 GREEN)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-03-PLAN.md — Indentation engine: INDENT/DEDENT/NEWLINE, blank/comment skip, uniform-step validation, EOF drain (LEX-02/03/04 GREEN — all 28 tests GREEN)

### Phase 2: Parser

**Goal**: The token stream is turned into a complete Program AST that honors the spec's operator-precedence ladder, with multiple syntax errors collected in one run and no hangs.
**Depends on**: Phase 1
**Requirements**: PARSE-01, PARSE-02, PARSE-03, PARSE-04, PARSE-05, PARSE-06
**Success Criteria** (what must be TRUE):

  1. Parsing the golden program produces a complete AST using the defined node types, with indentation-delimited blocks (if/else, while, repeat, function bodies) nested to arbitrary depth.
  2. Arithmetic and logical precedence/associativity are correct: `2 + 3 * 4` parses as `2 + (3 * 4)`, `10 - 3 - 2` left-associates, unary `-5` and `a - -b` parse, and postfix chains like `a[1][2]` and `student.name` bind tighter than any binary operator.
  3. Function definitions, `return`, function calls, list literals, dict literals, index access, dot access, and `add … to …` / `remove … from …` statements all parse into their AST nodes.
  4. A program with three malformed statements reports three plain-English syntax errors (one per bad statement, recovered via synchronization on statement boundaries), not one-per-token spam.
  5. Any malformed input terminates without an infinite loop (the parse loop always makes progress) and never surfaces a Python exception.

**Plans**: 5 plans

Plans:
**Wave 1** *(TDD RED gate — must run first)*

- [x] 02-01-PLAN.md — TDD RED: all parser test stubs in tests/test_parser.py + Parser skeleton (imports, constructor, cursor helpers, _ParseError, empty parse() loop)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Pratt expression parser: _BINARY_BP table, _parse_expression (precedence climbing), _parse_unary (nud/led split), _parse_postfix (tight [] . () chain), _parse_primary (all atom types + list/dict literals + length)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Statement dispatcher: show, ask (D-01/D-02), if/else, while, repeat, function_def (fn_depth), return, add…to, remove…from; INDENT/DEDENT block parsing wired

**Wave 4** *(blocked on Wave 3 completion — run in parallel with 02-05)*

- [x] 02-04-PLAN.md — Error recovery + Python-ism redirects: _synchronize(), progress invariant backstop, all D-04 redirects (def/elif/for/class/import/==-slip/top-level-return)
- [x] 02-05-PLAN.md — Integration tests: golden program parse, pitfall coverage (unary-vs-binary, postfix-in-expression, deep nesting, valid-after-errors, error-count cap)

### Phase 3: Semantic Analyzer

**Goal**: The AST is enriched in place with every semantic decision — coercion, index rewrite, scope and arity checks — so the generator can later emit verbatim and never re-derive anything.
**Depends on**: Phase 2
**Requirements**: SEM-01, SEM-02, SEM-03, SEM-04, SEM-05, SEM-06, SEM-07
**Success Criteria** (what must be TRUE):

  1. `str()` coercion is injected bottom-up so `"a" + 1 + 2` is analyzed to yield `"a12"` and `1 + "x"` wraps the `1`, while `number + number` and `string + string` are left untouched; a disallowed `+` combination produces a plain-English "Cannot combine [type] and [type]" error instead of a runtime crash.
  2. A literal `items[1]` is rewritten to `items[0]` exactly once (idempotent), nested `grid[2][3]` becomes `grid[1][2]`, and a literal `items[0]` or a literal negative index produces "Lists in Atena start at 1, not 0."
  3. A variable index (`items[i]`) is routed through the runtime index helper rather than a bare `[i - 1]`, so at runtime an index below 1 errors instead of silently wrapping to Python's negative-index behavior.
  4. Using an undefined variable produces a plain-English error naming it (e.g. `I don't know what "xyz" is.`), and the symbol is poisoned so later uses don't re-report — one mistake yields one error.
  5. Calling a function before it is defined (no hoisting) errors at analysis time, and a call with the wrong number of arguments errors with a human-terms arity message (e.g. `"greet" expects 1 value, but you gave 2.`).

**Plans**: 3 plans

Plans:
**Wave 1** *(TDD RED gate — must run first)*

- [x] 03-01-PLAN.md — TDD RED: SemanticAnalyzer skeleton + all 25+ test_analyzer.py stubs (imports succeed, all tests fail)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 03-02-PLAN.md — Expression semantics: _COERCE_TABLE, type inference, str() coercion injection, _atena_concat routing, 1→0 index rewrite, literal-bounds errors, _atena_index helper (SEM-01..SEM-05 GREEN)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 03-03-PLAN.md — Scope + arity: visit_Assign/Ask registration, visit_Identifier undefined detection + poisoning + D-08 outer-var message, visit_FunctionDef push/pop, visit_FunctionCall no-hoist + arity (SEM-06..SEM-07 GREEN — all tests GREEN)

### Phase 4: Code Generator

**Goal**: The fully analyzed AST is translated into valid, readable, runnable Python 3 — emitted verbatim from the analyzed tree, gated on zero errors, and self-checked.
**Depends on**: Phase 3
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06
**Success Criteria** (what must be TRUE):

  1. The generator reproduces the spec's golden `school.atena` exactly as its expected Python output, and the generated Python *executes* to the expected program output (execution test, not just text match).
  2. Core constructs map correctly (`show`→`print`, `ask`→`input`, `repeat N times`→`for _<unique> in range(N)`, `while`, `if`/`else` with colons, `true`/`false`→`True`/`False`, `and`/`or`/`not`) and list/dict operations map correctly (`add`→`.append`, `remove`→`.remove`, `length`→`len`, `{name = "Ana"}`→`{"name": "Ana"}`, `student.name` read and `student.grade = 10` write both as subscript).
  3. The generator emits indices and coercions verbatim from the analyzed tree and never re-transforms them — a nested `grid[2][3]` is not double-shifted, and a number-only `x + 1` is not str()-wrapped.
  4. Generated Python is correctly indented, uses a unique loop variable per nested `repeat`, and mangles Atena identifiers that collide with Python keywords (`class`, `import`) so the output still parses.
  5. Every generated program passes an internal `ast.parse()` self-check, and the generator emits no Python at all when any error was collected upstream.

**Plans**: TBD

### Phase 5: CLI Runtime & Pipeline Integration

**Goal**: The four phases are wired under a driver and a two-verb CLI so a learner can run or build a program, and runtime errors are translated to plain English — the no-stack-trace promise holds end-to-end.
**Depends on**: Phase 4
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):

  1. `atena run examples/school.atena` transpiles and executes the program, printing the expected output to the terminal.
  2. `atena build file.atena` writes/prints the generated Python 3 without executing it, and a `--show` (or `atena build`) reveals the generated Python so learners can connect Atena constructs to real Python.
  3. When transpilation fails, both `run` and `build` print the collected Atena errors (never a Python traceback) and exit non-zero.
  4. A runtime error during `atena run` (e.g. an out-of-range index) is translated to a plain-English Atena message with the Atena line number, never a Python traceback.
  5. A missing or unreadable `.atena` file produces a friendly plain-English message, not a Python `FileNotFoundError` traceback.

**Plans**: TBD

### Phase 6: Packaging & Curriculum

**Goal**: The transpiler ships as a real, learnable product — pip-installable, with a concept-ladder of example programs and a getting-started guide — so a complete non-programmer can install it and start learning.
**Depends on**: Phase 5
**Requirements**: PKG-01, DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):

  1. `pip install` (from the repo) exposes a working `atena` console entry point, built from a `pyproject.toml` + `src/` layout with zero runtime dependencies.
  2. `examples/` contains a concept-ladder of `.atena` programs (I/O → variables → conditionals → loops → functions → lists → dicts), each of which runs to completion via `atena run`, including the golden `school.atena`.
  3. A getting-started README explains installation, `atena run` / `atena build`, and the language basics, and following it end-to-end gets a new user from install to running their first program.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 0 → 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Diagnostics Spine & Data Contracts | 5/5 | Complete   | 2026-06-13 |
| 1. Lexer | 3/3 | Complete   | 2026-06-13 |
| 2. Parser | 5/5 | Complete   | 2026-06-14 |
| 3. Semantic Analyzer | 1/3 | In Progress|  |
| 4. Code Generator | 0/TBD | Not started | - |
| 5. CLI Runtime & Pipeline Integration | 0/TBD | Not started | - |
| 6. Packaging & Curriculum | 0/TBD | Not started | - |
