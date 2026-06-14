# Phase 3: Semantic Analyzer - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 2 (src/atena/analyzer.py, tests/test_analyzer.py)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/atena/analyzer.py` | service (tree-walk pass) | transform (in-place AST mutation) | `src/atena/parser.py` | role-match (both are single-pass, injected-ErrorCollector, dispatch-per-node modules) |
| `tests/test_analyzer.py` | test | batch (run all test layers) | `tests/test_parser.py` | exact (same three-layer structure, same helper/_parse pattern, same assertion style) |

## Pattern Assignments

---

### `src/atena/analyzer.py` (tree-walk transform, in-place AST mutation)

**Analog:** `src/atena/parser.py`

**Imports pattern** (`src/atena/parser.py` lines 1–23):
```python
"""
Semantic Analyzer for the Atena transpiler.

Takes the parser's Program AST (contract B) and enriches it in place,
producing the analyzed AST (contract C) the Phase-4 generator emits
verbatim. Implements a tree-walk (visit_<NodeType> dispatch) that mutates
nodes and reads/writes the shared ErrorCollector. Never raises to the user
and never builds a parallel tree.
"""

from __future__ import annotations

from atena.errors import ErrorCollector, suggest, ATENA_KEYWORDS
from atena.ast_nodes import (
    Program, Assign, Show, Ask, If, While, Repeat,
    FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
    ListLiteral, DictLiteral, IndexAccess, DotAccess,
    ListAdd, ListRemove, Identifier, NumberLiteral,
    StringLiteral, BoolLiteral,
    Node,
)
```

Key rule: `analyzer.py` imports ONLY `atena.errors` + `atena.ast_nodes` + stdlib. It NEVER imports `atena.lexer` or `atena.parser` (matching the dependency-free shape at parser.py lines 14–23: each phase imports only the phases upstream of it in the data contract).

---

**Constructor / injected-ErrorCollector pattern** (`src/atena/parser.py` lines 100–104):
```python
class Parser:
    def __init__(self, tokens: list[Token], errors: ErrorCollector) -> None:
        self._tokens = tokens           # fully-materialised list from the Lexer
        self._errors = errors           # injected — never instantiate internally
        self._pos = 0
        self._fn_depth = 0
```

For the analyzer, mirror this shape:
```python
class SemanticAnalyzer:
    def __init__(self, program: Program, errors: ErrorCollector) -> None:
        self._program = program         # mutated in place (contract B → C)
        self._errors = errors           # injected — never instantiate internally
        # Symbol table: two-level scope (D-07)
        self._globals: dict[str, str] = {}         # name → inferred type
        self._locals: dict[str, str] | None = None # set while inside a FunctionDef
        self._functions: dict[str, int] = {}       # name → arity
        self._current_fn: str | None = None        # name of enclosing function (or None)
```

---

**Dispatch / visit pattern** (parallel to `src/atena/parser.py` lines 699–828 `_dispatch_statement`):

The analyzer uses `visit_<NodeType>` naming (ARCHITECTURE Pattern 9). The public entry calls `_visit` which dispatches by `type(node).__name__`:
```python
def _visit(self, node: Node) -> str:
    """Dispatch to visit_<NodeType>; return the inferred type string for expressions."""
    method = getattr(self, f"visit_{type(node).__name__}", self._visit_default)
    return method(node)

def _visit_default(self, node: Node) -> str:
    """Fallthrough for node types the analyzer does not need to examine."""
    return "unknown"

def analyze(self) -> Program:
    """Public entry point. Walk all top-level statements; return the mutated Program.

    Returns a (potentially partial) Program even when errors were collected.
    The driver gates codegen on errors.is_empty(); it is the driver's
    responsibility to check, not the analyzer's.
    """
    for stmt in self._program.statements:
        self._visit(stmt)
    return self._program
```

---

**Error reporting pattern** — `errors.add()` only, never raise (`src/atena/parser.py` lines 224–228):
```python
try:
    return self._dispatch_statement()
except _ParseError as e:
    self._errors.add(e.line, e.message, e.source_line)
    self._synchronize()
    return None
```

The analyzer never uses internal exceptions for flow control. Every error goes directly through:
```python
self._errors.add(node.line, "plain English message", node.source_line)
```

Both `node.line` and `node.source_line` are already on every AST node (see `ast_nodes.py` lines 43–45):
```python
@dataclass
class Node:
    line: int = 0
    source_line: str = ""
```

---

**Core visit method shape** — statement-level visit (parallel to `_parse_if`, `_parse_while`, etc. in `parser.py` lines 554–597):
```python
def visit_If(self, node: If) -> str:
    self._visit(node.condition)
    for stmt in node.then_body:
        self._visit(stmt)
    for stmt in node.else_body:
        self._visit(stmt)
    return "unknown"

def visit_While(self, node: While) -> str:
    self._visit(node.condition)
    for stmt in node.body:
        self._visit(stmt)
    return "unknown"

def visit_Assign(self, node: Assign) -> str:
    inferred = self._visit(node.value)
    # Register name in the current scope.
    scope = self._locals if self._locals is not None else self._globals
    scope[node.name] = inferred
    return "unknown"
```

---

**FunctionDef scoping pattern** (parallel to `_parse_function_def` tracking `_fn_depth` at `parser.py` lines 599–625):

The parser uses `_fn_depth` incremented/decremented around the body parse. The analyzer uses a pushed/popped local scope:
```python
def visit_FunctionDef(self, node: FunctionDef) -> str:
    # Register before visiting body so recursive calls resolve (but no hoisting: D-09).
    self._functions[node.name] = len(node.params)
    self._globals[node.name] = "function"

    # Push local scope (D-07: pure functions, no global-var reads).
    saved_locals = self._locals
    saved_fn = self._current_fn
    self._locals = {p: "unknown" for p in node.params}
    self._current_fn = node.name
    try:
        for stmt in node.body:
            self._visit(stmt)
    finally:
        self._locals = saved_locals
        self._current_fn = saved_fn
    return "unknown"
```

The `try/finally` mirrors parser.py lines 614–618 exactly — scope cleanup is guaranteed even on internal errors.

---

**IndexAccess rewrite pattern** (SEM-03/SEM-04/SEM-05 — D-05):

`index_converted` is the ready-made idempotency flag on `IndexAccess` (ast_nodes.py lines 179–190):
```python
@dataclass
class IndexAccess(Node):
    target: Node = field(default_factory=lambda: Node())
    index: Node = field(default_factory=lambda: Node())
    index_converted: bool = False
```

Rewrite logic:
```python
def visit_IndexAccess(self, node: IndexAccess) -> str:
    self._visit(node.target)

    if node.index_converted:
        # Idempotency guard: never shift twice (PITFALLS 6, D-05).
        self._visit(node.index)
        return "unknown"

    if isinstance(node.index, NumberLiteral):
        if node.index.value == 0:
            self._errors.add(
                node.line,
                "Lists in Atena start at 1, not 0.",
                node.source_line,
            )
        else:
            # Fold literal 1-based index to 0-based in place.
            node.index.value -= 1
            node.index_converted = True
    elif isinstance(node.index, UnaryOp) and node.index.op == "-" and isinstance(node.index.operand, NumberLiteral):
        # Literal negative: compile-time error with distinct message (D-06).
        self._errors.add(
            node.line,
            "Atena lists count from 1 — there are no negative positions. The last item is at length, not -1.",
            node.source_line,
        )
    else:
        # Dynamic index: route through _atena_index runtime helper (D-05, PITFALLS 5).
        # Wrap the existing index node inside a FunctionCall so codegen emits
        # _atena_index(i) which performs the 1→0 shift and validates at runtime.
        helper = FunctionCall(
            name="_atena_index",
            args=[node.index],
            line=node.line,
            source_line=node.source_line,
        )
        node.index = helper
        node.index_converted = True
    return "unknown"
```

---

**BinOp coercion pattern** (SEM-01/SEM-02 — D-01/D-02):

Types are inferred bottom-up. `_visit` returns an inferred type string (from the lattice: `"str"`, `"number"`, `"bool"`, `"list"`, `"dict"`, `"unknown"`). The `+` coercion decision is made after both sides are inferred. Node injection uses the existing `FunctionCall` node (CODE CONTEXT note):
```python
def visit_BinOp(self, node: BinOp) -> str:
    left_type = self._visit(node.left)
    right_type = self._visit(node.right)

    if node.op != "+":
        # Non-+ operators: no static type-checking in v1.0 (D-04).
        return "unknown"

    # + coercion table (D-01: total, no silent fall-through).
    outcome = _COERCE_TABLE.get((left_type, right_type))
    if outcome == "error":
        self._errors.add(
            node.line,
            f"I can't add a {_HUMAN_TYPE[left_type]} and a {_HUMAN_TYPE[right_type]} together"
            " — try making them the same kind first.",
            node.source_line,
        )
        return "unknown"
    elif outcome == "coerce_right":
        node.right = FunctionCall(name="str", args=[node.right],
                                  line=node.right.line, source_line=node.right.source_line)
        return "str"
    elif outcome == "coerce_left":
        node.left = FunctionCall(name="str", args=[node.left],
                                 line=node.left.line, source_line=node.left.source_line)
        return "str"
    elif outcome == "runtime_helper":
        # Unknown-typed operand: route entire + through _atena_concat (D-02).
        helper = FunctionCall(
            name="_atena_concat",
            args=[node.left, node.right],
            line=node.line,
            source_line=node.source_line,
        )
        # Replace node fields so the parent sees a FunctionCall in node.left
        # (the generator will emit it as-is from the BinOp's parent).
        # Actually: the parent re-reads node; mutate both children to signal no-op
        # and store the helper on the node for the generator.
        # SIMPLER: the generator checks for _atena_concat on BinOp by inspecting
        # whether left or right is a FunctionCall(name="_atena_concat"). Mark via
        # replacing node.left with the helper and node.right with a sentinel, OR:
        # inject as a top-level replacement — planner chooses; mark here for planning.
        pass
    # outcome == "no_coerce" or None (both same type, or number+number):
    return left_type if left_type == right_type else "unknown"
```

The `_COERCE_TABLE` and `_HUMAN_TYPE` dictionaries are module-level constants:
```python
_HUMAN_TYPE: dict[str, str] = {
    "str": "text",
    "number": "number",
    "bool": "true/false",
    "list": "list",
    "dict": "dictionary",
    "unknown": "unknown",
}

# (left_type, right_type) → outcome
_COERCE_TABLE: dict[tuple[str, str], str] = {
    ("str",    "str"):     "no_coerce",
    ("str",    "number"):  "coerce_right",   # wrap number in str()
    ("str",    "bool"):    "coerce_right",   # wrap bool in str()
    ("number", "str"):     "coerce_left",    # wrap number in str()
    ("number", "number"):  "no_coerce",
    ("number", "bool"):    "error",
    ("bool",   "str"):     "coerce_left",    # wrap bool in str()
    ("bool",   "number"):  "error",
    ("bool",   "bool"):    "error",
    ("list",   "str"):     "error",
    ("dict",   "str"):     "error",
    # Any unknown side → defer to runtime helper (D-02)
    # (handled separately before table lookup: if either side is "unknown")
}
```

---

**Identifier / undefined-name + suggest pattern** (SEM-06 — D-08/D-09):

The `suggest()` function is already in `errors.py` (lines 102–152). Candidates are `in_scope_names + ATENA_KEYWORDS`. The suggest() call appends to the error message as a second sentence:
```python
def visit_Identifier(self, node: Identifier) -> str:
    name = node.name
    scope = self._locals if self._locals is not None else self._globals

    if name in scope:
        return scope[name]
    # Check for outer-variable read from inside a function (D-08 tailored message).
    if self._locals is not None and name in self._globals:
        self._errors.add(
            node.line,
            f'A function can only use its own inputs — pass "{name}" in as a parameter.',
            node.source_line,
        )
        scope[name] = "unknown"   # poison (D-09) to suppress cascade
        return "unknown"
    # Fully undefined.
    candidates = list(scope.keys()) + list(ATENA_KEYWORDS)
    hint = suggest(name, candidates)
    msg = f'I don\'t know what "{name}" is yet. Did you forget to create it first?'
    if hint:
        msg = f'{msg} {hint}'
    self._errors.add(node.line, msg, node.source_line)
    # Poison: register as UNKNOWN so later uses don't re-error (D-09).
    scope[name] = "unknown"
    return "unknown"
```

---

**FunctionCall arity pattern** (SEM-07 — D-09):
```python
def visit_FunctionCall(self, node: FunctionCall) -> str:
    # Visit args first (bottom-up).
    for arg in node.args:
        self._visit(arg)

    # Built-in pass-through names: "length", "str", "_atena_concat", "_atena_index".
    if node.name in {"length", "str", "_atena_concat", "_atena_index"}:
        return "unknown"

    if node.name not in self._functions:
        # Check if it exists as a global variable (wrong-kind error) or is unknown.
        if node.name in self._globals:
            self._errors.add(
                node.line,
                f'"{node.name}" is not a function — it\'s a value you stored. '
                'You cannot call it.',
                node.source_line,
            )
        else:
            candidates = list(self._globals.keys()) + list(ATENA_KEYWORDS)
            hint = suggest(node.name, candidates)
            msg = f'I don\'t know a function called "{node.name}" yet — define it above this line first.'
            if hint:
                msg = f'{msg} {hint}'
            self._errors.add(node.line, msg, node.source_line)
        return "unknown"

    expected = self._functions[node.name]
    given = len(node.args)
    if expected != given:
        self._errors.add(
            node.line,
            f'"{node.name}" expects {expected} value{"s" if expected != 1 else ""}, '
            f'but you gave {given}.',
            node.source_line,
        )
    return "unknown"
```

---

**Ask / str-typed symbol pattern** (D-03):
```python
def visit_Ask(self, node: Ask) -> str:
    # ask results are always typed str (D-03).
    scope = self._locals if self._locals is not None else self._globals
    scope[node.target] = "str"
    return "unknown"
```

---

**Module-level docstring shape** (parallel to `src/atena/parser.py` lines 1–10):
```python
"""
Semantic Analyzer for the Atena transpiler.

Takes the parser's Program AST (contract B) and enriches it in place,
producing the analyzed AST (contract C) the Phase-4 generator emits
verbatim. Semantic errors are collected through the injected ErrorCollector.
The analyzer never raises to the user and never emits a Python traceback.
"""
```

---

### `tests/test_analyzer.py` (test, batch)

**Analog:** `tests/test_parser.py`

**Module-level docstring + imports pattern** (`tests/test_parser.py` lines 1–32):
```python
"""
TDD tests for the Atena Semantic Analyzer — Phase 3 RED phase.

Layer 1 (golden mutated-AST snapshots): run the analyzer on a valid snippet,
    assert the mutated node equals the expected shape (index_converted=True,
    injected FunctionCall("str"/...), updated field values).

Layer 2 (error-path tests): feed source with semantic errors, assert exact
    key phrase in ec.report(), error count, and line numbers — no crash,
    no hang.

Layer 3 (cross-requirement tests): multiple errors collected in one run,
    poison suppresses cascades, arity checks, no-hoisting enforcement.
"""

from __future__ import annotations

import pytest

from atena.errors import ErrorCollector
from atena.ast_nodes import (
    Program, Assign, Show, Ask, If, While, Repeat,
    FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
    ListLiteral, DictLiteral, IndexAccess, DotAccess,
    ListAdd, ListRemove, Identifier, NumberLiteral,
    StringLiteral, BoolLiteral,
)
from atena.lexer import Lexer
from atena.parser import Parser
from atena.analyzer import SemanticAnalyzer
```

---

**Test helper pattern** (`tests/test_parser.py` lines 35–45 `_parse`):
```python
def _analyze(source: str) -> tuple[Program, ErrorCollector]:
    """Helper: lex + parse + analyze source; return (program_ast, errors).

    Chains through the real Lexer and Parser so tests use production ASTs.
    The ErrorCollector is shared across all three phases — each phase appends
    to the same collector (matching the pipeline contract).
    """
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    program = Parser(tokens, ec).parse()
    SemanticAnalyzer(program, ec).analyze()
    return program, ec
```

---

**Layer 1 — Golden mutated-AST snapshot test shape** (`tests/test_parser.py` lines 53–62):
```python
def test_A1_index_literal_rewritten():
    """'x = items[1]' → analyzer sets index.value=0 and index_converted=True."""
    program, ec = _analyze("items = [10, 20]\nx = items[1]\n")
    assert ec.is_empty()
    assign = program.statements[1]
    assert isinstance(assign, Assign)
    access = assign.value
    assert isinstance(access, IndexAccess)
    assert access.index_converted is True
    assert isinstance(access.index, NumberLiteral)
    assert access.index.value == 0   # 1→0 rewrite


def test_A1_string_concat_no_coerce():
    """'x = "a" + "b"' → BinOp left/right unchanged (both str, no coercion needed)."""
    program, ec = _analyze('x = "a" + "b"\n')
    assert ec.is_empty()
    binop = program.statements[0].value
    assert isinstance(binop, BinOp)
    assert isinstance(binop.left, StringLiteral)    # not wrapped
    assert isinstance(binop.right, StringLiteral)   # not wrapped


def test_A1_str_coerce_number_rhs():
    """'x = "hello" + 5' → right side wrapped in FunctionCall("str", [NumberLiteral(5)])."""
    program, ec = _analyze('x = "hello" + 5\n')
    assert ec.is_empty()
    binop = program.statements[0].value
    assert isinstance(binop, BinOp)
    assert isinstance(binop.left, StringLiteral)
    assert isinstance(binop.right, FunctionCall)
    assert binop.right.name == "str"
    assert len(binop.right.args) == 1
    assert isinstance(binop.right.args[0], NumberLiteral)
    assert binop.right.args[0].value == 5
```

---

**Layer 2 — Error-path test shape** (`tests/test_parser.py` lines 598–609):
```python
def test_A2_index_zero_error():
    """'x = items[0]' produces the canonical '...start at 1, not 0.' error."""
    items_assign = "items = [10, 20, 30]\n"
    _, ec = _analyze(f"{items_assign}x = items[0]\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "start at 1, not 0" in report
    assert "Error on line 2" in report


def test_A2_undefined_variable():
    """Using 'score' before assigning it produces the canonical undefined-name error."""
    _, ec = _analyze("show score\n")
    assert not ec.is_empty()
    report = ec.report()
    assert '"score"' in report
    assert "Error on line 1" in report


def test_A2_call_before_defined():
    """Calling 'greet()' before its 'function greet()' definition is a compile error."""
    source = "greet()\nfunction greet()\n    show 1\n"
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "greet" in report
    assert "Error on line 1" in report


def test_A2_wrong_arity():
    """Calling greet(1, 2) when greet expects 1 arg produces the arity message."""
    source = 'function greet(name)\n    show name\ngreet("Ana", "extra")\n'
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "greet" in report
    assert "expects 1" in report
    assert "gave 2" in report
```

---

**Layer 3 — Cross-requirement test shape** (`tests/test_parser.py` lines 809–847):
```python
def test_Ax_poison_suppresses_cascade():
    """Undefined 'score' on line 1 produces exactly 1 error; line 2 'show score' does NOT add a second."""
    source = "show score\nshow score\n"
    _, ec = _analyze(source)
    report = ec.report()
    # Dedup fires at report() time; or poison prevents a second add().
    assert report.count("Error on line") == 1


def test_Ax_multiple_semantic_errors_collected():
    """Three independent errors in one program are all collected."""
    source = "show undefined1\nshow undefined2\nx = items[0]\n"
    _, ec = _analyze(source)
    report = ec.report()
    assert report.count("Error on line") >= 3


def test_Ax_empty_program_no_errors():
    """Empty source produces no semantic errors."""
    _, ec = _analyze("")
    assert ec.is_empty()
```

---

**Error count / line assertion pattern** (`tests/test_parser.py` lines 809–815):
```python
# Count errors by counting "Error on line" in ec.report()
error_count = ec.report().count("Error on line")
assert error_count == 3

# Assert specific line numbers
assert "Error on line 1" in ec.report()
assert "Error on line 2" in ec.report()
```

---

**Key phrase assertion pattern** (`tests/test_parser.py` lines 600–605):
```python
# Always assert a key phrase in the plain-English message, not the full string.
# This makes tests resilient to minor wording tweaks.
assert "start at 1, not 0" in report        # canonical locked phrasing
assert '"score"' in report                  # quoted name appears in message
assert "function" in report                 # keyword in redirect message
```

---

## Shared Patterns

### ErrorCollector injection (shared by all `src/atena/` modules)

**Source:** `src/atena/parser.py` lines 100–104; `src/atena/errors.py` lines 29–37

**Apply to:** `src/atena/analyzer.py`

Pattern: `ErrorCollector` is always a constructor argument, never instantiated inside the class. The analyzer calls ONLY `self._errors.add(line, message, source_line)` — it never calls `self._errors.report()` or reads `self._errors.is_empty()`. The driver does that.

```python
# CORRECT
class SemanticAnalyzer:
    def __init__(self, program: Program, errors: ErrorCollector) -> None:
        self._errors = errors

# NEVER
class SemanticAnalyzer:
    def __init__(self, program: Program) -> None:
        self._errors = ErrorCollector()  # wrong: global state
```

---

### suggest() + ATENA_KEYWORDS (shared undefined-name affordance)

**Source:** `src/atena/errors.py` lines 88–152

**Apply to:** `src/atena/analyzer.py` (visit_Identifier, visit_FunctionCall)

```python
from atena.errors import ErrorCollector, suggest, ATENA_KEYWORDS

# Build candidates as in-scope names PLUS all 19 keywords
candidates = list(scope.keys()) + list(ATENA_KEYWORDS)
hint = suggest(name, candidates)
# suggest() returns ready-to-append string or None
msg = f'I don\'t know what "{name}" is yet. Did you forget to create it first?'
if hint:
    msg = f'{msg} {hint}'
self._errors.add(node.line, msg, node.source_line)
```

---

### Node position fields (shared across all phases)

**Source:** `src/atena/ast_nodes.py` lines 43–45

**Apply to:** `src/atena/analyzer.py` (every `self._errors.add()` call)

Every `Node` subclass carries `line: int` and `source_line: str` — always use `node.line` and `node.source_line` directly; never recalculate or look up the source text.

```python
self._errors.add(node.line, "plain English message", node.source_line)
```

---

### try/finally scope cleanup (shared with parser)

**Source:** `src/atena/parser.py` lines 614–618

**Apply to:** `src/atena/analyzer.py` `visit_FunctionDef`

```python
self._fn_depth += 1
try:
    body = self._parse_block()
finally:
    self._fn_depth -= 1
```

Mirror exactly in the analyzer with `_locals`/`_current_fn` instead of `_fn_depth`:
```python
saved_locals = self._locals
saved_fn = self._current_fn
self._locals = {p: "unknown" for p in node.params}
self._current_fn = node.name
try:
    for stmt in node.body:
        self._visit(stmt)
finally:
    self._locals = saved_locals
    self._current_fn = saved_fn
```

---

### `from __future__ import annotations` (project-wide)

**Source:** `src/atena/parser.py` line 12; `src/atena/errors.py` line 12; `src/atena/ast_nodes.py` line 21

**Apply to:** both `src/atena/analyzer.py` and `tests/test_analyzer.py` — always the first non-docstring import.

---

### Test helper naming convention

**Source:** `tests/test_parser.py` line 35 (`_parse`); `tests/test_lexer.py` line 22 (`_lex`)

**Apply to:** `tests/test_analyzer.py`

Name the helper `_analyze`. It chains through the real Lexer and Parser before calling `SemanticAnalyzer`, so tests always use the full production input path.

---

### Test naming convention

**Source:** `tests/test_parser.py` lines 53, 598, 809

**Apply to:** `tests/test_analyzer.py`

Three layers, three prefixes:
- `test_A1_<description>` — Layer 1 golden mutated-AST snapshot
- `test_A2_<description>` — Layer 2 error-path (key phrase + line number)
- `test_Ax_<description>` — Layer 3 cross-requirement (cascades, counts, integration)

---

## No Analog Found

No files fall in this category. Both files have close analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `src/atena/`, `tests/`
**Files scanned:** `src/atena/parser.py` (847 lines), `src/atena/ast_nodes.py` (248 lines), `src/atena/errors.py` (153 lines), `tests/test_parser.py` (1149 lines), `tests/conftest.py` (9 lines), `tests/test_lexer.py` (first 80 lines)
**Pattern extraction date:** 2026-06-14
