# Architecture Research

**Domain:** Single-pass teaching transpiler (Atena → Python 3), four sequential phases
**Researched:** 2026-06-13
**Confidence:** HIGH

This is a textbook compiler front-end + trivial back-end. The architecture is fixed (Lexer → Parser → Semantic Analyzer → Code Generator); the research question is *how to structure each phase well* and *what the inter-phase contracts are*. Every recommendation below maps to a classic, well-understood pattern (CPython's own tokenizer algorithm, recursive-descent + Pratt expression parsing, the visitor/tree-walk pattern), adapted to Atena's deliberate simplifications.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLI / Driver (pipeline.py)                     │
│   atena run file.atena  │  atena build file.atena                      │
│   reads source → runs phases in order → owns the ErrorCollector        │
└───────────────┬──────────────────────────────────────────────────────┘
                │  source string + filename
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 1: LEXER                                                        │
│  ┌──────────────┐   indentation stack   ┌─────────────────────────┐   │
│  │ char scanner │ ───────────────────►  │ INDENT/DEDENT/NEWLINE   │   │
│  └──────────────┘                       │ emitter                 │   │
│  consumes: source text                  └─────────────────────────┘   │
│  produces: List[Token]  (each carries line, col, source-line text)    │
└───────────────┬──────────────────────────────────────────────────────┘
                │  List[Token]
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 2: PARSER (recursive descent + Pratt expressions)              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐   │
│  │ statement    │   │ block parser │   │ Pratt expression parser  │   │
│  │ dispatch     │   │ INDENT…DEDENT│   │ (precedence ladder)      │   │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘   │
│  error recovery: synchronize on NEWLINE / DEDENT                      │
│  consumes: List[Token]                                                │
│  produces: AST (Program root) — may be partial if errors collected    │
└───────────────┬──────────────────────────────────────────────────────┘
                │  AST
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 3: SEMANTIC ANALYZER (AST → annotated/rewritten AST)           │
│  ┌────────────┐ ┌─────────────┐ ┌────────────┐ ┌──────────────────┐  │
│  │ scope /    │ │ coercion    │ │ 1→0 index  │ │ arity / defined- │  │
│  │ undefined  │ │ injection   │ │ rewrite    │ │ before-called    │  │
│  └────────────┘ └─────────────┘ └────────────┘ └──────────────────┘  │
│  consumes: AST                                                        │
│  produces: same AST, mutated in place (coercions, index offsets,     │
│            inferred type tags) — "analyzed AST"                        │
└───────────────┬──────────────────────────────────────────────────────┘
                │  analyzed AST  (ONLY if ErrorCollector is empty)
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 4: CODE GENERATOR (tree-walk → Python 3 string)               │
│  visitor over AST, tracks indentation depth, applies spec mapping     │
│  consumes: analyzed AST                                               │
│  produces: Python 3 source string                                     │
└──────────────────────────────────────────────────────────────────────┘
                │
                ▼
        run: exec the string  │  build: write .py to disk

  ┌─────────────────────────────────────────────────────────────────┐
  │ ErrorCollector  — shared, threaded through ALL phases            │
  │ phases append (line, message, source_line); never raise to user  │
  │ driver checks .is_empty() between phases to decide whether to     │
  │ continue; codegen runs only when zero errors.                     │
  └─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Driver / pipeline** | Read file, instantiate `ErrorCollector`, run phases in order, gate on error count, print errors or emit/run Python | A `transpile(source, filename) -> str | None` function + a thin `argparse` CLI |
| **Lexer** | Char-by-char scan → flat token list; owns the indentation stack and INDENT/DEDENT/NEWLINE emission; skips blank/comment-only lines; classifies keywords vs identifiers; distinguishes `=` from `==` | A `Lexer` class with a position cursor and an `indent_stack: list[int]` |
| **Token** | Carry type, literal value, **line number, column, and the full source-line text** for error messages | A frozen dataclass / namedtuple |
| **Parser** | Token list → AST; recursive descent for statements/blocks, Pratt/precedence-climbing for expressions; error recovery via synchronization | A `Parser` class with `current`/`peek`/`advance`/`expect`/`match` helpers |
| **AST nodes** | Typed, position-bearing tree node-set | Small dataclasses, one per node kind, each with `line` |
| **Semantic Analyzer** | Walk AST, populate a flat global symbol table, inject `str()` coercion, rewrite 1-indexed access to 0-indexed, flag undefined vars, check arity with no hoisting | A visitor that mutates the AST in place and reads/writes `ErrorCollector` |
| **Code Generator** | Tree-walk the analyzed AST, emit indented Python, track indent depth | A visitor returning strings (or appending to a line buffer) |
| **ErrorCollector** | Accumulate `(line, message, source_line)` records across the whole run; format them as `Error on line {N}: ... → {source}` | A class with `add(...)`, `is_empty()`, `report()` |

---

## Recommended Project Structure

```
atena/
├── __init__.py
├── __main__.py            # enables `python -m atena`
├── cli.py                 # argparse: `run` / `build` subcommands → calls pipeline
├── pipeline.py            # transpile(source, filename) -> str | None; owns phase ordering + gating
├── errors.py             # ErrorCollector, error formatting (the ONLY place the message format lives)
├── tokens.py             # TokenType enum, Token dataclass, KEYWORDS map
├── lexer.py              # Lexer: source string -> list[Token]
├── ast_nodes.py          # all AST node dataclasses (Program, Assign, If, BinOp, ...)
├── parser.py             # Parser: list[Token] -> Program (recursive descent + Pratt)
├── analyzer.py           # SemanticAnalyzer: Program -> Program (mutated) + errors
├── codegen.py            # CodeGenerator: Program -> python source string
└── builtins_map.py       # optional: spec mapping table (show→print, ask→input, ...) if large
tests/
├── test_lexer.py
├── test_parser.py
├── test_analyzer.py
├── test_codegen.py
├── test_errors.py
├── test_pipeline.py      # end-to-end
└── fixtures/
    ├── school.atena       # the golden example from the spec
    └── school.expected.py # its expected Python output (canonical integration assertion)
examples/                  # teaching curriculum (.atena programs)
```

### Structure Rationale

- **One module per phase** mirrors the four-phase contract exactly and keeps the TDD "100% green before advancing" gate clean — each phase has its own test file with no cross-contamination.
- **`errors.py` is the single source of truth for the message format.** Every phase imports the same `ErrorCollector`; the `Error on line {N}: ... → {source}` template is written once. This is the most important boundary: the product's core value ("never a Python stack trace") lives here.
- **`tokens.py` and `ast_nodes.py` are pure data** with no logic. They are the inter-phase *contracts* in code form. Keeping them dependency-free means the lexer test can construct tokens and the parser test can construct expected ASTs without importing the other phases.
- **`pipeline.py` separate from `cli.py`** so the whole transpiler is callable as a plain function in tests and from both `run` and `build` without going through `argparse`.
- **`fixtures/school.atena` + `.expected.py`** make the golden example a real, diffable test rather than prose.

---

## Architectural Patterns

### Pattern 1: Indentation stack for INDENT/DEDENT (CPython tokenizer style)

**What:** The lexer keeps a stack of indentation widths, initialized to `[0]`. At the **start of each logical (non-blank, non-comment) line**, measure leading whitespace width and compare to the stack top:
- **equal** → emit nothing
- **greater** → push the new width, emit one `INDENT`
- **less** → pop every width greater than the new one, emitting one `DEDENT` per pop; the new width **must equal** a width left on the stack, otherwise it is an indentation error ("inconsistent dedent")

A `NEWLINE` token terminates each logical line. At end-of-file, emit a `DEDENT` for every width still on the stack above `0`. This is exactly CPython's documented algorithm (verified against the Python language reference).

**When to use:** Always, for any off-side-rule (indentation-delimited) language. Do not try to track depth with a single integer — you cannot detect mismatched dedents that way.

**Trade-offs:** Correct and standard. The only subtlety is *what counts as a column* (see the tabs/spaces note below).

**Example:**
```python
# in Lexer, at the start of each logical line:
def handle_indentation(self, width: int, line_no: int, source_line: str):
    top = self.indent_stack[-1]
    if width > top:
        self.indent_stack.append(width)
        self.emit(TokenType.INDENT, line_no, source_line)
    elif width < top:
        while self.indent_stack[-1] > width:
            self.indent_stack.pop()
            self.emit(TokenType.DEDENT, line_no, source_line)
        if self.indent_stack[-1] != width:
            self.errors.add(line_no, "This line's indentation doesn't match "
                            "any outer block", source_line)
    # width == top → no token
```

### Pattern 2: "Consistent tabs OR spaces, not mixed" — detect once, measure simply

**What:** Atena's constraint is *simpler* than CPython's (CPython allows mixing as long as it's unambiguous; Atena forbids mixing outright per PROJECT.md). The clean implementation: on the **first** indented line of the file, record which character (`\t` or space) was used as the indent unit. On every subsequent line's leading whitespace, if the *other* character appears, emit a plain-English error. Because only one whitespace char is ever legal in a given file, "indentation width" can be a simple **character count** — you never have to resolve the worth-of-a-tab question that complicates CPython.

**When to use:** Exactly this language. The simplification is deliberate and pedagogical.

**Trade-offs:** Rejects files Python would accept, but that is the point — beginners should not learn the tab-width rabbit hole. Detection is O(1) per line.

**Example:**
```python
# first indented line sets the unit; later mixing is an error
unit = self.indent_char  # '\t' or ' ', or None until first indent seen
if ' ' in leading and '\t' in leading:
    self.errors.add(line_no, "Don't mix tabs and spaces for indentation "
                    "— pick one and use it everywhere", source_line)
```

### Pattern 3: Skip blank and comment-only lines (no NEWLINE)

**What:** A line that is empty, all-whitespace, or whitespace-then-comment produces **no tokens at all** — no `NEWLINE`, no `INDENT`, no `DEDENT`. The indentation stack is untouched. This matches CPython exactly (verified) and is what makes blank lines inside a block harmless and comments free-floating. Implementation: after consuming leading whitespace, peek; if at end-of-line or at a comment marker, consume to end-of-line and `continue` *without* running `handle_indentation` or emitting `NEWLINE`.

**When to use:** Always. Getting this wrong (emitting NEWLINE/DEDENT for a blank line) is the #1 indentation lexer bug.

**Trade-offs:** None.

### Pattern 4: Maximal-munch + lookahead for `=` vs `==`

**What:** When the scanner sees `=`, it must peek at the next character. If it is another `=`, consume both and emit `EQ` (comparison); otherwise emit `ASSIGN`. This "longest match wins" rule generalizes to any multi-char operator (`!=`, `<=`, `>=` if present). Single-character lookahead is sufficient for Atena's operator set.

**Example:**
```python
if c == '=':
    if self.peek() == '=':
        self.advance(); self.emit(TokenType.EQ, ...)      # ==
    else:
        self.emit(TokenType.ASSIGN, ...)                  # =
```

### Pattern 5: Recursive descent for statements, Pratt/precedence-climbing for expressions

**What:** Two complementary techniques in one parser:
- **Statements** are parsed by recursive descent: a `statement()` dispatcher peeks the first token and calls a dedicated method (`parse_if`, `parse_while`, `parse_repeat`, `parse_function_def`, `parse_show`, `parse_ask`, `parse_return`, `parse_list_op`, or falls through to assignment / expression statement). Each keyword statement has exactly one method — readable and directly testable.
- **Expressions** use **Pratt parsing (precedence climbing)** to encode the operator ladder without one grammar method per level. The ladder, lowest binding to highest:
  `or` → `and` → `not` (unary) → comparison (`==`, `<`, `>`, …) → `+`/`-` → `*`/`/` → unary minus → postfix (`[]`, `.`, `()`).

  Each binary operator gets a binding power; postfix `[]`/`.`/`()` are handled as a tight postfix loop after a primary. This collapses what would be ~8 mutually-recursive methods into one precedence-driven loop, which is easier to keep correct and to extend.

**When to use:** Recursive descent is the default for any hand-written parser; Pratt is the standard answer for non-trivial expression precedence. For a teaching project the readability win of Pratt over a deep `parse_or → parse_and → … → parse_primary` chain is real but modest — either is acceptable. **Recommendation: Pratt**, because the precedence table doubles as living documentation of the spec's ladder.

**Trade-offs:** Pratt has a slightly higher initial conceptual cost; the precedence-table-of-methods approach is more verbose but arguably more obvious to a first-time reader. Both are O(n).

**Example (Pratt core):**
```python
PRECEDENCE = {  # higher = binds tighter
    'or': 1, 'and': 2,
    '==': 3, '!=': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
    '+': 4, '-': 4,
    '*': 5, '/': 5,
}

def parse_expression(self, min_bp=0):
    left = self.parse_unary()                 # handles `not`, unary `-`, then postfix
    while (bp := PRECEDENCE.get(self.current.value, 0)) > min_bp:
        op = self.advance()
        right = self.parse_expression(bp)     # left-assoc: same bp on the right
        left = BinOp(op.value, left, right, line=op.line)
    return left
```

### Pattern 6: Block parsing consumes INDENT … DEDENT

**What:** A block is the sequence of statements between an `INDENT` and its matching `DEDENT`. Every compound statement (`if`, `while`, `repeat`, `function`) parses its header, expects a `NEWLINE`, then calls `parse_block()`, which: `expect(INDENT)`, loops `parse_statement()` until it sees `DEDENT`, then `expect(DEDENT)`. Because the lexer already balanced INDENT/DEDENT, the parser never counts columns — it only consumes the structural tokens. This is the clean separation that makes the off-side rule tractable.

**Example:**
```python
def parse_block(self) -> list[Stmt]:
    self.expect(TokenType.INDENT)
    body = []
    while not self.check(TokenType.DEDENT) and not self.at_end():
        stmt = self.parse_statement()
        if stmt is not None:
            body.append(stmt)
    self.expect(TokenType.DEDENT)
    return body
```

### Pattern 7: Error recovery via synchronization (collect, don't fail-fast)

**What:** When `parse_statement()` hits an unexpected token, the parser **records an error** in the `ErrorCollector`, then **synchronizes**: discard tokens until it reaches a safe restart point — a `NEWLINE` or a `DEDENT` (the statement/block boundaries) — and resume. This is classic panic-mode recovery (verified against the Dragon Book / standard parser literature), with NEWLINE/DEDENT playing the role that `;`/`}` play in C-like languages. The benefit is exactly the product requirement: one run surfaces every error, not just the first.

**When to use:** Required here — "collect all errors" is a Key Decision in PROJECT.md.

**Trade-offs:** Recovery can occasionally produce a spurious cascade error; synchronizing on the statement boundary (NEWLINE/DEDENT) minimizes this because each statement is re-attempted from a clean slate. The AST returned may be *partial* — that's fine, because the driver will not run later phases if errors exist.

**Example:**
```python
def synchronize(self):
    while not self.at_end():
        if self.previous.type == TokenType.NEWLINE:
            return
        if self.current.type in (TokenType.DEDENT, TokenType.NEWLINE):
            return
        self.advance()

def parse_statement(self):
    try:
        return self.dispatch_statement()
    except ParseError as e:
        self.errors.add(e.line, e.message, e.source_line)
        self.synchronize()
        return None   # caller filters out None
```
A local `ParseError` exception is raised by `expect()` and caught *only* at the statement boundary — it is an internal control-flow tool, never surfaced to the user.

### Pattern 8: AST as position-bearing dataclasses

**What:** One small dataclass per node kind, each with a `line: int` field (copied from the token that introduced it) so any phase can produce a located error. The node-set the spec needs:

```
Program(statements)
Assign(name, value, line)                Show(value, line)
Ask(prompt, target, line)                If(condition, then_body, else_body, line)
While(condition, body, line)             Repeat(count, body, line)
FunctionDef(name, params, body, line)    Return(value, line)
FunctionCall(name, args, line)
BinOp(op, left, right, line)             UnaryOp(op, operand, line)
ListLiteral(elements, line)              DictLiteral(pairs, line)
IndexAccess(target, index, line)         DotAccess(target, name, line)
ListAdd(target, value, line)             ListRemove(target, value, line)
Identifier(name, line)                   NumberLiteral(value, line)
StringLiteral(value, line)               BoolLiteral(value, line)
```

**When to use:** Always. `@dataclass` gives free `__eq__` and `__repr__`, which makes parser tests trivial: assert the produced node equals the expected node literal. Attach `line` at construction from the triggering token (`op.line`, `keyword.line`).

**Trade-offs:** Slightly more boilerplate than a generic tuple-based tree, but the type names make the codegen visitor and the tests self-documenting. Worth it.

### Pattern 9: Visitor / tree-walk for analyzer and codegen

**What:** Both phase 3 and phase 4 are tree-walks. Use the `visit_<NodeType>` dispatch convention (one method per node kind, dispatched by `type(node).__name__`). The analyzer's visitors **mutate** nodes (set a `coerce=True` flag, replace a 1-based index with a 0-based one, tag inferred types) and read/write the symbol table and `ErrorCollector`. The codegen's visitors **return strings** (or append to a line buffer) and read the (now-annotated) nodes.

**When to use:** The standard pattern for both passes. Keeps each node's handling in one obvious place.

**Trade-offs:** None meaningful at this size.

### Pattern 10: Coercion injection without a real type system

**What:** The analyzer needs just enough "type" to decide whether a `+` is string-concatenation needing `str()` wrapping. It does **lightweight, local type inference**, not a type checker:
- Literal nodes have an obvious static type: `StringLiteral`→`str`, `NumberLiteral`→`number`, `BoolLiteral`→`bool`.
- For an `Identifier`, look up the **last assigned** type in the flat symbol table (single global scope, so this is just a dict `name → inferred_type`).
- For a `BinOp('+')`, infer the type of each side recursively. If **either** side is `str`, the result is `str`, and the analyzer flags the non-string side for `str()` wrapping at codegen (`number + number` and `string + string` are left untouched; combinations the spec disallows become a plain-English error).
- Unknown/uninferable operands (e.g., a function-call result) default to a permissive "unknown" type that suppresses false-positive coercion errors — better to under-coerce than to wrongly reject a beginner's program.

This is "abstract interpretation lite": a single forward pass tracking a tiny type lattice (`number`, `str`, `bool`, `list`, `dict`, `unknown`). It deliberately does **not** handle reassignment-changes-type precisely or flow-sensitive narrowing — out of scope and unnecessary for coercion.

**When to use:** Exactly this. A full Hindley-Milner / bidirectional type system is massive overkill for a teaching transpiler whose only typing job is "is this `+` a string concat?".

**Trade-offs:** Can mis-infer when a variable's type changes between assignments; acceptable because the worst case is a missed or extra `str()` wrap, never a crash (Python's own `str()` is forgiving). Document this limitation.

### Pattern 11: 1→0 index rewrite owned by the analyzer

**What:** Atena is 1-indexed; Python is 0-indexed. The analyzer (not the codegen) owns the rewrite so the contract stays clean — codegen emits whatever index the analyzed AST holds. For `IndexAccess`:
- **Literal `0` or a literal negative** → plain-English error ("Lists in Atena start at 1, not 0") and **do not** rewrite.
- **Literal positive `n`** → rewrite the index node to `n-1` in place.
- **Non-literal index** (a variable/expression) → cannot be checked statically; codegen must emit a runtime `- 1` (i.e., emit `expr - 1`). Decide this once and document it: dynamic indices get a `- 1` at runtime; literal indices are folded at analysis time.

**Trade-offs:** Dynamic-index `- 1` injection means a runtime out-of-range still surfaces as a Python error — acceptable for v1.0, or wrap with a guard later. Note this as a phase-4/runtime-friendliness follow-up.

### Pattern 12: No hoisting — defined-before-called arity checks

**What:** Functions are **not** hoisted (PROJECT.md: "no hoisting — defined-before-called"). The analyzer walks statements **in source order**, registering each `FunctionDef` (name → arity) as it encounters it. A `FunctionCall` is checked against the table **as it is reached**: if the name is not yet registered, it is an "undefined function" / "called before defined" error; if registered, arity (argument count vs parameter count) is checked. Same single forward pass that does undefined-variable detection — variables and functions live in (separate compartments of) the flat global symbol table.

**Trade-offs:** Forbids mutual recursion and forward references — intentional, matches the simple mental model. Single-pass, no fixpoint needed.

---

## Data Flow

### Pipeline Flow (the inter-phase contracts)

```
source: str, filename: str
    │
    ▼  Lexer(source, errors).tokenize()
list[Token]                         # contract A: flat token list, INDENT/DEDENT balanced,
    │                               #   every token has line + source_line text
    ▼  Parser(tokens, errors).parse()
Program (AST)                       # contract B: tree of position-bearing nodes;
    │                               #   may be partial if parse errors were collected
    ▼  SemanticAnalyzer(ast, errors).analyze()
Program (analyzed AST)              # contract C: SAME tree, mutated in place —
    │                               #   coercion flags set, indices rewritten, types tagged
    │
    ├──► if errors NOT empty: report all errors, STOP. Never run codegen.
    │
    ▼  CodeGenerator(analyzed_ast).generate()   # only reached when errors.is_empty()
python_source: str                  # contract D: runnable Python 3 text
    │
    ├──► run:   exec(python_source)
    └──► build: write python_source to file.py
```

### The Shared ErrorCollector (cross-cutting)

```
                    ┌──────────────────┐
   Lexer  ─────────►│                  │
   Parser ─────────►│  ErrorCollector  │◄──── single instance created by the driver,
   Analyzer ───────►│  list[ErrorRec]  │      passed into each phase's constructor
                    └────────┬─────────┘
                             │  driver inspects between phases
                             ▼
            is_empty()? ── no ──► report() (formatted plain-English) and halt
                  │ yes
                  ▼  proceed to next phase / codegen
```

- Every phase receives the **same** `ErrorCollector` instance and only ever calls `add(line, message, source_line)`. No phase prints or raises to the user.
- The driver decides flow **between** phases, not inside them. A phase always runs to completion (collecting what it can) so a single run surfaces the maximum number of errors *for that phase*.
- **Gating rule:** lexer and parser errors should both be collected before deciding to stop (a token stream with errors can often still be parsed enough to find more). The analyzer runs on whatever AST exists. **Codegen is the hard gate:** it runs *only* when the collector is empty, because generating Python from a known-broken AST would produce garbage or crash.

### Key Data Flows

1. **Source-position threading (the human-error backbone):** the lexer stamps every `Token` with `line`, `col`, and the **entire source line text**. The parser copies the triggering token's `line` onto each AST node. The analyzer reads `node.line` for its errors. Result: any phase can produce `Error on line {N}: {message} → {source_line}` without re-reading the file. This thread is the single most important architectural detail for the product's core value — design `Token` and the AST base around it first.
2. **In-place AST mutation (phase 3):** the analyzer does not build a new tree; it annotates the existing one (coercion flags, rewritten indices, type tags). This keeps the parser→analyzer→codegen contract to "the same `Program` object, progressively enriched," which is simpler to test (assert on mutated fields) than a parallel IR.
3. **Symbol table lifetime:** built and consumed entirely within the analyzer's single pass; it does not cross a phase boundary. Codegen needs no symbol table because all decisions (coercion, indexing, arity) were resolved upstream.

---

## Suggested Build Order

The phases must be **built** in pipeline order — each is the input contract for the next — and PROJECT.md mandates "one phase at a time, 100% green before advancing." This maps directly onto roadmap phases:

| Build step | Phase | Why this order | Definition of done (the contract it must satisfy) |
|-----------|-------|----------------|---------------------------------------------------|
| 0 | **Error infrastructure + Token/AST data + CLI skeleton** | Everything depends on `ErrorCollector`, `Token`, and the error format. Build the shared spine first so all four phases plug into it. | `ErrorCollector` formats `Error on line {N}: ... → {source}`; `Token` and AST dataclasses exist; `atena run/build` wired to a stub pipeline. |
| 1 | **Lexer** | Produces contract A (tokens). Nothing else can be tested without real tokens. Highest-risk component (INDENT/DEDENT). | Given source, emits a correct token list with balanced INDENT/DEDENT, skipped blank/comment lines, `=`/`==` distinguished, positions stamped. Tab/space-mix errors collected. |
| 2 | **Parser** | Consumes contract A, produces contract B (AST). Cannot exist before tokens. | Given tokens, builds the full AST per the precedence ladder; blocks consume INDENT…DEDENT; multiple syntax errors collected via synchronization. |
| 3 | **Semantic Analyzer** | Consumes contract B, produces contract C (analyzed AST). Needs a complete AST to walk. | Coercion flags injected, 1→0 indices rewritten, undefined vars + arity errors collected; analyzed AST ready. |
| 4 | **Code Generator** | Consumes contract C, produces contract D (Python). Last because it relies on a *fully analyzed* tree and only runs when error-free. | Golden example (`school.atena`) transpiles byte-for-byte to its expected `.py`; runs without a stack trace. |
| 5 | **Pipeline integration + packaging + curriculum** | Ties the four phases together under the driver, then packaging/docs/examples. | End-to-end fixtures pass; `pip install` entry point works; teaching examples run. |

**Critical build-order implications for the roadmap:**
- **Step 0 (error spine + data contracts) is a real phase, not setup.** It is tempting to fold it into the lexer phase, but the `ErrorCollector` and the `Error on line {N}: … → {source}` format are cross-cutting and define the product's core value. Establishing them first prevents each phase from inventing its own error style.
- **The lexer is the highest-risk phase** (INDENT/DEDENT + blank-line skipping + tab/space policy). Flag it for the deepest testing. Off-side-rule bugs are the classic source of "works on my file, breaks on yours."
- **Parser error recovery (synchronization) is a sub-feature with its own test surface** — easy to defer and regret. Build the happy-path parser, then add synchronization before declaring the phase done, because "collect all errors" is a stated requirement.
- **Codegen is low-risk but gated:** it can only be meaningfully tested once the analyzer exists, and its acceptance test is the golden example. Treat the golden `school.atena` → `school.expected.py` pair as the phase-4 (and integration) gate.

---

## Anti-Patterns

### Anti-Pattern 1: Tracking indentation with a single depth counter

**What people do:** Keep one integer `depth` and `+1/-1` it, instead of a stack of widths.
**Why it's wrong:** It cannot detect a dedent that doesn't line up with any open block ("inconsistent dedent"), and it breaks the moment indentation is more than one level deep. You lose the exact errors beginners most need.
**Do this instead:** Use the indentation **stack** (Pattern 1). Pop until you match a width on the stack; "no match" is the error case.

### Anti-Pattern 2: Emitting NEWLINE/INDENT/DEDENT for blank or comment lines

**What people do:** Run indentation logic on every physical line.
**Why it's wrong:** A blank line inside a block, or a comment indented differently, spuriously closes/opens blocks and produces baffling errors. This is the most common off-side-rule bug.
**Do this instead:** Detect blank/comment-only lines *before* touching the stack and skip them entirely (Pattern 3) — exactly as CPython does.

### Anti-Pattern 3: Fail-fast parsing (throwing on the first error)

**What people do:** Raise an exception out of the parser on the first unexpected token.
**Why it's wrong:** Violates the "collect all errors" requirement; a beginner fixes one error, re-runs, finds the next — a frustrating loop.
**Do this instead:** Catch the internal `ParseError` at the statement boundary, record it, synchronize on NEWLINE/DEDENT, continue (Pattern 7).

### Anti-Pattern 4: Putting coercion / indexing logic in the code generator

**What people do:** Decide `str()` wrapping or the `-1` index shift while emitting Python.
**Why it's wrong:** It blurs the phase contracts, duplicates type reasoning, and makes codegen un-testable in isolation. Codegen should be a dumb, faithful translator of an already-decided tree.
**Do this instead:** The analyzer owns *all* semantic decisions and records them on the AST (flags, rewritten indices). Codegen only reads them (Patterns 10–11).

### Anti-Pattern 5: Building a full type system for coercion

**What people do:** Reach for a complete type checker to decide when to inject `str()`.
**Why it's wrong:** Enormous complexity for a binary question ("is this `+` a string concat?"). It will also reject programs beginners legitimately write.
**Do this instead:** Lightweight forward type inference over a tiny lattice, defaulting unknowns to permissive (Pattern 10). Under-coerce rather than over-reject.

### Anti-Pattern 6: Letting a Python exception reach the user

**What people do:** Allow an `IndexError`, `KeyError`, or an internal `assert` to propagate to stdout.
**Why it's wrong:** Directly violates the core value — the learner sees a Python stack trace, the one thing the product promises they never will.
**Do this instead:** The driver wraps the whole pipeline; any uncaught internal error is converted to a generic plain-English "internal error on line N" and the run is still reported through the `ErrorCollector`. Internal `ParseError` is caught at the statement boundary and never escapes.

### Anti-Pattern 7: Running codegen on a tree that had errors

**What people do:** Always run all four phases, then check for errors at the end.
**Why it's wrong:** Codegen on a partial/broken AST crashes or emits nonsense, and the crash may itself leak a stack trace.
**Do this instead:** Hard-gate codegen on `errors.is_empty()` (Data Flow, gating rule). Lex/parse/analyze accumulate; codegen is conditional.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Python runtime (`run`) | `exec(generated_source, namespace)` or write-to-temp + `subprocess` | `exec` is simplest; a subprocess isolates the learner's program and makes its own runtime errors easier to intercept and re-phrase. Prefer subprocess if you later want to catch runtime errors plainly. |
| Filesystem (`build`) | write the generated string to `file.py` next to the source | Trivial; just ensure the output is `exec`-clean (trailing newline, no BOM). |
| `pip` packaging | `pyproject.toml` with a console-script entry point → `atena.cli:main` | Standard-library-only core keeps packaging trivial; the entry point is the only packaging surface. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Lexer ↔ Parser | `list[Token]` (contract A) | One-way, fully materialized list (not a generator) so the parser can peek/lookahead freely. |
| Parser ↔ Analyzer | `Program` AST (contract B) | One-way; the same object is handed forward and mutated. |
| Analyzer ↔ Codegen | analyzed `Program` (contract C) | One-way; codegen treats it as read-only. |
| All phases ↔ ErrorCollector | shared mutable instance | The only cross-cutting, many-to-one dependency. Inject via constructor; never make it a global. |
| Phases ↔ Token/AST data modules | import-only | `tokens.py`/`ast_nodes.py` depend on nothing, so every phase and every test can import them freely. |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| INDENT/DEDENT stack algorithm, blank/comment skipping, tabs/spaces | HIGH | Verified directly against the Python language reference (lexical analysis); Atena's "tabs OR spaces, not mixed" is a documented simplification of CPython's rule. |
| Recursive descent + Pratt expression parsing for the given ladder | HIGH | Standard, well-documented techniques; the precedence ladder maps cleanly onto binding powers. |
| Error recovery via synchronization on statement boundaries | HIGH | Classic panic-mode recovery (Dragon Book); NEWLINE/DEDENT are the natural sync tokens, verified against parser-recovery literature. |
| Phase contracts, build order, error-collector gating | HIGH | Directly implied by PROJECT.md's four-phase + "collect errors" + "codegen only when green" decisions; standard compiler pipeline structure. |
| Lightweight coercion inference (no full type system) | MEDIUM-HIGH | Standard "abstract-interpretation-lite" approach; the only judgment call is the permissive-unknown default, which is a deliberate product-friendliness choice, not a verified fact. |

---

## Sources

- Python Language Reference — Lexical Analysis (INDENT/DEDENT stack algorithm, blank/comment-line handling, tab/space rules): https://docs.python.org/3/reference/lexical_analysis.html — HIGH
- Panic-mode / synchronization error recovery (Dragon Book lineage; restart on statement-boundary tokens): https://www.rose-hulman.edu/class/csse/csse404/schedule/day31/ErrorRecovery.pdf and https://www.geeksforgeeks.org/error-recovery-in-predictive-parsing/ — HIGH
- Resilient recursive-descent parsing (synchronization patterns in hand-written parsers): https://thunderseethe.dev/posts/parser-base/ — MEDIUM
- PROJECT.md (Atena spec: four-phase architecture, coercion rules, 1-indexing, error format, no-hoisting) — authoritative for this project

---
*Architecture research for: teaching transpiler (Atena → Python 3)*
*Researched: 2026-06-13*
