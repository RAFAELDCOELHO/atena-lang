# Phase 4: Code Generator - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 4 new files
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/atena/codegen.py` | service/transformer | transform (AST → source string) | `src/atena/analyzer.py` | role-match (same tree-walk + dispatch structure; different output) |
| `tests/test_codegen.py` | test | batch (three-layer gate) | `tests/test_analyzer.py` | exact (same three-layer structure, same helper pattern) |
| `tests/fixtures/` | config/data | file-I/O | no fixtures dir exists yet | no analog — create from scratch |
| `examples/school.atena` | config/data | file-I/O | no examples dir exists yet | no analog — author from scratch |

---

## Pattern Assignments

### `src/atena/codegen.py` (transformer, AST → Python source string)

**Analog:** `src/atena/analyzer.py`

**Imports pattern** (analyzer.py lines 1–20):
```python
"""
<module docstring explaining what the phase does, its inputs and outputs,
and what the produced contract is (contract D for codegen)>
"""

from __future__ import annotations

from atena.ast_nodes import (
    Program, Assign, Show, Ask, If, While, Repeat,
    FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
    ListLiteral, DictLiteral, IndexAccess, DotAccess,
    ListAdd, ListRemove, Identifier, NumberLiteral,
    StringLiteral, BoolLiteral,
    Node,
)
```

**CRITICAL import constraint for codegen.py:** Import `ast_nodes` plus stdlib `ast` only. Never import `lexer`, `parser`, or `analyzer`. Never import `errors` (the generator adds no errors; it receives a `Program` that is already gate-checked). The `ErrorCollector` is not injected into `CodeGenerator` — it is the driver's (Phase 5) responsibility to call `errors.is_empty()` before ever calling `CodeGenerator`.

**Class and `__init__` pattern** (analyzer.py lines 68–84, adapted for codegen):
```python
class CodeGenerator:
    """Tree-walk code generator for the Atena transpiler.

    Reads the fully-analyzed Program AST (contract C) and produces a valid
    Python 3 source string (contract D) via stdlib ast.unparse().

    The driver (Phase 5) MUST gate on errors.is_empty() before calling
    generate(). This class assumes the tree is error-free and emits verbatim
    — it never re-derives indices or coercion marks (anti-pattern 4).
    """

    def __init__(self, program: Program) -> None:
        self._program: Program = program   # read-only — never mutated
        self._used_helpers: set[str] = set()   # tracks which _atena_* helpers were used
        self._loop_counter: int = 0            # monotonic counter for nested repeat vars
```

No `ErrorCollector` field. That is the key structural difference from `SemanticAnalyzer.__init__`.

**Public entry point pattern** (analyzer.py lines 89–98, adapted):
```python
def generate(self) -> str:
    """Walk all top-level statements; return the Python source string.

    Applies the three D-02 post-patches after ast.unparse():
    1. Restore double-quoted strings (single-quote → double-quote, carefully).
    2. Blank lines between top-level function definitions.
    3. Header comment at the top.
    Then runs ast.parse() self-check (GEN-05) — a failure here is an
    internal bug, not a user error.
    """
    body_stmts: list[ast.stmt] = []
    for stmt in self._program.statements:
        result = self._emit(stmt)
        if isinstance(result, list):
            body_stmts.extend(result)
        else:
            body_stmts.append(result)

    # Prepend on-demand helper bodies (GEN-04, Claude's Discretion: on-demand)
    preamble = self._build_preamble()
    module = ast.Module(body=preamble + body_stmts, type_ignores=[])
    ast.fix_missing_locations(module)
    python_source = ast.unparse(module)

    # D-02 post-patches
    python_source = self._patch_double_quotes(python_source)
    python_source = self._patch_blank_lines(python_source)
    python_source = self._patch_header(python_source)

    # GEN-05 self-check — always run after patches
    ast.parse(python_source)   # raises SyntaxError on internal bug
    return python_source
```

**Dispatch pattern** (analyzer.py lines 104–119):
```python
def _emit(self, node: Node) -> ast.stmt | ast.expr:
    """Dispatch to _emit_<NodeType>; return an ast node."""
    method = getattr(self, f"_emit_{type(node).__name__}", self._emit_default)
    return method(node)

def _emit_default(self, node: Node) -> ast.expr:
    """Fallthrough for unhandled node types — raises immediately (internal bug)."""
    raise TypeError(
        f"CodeGenerator has no emitter for {type(node).__name__}. "
        "This is an internal Atena bug."
    )
```

The naming convention mirrors the analyzer: `_emit_<NodeType>` instead of `visit_<NodeType>`. The fallthrough raises (unlike the analyzer which returns "unknown") because an unhandled node in codegen is always an internal bug — there are no errors to collect.

**Core emit pattern — statements** (pattern from analyzer.py visit_ methods):
```python
def _emit_Assign(self, node: Assign) -> ast.Assign:
    """name = value  →  ast.Assign([ast.Name(name)], emit_expr(value))"""
    import keyword
    target_name = _mangle(node.name)   # keyword mangling (GEN-04)
    return ast.Assign(
        targets=[ast.Name(id=target_name, ctx=ast.Store())],
        value=self._emit_expr(node.value),
    )

def _emit_Show(self, node: Show) -> ast.Expr:
    """show value  →  print(value)"""
    return ast.Expr(
        value=ast.Call(
            func=ast.Name(id="print", ctx=ast.Load()),
            args=[self._emit_expr(node.value)],
            keywords=[],
        )
    )

def _emit_Ask(self, node: Ask) -> ast.Assign:
    """ask "prompt" into target  →  target = input("prompt")"""
    target_name = _mangle(node.target)
    return ast.Assign(
        targets=[ast.Name(id=target_name, ctx=ast.Store())],
        value=ast.Call(
            func=ast.Name(id="input", ctx=ast.Load()),
            args=[ast.Constant(value=node.prompt)],
            keywords=[],
        ),
    )

def _emit_Repeat(self, node: Repeat) -> ast.For:
    """repeat N times  →  for _atena_i{N} in range(N):"""
    loop_var = f"_atena_i{self._loop_counter}"
    self._loop_counter += 1
    body = [self._emit(s) for s in node.body]
    self._loop_counter -= 1   # restore depth counter after body
    return ast.For(
        target=ast.Name(id=loop_var, ctx=ast.Store()),
        iter=ast.Call(
            func=ast.Name(id="range", ctx=ast.Load()),
            args=[self._emit_expr(node.count)],
            keywords=[],
        ),
        body=body,
        orelse=[],
    )
```

**Keyword mangling pattern** (module-level helper, GEN-04):
```python
import keyword as _keyword_module

def _mangle(name: str) -> str:
    """Append trailing underscore to Python keyword identifiers (GEN-04).

    Minimum: keyword.kwlist (hard keywords that make output unparseable).
    Does NOT mangle soft keywords (match/case/type) or builtins in v1.0.
    """
    if _keyword_module.iskeyword(name):
        return name + "_"
    return name
```

**On-demand helper emission pattern** (GEN-04, Claude's Discretion):
```python
def _build_preamble(self) -> list[ast.stmt]:
    """Emit helper function bodies only when the program uses them."""
    stmts: list[ast.stmt] = []
    if "_atena_index" in self._used_helpers:
        stmts.extend(_parse_helper(_ATENA_INDEX_SRC))
    if "_atena_concat" in self._used_helpers:
        stmts.extend(_parse_helper(_ATENA_CONCAT_SRC))
    return stmts

# Module-level helper source strings (bodies are locked by 03-CONTEXT D-06)
_ATENA_INDEX_SRC = """\
def _atena_index(i):
    if i < 1:
        raise IndexError("List positions in Atena start at 1.")
    return i - 1
"""

_ATENA_CONCAT_SRC = """\
def _atena_concat(a, b):
    return str(a) + str(b)
"""
```

**DotAccess emit pattern** (GEN-02 — dict dot-access → subscript):
```python
def _emit_expr_DotAccess(self, node: DotAccess) -> ast.Subscript:
    """student.name  →  student["name"]"""
    return ast.Subscript(
        value=self._emit_expr(node.target),
        slice=ast.Constant(value=node.name),
        ctx=ast.Load(),
    )
```

For **dot-write** (assignment target like `student.grade = 10`), the parser produces an `Assign` where `node.name` is a synthetic compound, OR the analyzer produces a `DotAccess` on the left side. The emit pattern is:
```python
# Inside _emit_Assign, detect DotAccess target:
if isinstance(node.value_target, DotAccess):   # schema depends on parser output
    target_ast = ast.Subscript(
        value=self._emit_expr(node.value_target.target),
        slice=ast.Constant(value=node.value_target.name),
        ctx=ast.Store(),
    )
```

**D-02 double-quote patch pattern** (post-unparse, fragile):
```python
import re as _re

def _patch_double_quotes(self, src: str) -> str:
    """Restore double-quoted strings after ast.unparse() singles them.

    Strategy: use ast.parse() to find string literal positions, then
    reconstruct — OR use a targeted regex that only replaces 'X' → "X"
    when X contains no single-quote (safe path) and leave strings with
    embedded single-quotes alone (ast.unparse already uses double-quotes
    for those).

    Do NOT use a naive global str.replace("'", '"') — it corrupts strings
    containing single quotes.
    """
    # Safe replacement: 'content' → "content" only when content has no single-quote
    return _re.sub(r"'([^'\\]*)'", r'"\1"', src)
```

---

### `tests/test_codegen.py` (test, three-layer gate)

**Analog:** `tests/test_analyzer.py`

**Module docstring pattern** (analyzer.py lines 1–14):
```python
"""
TDD tests for the Atena Code Generator — Phase 4 RED phase.

Layer 1 (golden snapshot tests): run the full pipeline on a valid snippet,
    assert the generated Python source text-matches the expected string exactly.
    The canonical golden is school.atena → school.expected.py (GEN-06).

Layer 2 (execution tests): compile and exec the generated Python with canned
    stdin, assert stdout matches the expected learner output. These catch
    runnable-but-wrong bugs (index/coercion) that text-match cannot.

Layer 3 (self-check + edge tests): ast.parse() self-check fires on every
    generate() call; targeted fixtures for mangling, nested-repeat loop vars,
    _atena_concat path, _atena_index path, dict dot-write, etc.
"""
```

**Import block pattern** (analyzer.py lines 18–31, adapted for codegen):
```python
from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

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
from atena.codegen import CodeGenerator
```

**Pipeline helper function pattern** (analyzer.py lines 33–44):
```python
def _generate(source: str) -> str:
    """Helper: full pipeline (lex → parse → analyze → generate); return Python source.

    Asserts no pipeline errors so test failures are readable.
    The ErrorCollector is shared across all phases (pipeline contract).
    """
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    program = Parser(tokens, ec).parse()
    SemanticAnalyzer(program, ec).analyze()
    assert ec.is_empty(), f"Pipeline errors before codegen:\n{ec.report()}"
    return CodeGenerator(program).generate()
```

**Layer 1 — Golden snapshot test pattern** (analyzer.py test_A1_* pattern):
```python
# ---------------------------------------------------------------------------
# Layer 1 — Golden snapshot tests (G1_*)
# ---------------------------------------------------------------------------

def test_G1_show_string_literal():
    """'show "hello"' → generated Python contains 'print("hello")'."""
    result = _generate('show "hello"\n')
    assert 'print("hello")' in result


def test_G1_assign_number():
    """'x = 5' → generated Python contains 'x = 5'."""
    result = _generate("x = 5\n")
    assert "x = 5" in result


def test_G1_golden_school_roundtrip():
    """school.atena round-trips through the pipeline to exactly school.expected.py."""
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "school.atena").read_text()
    expected = (fixtures / "school.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"Golden mismatch.\n--- expected ---\n{expected}\n--- got ---\n{result}"
    )
```

**Layer 2 — Execution test pattern** (subprocess approach, mirroring test_cli.py lines 28–34):
```python
# ---------------------------------------------------------------------------
# Layer 2 — Execution tests (G2_*)
# ---------------------------------------------------------------------------

def test_G2_school_execution_with_canned_stdin():
    """Generated school.py runs correctly with canned stdin and produces expected stdout."""
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "school.expected.py").read_text()

    result = subprocess.run(
        [sys.executable, "-c", python_src],
        input="Ana\n",          # canned stdin: student name
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert "Ana" in result.stdout, f"Expected name in output. Got:\n{result.stdout}"


def test_G2_show_number_executes():
    """'show 42' → generated Python executes and prints '42'."""
    python_src = _generate("show 42\n")
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "42"
```

**Layer 3 — Self-check and edge tests** (G3_* tests):
```python
# ---------------------------------------------------------------------------
# Layer 3 — Self-check + edge tests (G3_*)
# ---------------------------------------------------------------------------

def test_G3_ast_parse_selfcheck_on_every_output():
    """Every generate() call produces output that ast.parse() accepts without error."""
    snippets = [
        'show "hello"\n',
        "x = 5\nshow x\n",
        "items = [1, 2, 3]\nshow items[1]\n",
    ]
    for snippet in snippets:
        python_src = _generate(snippet)
        ast.parse(python_src)   # raises AssertionError on SyntaxError


def test_G3_keyword_mangling_class():
    """'class_ = 5' (Python keyword) → mangled as 'class_' in output."""
    result = _generate("class = 5\n")
    assert "class_" in result
    ast.parse(result)   # must parse cleanly


def test_G3_nested_repeat_unique_loop_vars():
    """Nested 'repeat' loops use distinct _atena_i* variables so inner never shadows outer."""
    source = "repeat 3 times\n    repeat 2 times\n        show 1\n"
    result = _generate(source)
    # Two distinct loop variables must appear
    import re
    loop_vars = re.findall(r"_atena_i\d+", result)
    assert len(set(loop_vars)) == 2, f"Expected 2 unique loop vars, got: {loop_vars}"
```

**Layer naming convention** (mirrors test_analyzer.py exactly):
- `test_G1_*` — golden snapshot (text-match)
- `test_G2_*` — execution tests (run the generated Python)
- `test_G3_*` — self-check and single-construct edge cases
- `test_Gx_*` — cross-requirement tests (double-quote patch, header comment, on-demand helpers)

---

### `tests/fixtures/` (data, file-I/O)

**No analog exists** — the `tests/fixtures/` directory does not exist yet. Create it.

**Convention from STACK.md / CONTEXT.md canonical refs:**
```
tests/fixtures/
    school.atena          ← canonical capstone (authored in Phase 4, D-03/D-04)
    school.expected.py    ← derived snapshot: pipeline output reviewed once and locked (D-06)
    # small targeted fixtures for edge cases:
    keyword_mangle.atena
    keyword_mangle.expected.py
    nested_repeat.atena
    nested_repeat.expected.py
    dynamic_index.atena
    dynamic_index.expected.py
    concat_helper.atena
    concat_helper.expected.py
    dict_dot_write.atena
    dict_dot_write.expected.py
```

**`school.atena` shape** (D-03/D-04/D-05 decisions from CONTEXT.md):
- Asks for one string (student name) via `ask` → `input()`
- Grades stored as list/dict literal data (no `ask`-for-numbers limitation hit)
- Exercises: I/O, variables, `if`/`else`, `while`, nested `repeat`, functions + `return`, lists (`add`/`remove`/`length`/literal index + variable index), dicts (literal + dot read + dot write), `str()` coercion, arithmetic
- `ask` feeds canned stdin `"Ana\n"` in Layer-2 execution tests for deterministic output

**`school.expected.py` generation process** (D-06):
1. Author `school.atena`
2. Run `_generate(school_atena_source)` to produce the snapshot
3. Review the snapshot for correctness (readable Python, correct constructs, double-quoted strings, header comment, blank lines between functions)
4. Write it to `tests/fixtures/school.expected.py` and lock

---

### `examples/school.atena` (data, file-I/O)

**No analog exists** — the `examples/` directory does not exist yet. Create it.

**This file is a copy of `tests/fixtures/school.atena`** — same content, different location. The `examples/` copy is the user-facing curriculum flagship (DOCS-01, Phase 6). For Phase 4, authoring it once in `tests/fixtures/` and symlinking or copying to `examples/` is sufficient.

---

## Shared Patterns

### Injected `ErrorCollector` convention (cross-cutting)
**Source:** `src/atena/analyzer.py` lines 76–83
**Apply to:** `codegen.py` class design — BUT with the key inversion: `CodeGenerator` does NOT receive an `ErrorCollector`. The gate is checked by the driver before codegen is called.

```python
# Analyzer: receives ErrorCollector, adds to it
class SemanticAnalyzer:
    def __init__(self, program: Program, errors: ErrorCollector) -> None:
        self._errors: ErrorCollector = errors  # injected

# CodeGenerator: NO ErrorCollector — driver gates before calling
class CodeGenerator:
    def __init__(self, program: Program) -> None:
        # No _errors field — GEN-05 self-check raises on internal bugs, never via collector
        ...
```

### Dispatch pattern (cross-cutting)
**Source:** `src/atena/analyzer.py` lines 104–119
**Apply to:** `codegen.py` — use `getattr(self, f"_emit_{type(node).__name__}", self._emit_default)`. Naming: `_emit_*` for codegen (vs `visit_*` for analyzer). Fallthrough in codegen raises `TypeError` (internal bug), not silently returns "unknown".

### `from __future__ import annotations` (all modules)
**Source:** Every existing module (`analyzer.py` line 10, `ast_nodes.py` line 20, `errors.py` — absent, `pipeline.py` line 8)
**Apply to:** `codegen.py` and `tests/test_codegen.py` — always the first non-comment import.

### Pipeline helper `_generate(source)` (test files)
**Source:** `tests/test_analyzer.py` lines 33–44 (`_analyze`), `tests/test_parser.py` lines 35–45 (`_parse`), `tests/test_lexer.py` lines 21–25 (`_lex`)
**Apply to:** `tests/test_codegen.py` — name it `_generate`, chain all four phases, assert `ec.is_empty()` before returning the generated string.

### Three-layer test gate (cross-cutting)
**Source:** `tests/test_analyzer.py` — Layer 1 (`test_A1_*`), Layer 2 (`test_A2_*`), Layer 3 (`test_Ax_*`)
**Apply to:** `tests/test_codegen.py` — Layer 1 (`test_G1_*` golden text-match), Layer 2 (`test_G2_*` execution), Layer 3 (`test_G3_*` self-check + edge), cross-req (`test_Gx_*`).

### subprocess execution pattern (test harness)
**Source:** `tests/test_cli.py` lines 28–34
**Apply to:** `tests/test_codegen.py` Layer-2 execution tests — use `subprocess.run([sys.executable, "-c", python_src], input=canned_stdin, capture_output=True, text=True, timeout=10)`. The `input=` parameter feeds canned stdin. This avoids monkeypatching `builtins.input` and works for any `exec`-style test.

### Double-quoted strings (project-wide)
**Source:** `CLAUDE.md` — "Double-quoted strings only; integers only"
**Apply to:** All string literals in `codegen.py`, `test_codegen.py`, and all fixture files. The D-02 patch restores double quotes in generated Python to match what the learner typed.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/fixtures/` | data | file-I/O | No fixture directory exists yet; first fixture-file tests in the project |
| `examples/school.atena` | data | file-I/O | No examples directory exists; first example program in the project |

---

## Metadata

**Analog search scope:** `src/atena/`, `tests/`
**Files scanned:** `analyzer.py` (599 lines), `ast_nodes.py` (248 lines), `errors.py` (153 lines), `tests/test_analyzer.py` (625 lines), `tests/test_cli.py` (414 lines), `tests/test_lexer.py` (80 lines sampled), `tests/test_parser.py` (80 lines sampled), `tests/conftest.py`, `src/atena/pipeline.py`
**Pattern extraction date:** 2026-06-14
