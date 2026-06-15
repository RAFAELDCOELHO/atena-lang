# Requirements: Atena Language

**Defined:** 2026-06-13
**Core Value:** A complete non-programmer can write real algorithmic logic without fighting syntax, and never sees a Python stack trace — only plain-English errors.

## v1 Requirements

Requirements for the initial release. Each maps to roadmap phases.

### Diagnostics & Errors

The cross-cutting spine. Established before the lexer; every phase plugs into it.

- [x] **DIAG-01**: Every error follows the exact format `Error on line {N}: {plain English description}` followed by `→ {offending source line}`
- [x] **DIAG-02**: The transpiler collects all errors in a single run and reports them ordered by line number (error recovery), instead of stopping at the first error
- [x] **DIAG-03**: No Python stack trace or compiler jargon (e.g. "token", "AST", "DEDENT", "arity", "NoneType") ever reaches the user, at compile time or runtime
- [x] **DIAG-04**: Error messages are written in a first-person, encouraging voice
- [x] **DIAG-05**: When a name is unknown, the error suggests the closest known variable or keyword ("Did you mean …?")
- [x] **DIAG-06**: Cascading duplicate errors from a single root cause are suppressed, and a long error list is capped with "…and N more"

### Lexer

- [x] **LEX-01**: Lexer tokenizes source into the defined token types (STRING, NUMBER, IDENTIFIER, OPERATOR, COMPARISON, ASSIGN, LPAREN, RPAREN, LBRACKET, RBRACKET, LBRACE, RBRACE, COMMA, DOT, NEWLINE, INDENT, DEDENT, EOF)
- [x] **LEX-02**: Lexer emits INDENT/DEDENT tokens by tracking indentation level, and drains all open blocks at end of file
- [x] **LEX-03**: Lexer skips blank lines and comment-only lines, emitting no NEWLINE for them
- [x] **LEX-04**: Lexer enforces consistent tabs OR spaces within a file and reports a plain-English error on mixed indentation
- [x] **LEX-05**: Lexer distinguishes ASSIGN (`=`) from COMPARISON (`==`) and recognizes all comparison (`!=`, `>`, `<`, `>=`, `<=`) and arithmetic (`+ - * /`) operators
- [x] **LEX-06**: Lexer recognizes all keywords: show, ask, if, else, while, repeat, times, and, or, not, function, return, add, to, remove, from, length, true, false
- [x] **LEX-07**: Lexer reads double-quoted string literals and integer numbers only, stamping every token with its line number and source-line text
- [x] **LEX-08**: Lexer reports a plain-English error for an unterminated string or an unexpected character

### Parser

- [x] **PARSE-01**: Parser builds a Program AST from the token stream using the defined node types (Program, Assign, Show, Ask, If, While, Repeat, BinOp, UnaryOp, FunctionCall, FunctionDef, Return, ListLiteral, DictLiteral, IndexAccess, DotAccess, ListAdd, ListRemove, Identifier, NumberLiteral, StringLiteral, BoolLiteral)
- [x] **PARSE-02**: Parser honors the full operator-precedence ladder: `or` → `and` → `not` → comparison → `+`/`-` → `*`/`/` → unary `-` → postfix `[]`/`.`/`()`
- [x] **PARSE-03**: Parser parses indentation-delimited blocks (INDENT…DEDENT) for if/else, while, repeat, and function bodies, with arbitrary nesting
- [x] **PARSE-04**: Parser parses function definitions and `return`, function calls, list literals, dict literals, index access, dot access, and `add … to …` / `remove … from …` statements
- [x] **PARSE-05**: Parser recovers from a syntax error by synchronizing on the next statement boundary, so multiple syntax errors are collected in one run
- [x] **PARSE-06**: Parser reports plain-English errors for malformed statements (e.g. a missing parenthesis) and never loops infinitely on an error

### Semantic Analyzer

The analyzer owns every semantic decision; the generator emits verbatim.

- [x] **SEM-01**: Analyzer injects `str()` coercion for `string + number` and `string + boolean`, evaluated bottom-up so coercion is correct across chains (e.g. `"a" + 1 + 2`)
- [x] **SEM-02**: Analyzer reports a plain-English error ("Cannot combine [type] and [type] with +") for disallowed `+` combinations instead of letting them crash at runtime
- [x] **SEM-03**: Analyzer rewrites 1-indexed list access to 0-indexed exactly once (idempotent), including nested indexing (`grid[2][3]` → `grid[1][2]`)
- [x] **SEM-04**: Analyzer reports "Lists in Atena start at 1, not 0." for a literal index of `0`, and rejects literal negative indices
- [x] **SEM-05**: Analyzer routes variable (non-literal) list indices through a runtime helper that errors on index < 1, so no index silently wraps to Python's negative-index behavior
- [x] **SEM-06**: Analyzer detects use of an undefined variable and reports it in plain English (e.g. `I don't know what "xyz" is. Did you forget to create it?`)
- [x] **SEM-07**: Analyzer enforces that functions are defined before they are called (no hoisting) and checks call arity (e.g. `"greet" expects 1 value, but you gave 2.`)

### Code Generator

- [x] **GEN-01**: Generator emits valid, runnable Python 3 for core constructs: `show`→`print`, `ask`→`input`, variables, `repeat N times`→`for _i in range(N):`, `while`, `if`/`else` (with colons), boolean/comparison/arithmetic expressions, `true`/`false`→`True`/`False`, `and`/`or`/`not`
- [x] **GEN-02**: Generator emits list operations (`add`→`.append`, `remove`→`.remove`, `length`→`len`), dict literals (`{name = "Ana"}`→`{"name": "Ana"}`), and dict dot access for both read (`student.name`→`student["name"]`) and write (`student.grade = 10`→`student["grade"] = 10`)
- [x] **GEN-03**: Generator runs only when zero errors were collected; if any error exists, it emits no Python
- [x] **GEN-04**: Generator produces correctly-indented Python, uses a unique loop variable per nested `repeat`, and mangles Atena identifiers that collide with Python keywords
- [x] **GEN-05**: Every generated program passes an internal `ast.parse()` self-check; invalid output is an internal bug surfaced in tests, never shown to the learner
- [x] **GEN-06**: Generator reproduces the spec's golden example (`school.atena`) exactly, matching the expected Python output

### CLI & Runtime

- [x] **CLI-01**: `atena run file.atena` transpiles and then executes the program
- [x] **CLI-02**: `atena build file.atena` writes/prints the generated Python 3 without executing it
- [x] **CLI-03**: `atena run` and `atena build` print collected Atena errors (never Python tracebacks) and exit non-zero when transpilation fails
- [x] **CLI-04**: Runtime errors during `atena run` are translated to plain-English Atena messages with the Atena line number (no Python traceback)
- [x] **CLI-05**: The CLI handles a missing or unreadable `.atena` file with a friendly plain-English message
- [x] **CLI-06**: `atena build` (or a `--show` flag) reveals the generated Python so learners can connect Atena constructs to real Python

### Packaging

- [x] **PKG-01**: The project is pip-installable and exposes an `atena` console entry point (`pyproject.toml`, `src/` layout)

### Curriculum & Docs

- [ ] **DOCS-01**: `examples/` contains a concept-ladder of `.atena` programs (I/O → variables → conditionals → loops → functions → lists → dicts), including the golden `school.atena`
- [ ] **DOCS-02**: A getting-started README explains installation, `atena run` / `atena build`, and the language basics

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Language

- **LANG-V2-01**: `elif` for multi-branch conditionals
- **LANG-V2-02**: Float numbers
- **LANG-V2-03**: String escaping (`\"`, `\n`)
- **LANG-V2-04**: List slicing

### Tooling

- **TOOL-V2-01**: Localized / translated keywords and messages (Hedy-style)
- **TOOL-V2-02**: REPL / interactive mode
- **TOOL-V2-03**: Editor/LSP integration

## Out of Scope

Explicitly excluded from v1.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| `elif` | Use nested if/else; keeps control-flow grammar minimal for learners (deferred to v2) |
| Float numbers | Integers only in v1.0; avoids precision/formatting teaching detours (deferred to v2) |
| String escaping | Double-quoted literals only; reduces lexer complexity (deferred to v2) |
| Negative list indices | Atena is 1-indexed; negatives would confuse the mental model and are a deliberate error |
| List slicing | Beyond foundational logic; not needed for v1.0 |
| Default function parameters | Keeps the function model simple |
| Nested functions / closures | Flat scope only; closures are an advanced concept |
| Classes / OOP | v1.0 teaches procedural logic only |
| Module imports | Single-program model in v1.0 |
| Multi-file programs | One `.atena` file per run |
| REPL / interactive mode | Structurally conflicts with the DEDENT-delimited block model (deferred to v2) |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DIAG-01 | Phase 0 | Complete |
| DIAG-02 | Phase 0 | Complete |
| DIAG-03 | Phase 0 | Complete |
| DIAG-04 | Phase 0 | Complete |
| DIAG-05 | Phase 0 | Complete |
| DIAG-06 | Phase 0 | Complete |
| LEX-01 | Phase 1 | Complete |
| LEX-02 | Phase 1 | Complete |
| LEX-03 | Phase 1 | Complete |
| LEX-04 | Phase 1 | Complete |
| LEX-05 | Phase 1 | Complete |
| LEX-06 | Phase 1 | Complete |
| LEX-07 | Phase 1 | Complete |
| LEX-08 | Phase 1 | Complete |
| PARSE-01 | Phase 2 | Complete |
| PARSE-02 | Phase 2 | Complete |
| PARSE-03 | Phase 2 | Complete |
| PARSE-04 | Phase 2 | Complete |
| PARSE-05 | Phase 2 | Complete |
| PARSE-06 | Phase 2 | Complete |
| SEM-01 | Phase 3 | Complete |
| SEM-02 | Phase 3 | Complete |
| SEM-03 | Phase 3 | Complete |
| SEM-04 | Phase 3 | Complete |
| SEM-05 | Phase 3 | Complete |
| SEM-06 | Phase 3 | Complete |
| SEM-07 | Phase 3 | Complete |
| GEN-01 | Phase 4 | Complete |
| GEN-02 | Phase 4 | Complete |
| GEN-03 | Phase 4 | Complete |
| GEN-04 | Phase 4 | Complete |
| GEN-05 | Phase 4 | Complete |
| GEN-06 | Phase 4 | Complete |
| CLI-01 | Phase 5 | Complete |
| CLI-02 | Phase 5 | Complete |
| CLI-03 | Phase 5 | Complete |
| CLI-04 | Phase 5 | Complete |
| CLI-05 | Phase 5 | Complete |
| CLI-06 | Phase 5 | Complete |
| PKG-01 | Phase 6 | Complete |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 42 total
- Mapped to phases: 42 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after roadmap creation (traceability populated)*
