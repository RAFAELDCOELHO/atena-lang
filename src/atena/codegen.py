"""
Code Generator for the Atena transpiler — Phase 4.

Takes the fully-analyzed Program AST (contract C) produced by the Semantic
Analyzer and emits a valid, runnable Python 3 source string (contract D).

Strategy D-01: build a real Python `ast` module tree from the Atena AST, call
`ast.fix_missing_locations()`, then `ast.unparse()` to get a Python source
string.  This makes operator-precedence and parenthesization bugs structurally
impossible — `ast.unparse` handles both for free.

Post-pass patches (D-02) applied after `ast.unparse()`:
  1. Restore double-quoted strings — `ast.unparse` defaults to single quotes;
     learners typed double quotes, so restore them for readability.
  2. Insert blank lines between top-level function definitions.
  3. Prepend a header comment (friendly tone, not raw code).

GEN-05 self-check: `ast.parse()` is called on the final source after patches.
A failure here is an internal Atena bug, not a user error — it is never caught
or turned into an ErrorCollector entry.

The driver (Phase 5) MUST check `errors.is_empty()` BEFORE calling
`CodeGenerator(program).generate()`.  This class assumes the tree is
error-free and emits verbatim — it never re-derives indices or coercion marks
(anti-pattern 4 from ARCHITECTURE.md).
"""

from __future__ import annotations

import ast
import keyword
import re

from atena.ast_nodes import (
    Program,
    Assign,
    Show,
    Ask,
    If,
    While,
    Repeat,
    FunctionDef,
    Return,
    FunctionCall,
    BinOp,
    UnaryOp,
    ListLiteral,
    DictLiteral,
    IndexAccess,
    DotAccess,
    ListAdd,
    ListRemove,
    Identifier,
    NumberLiteral,
    StringLiteral,
    BoolLiteral,
    Node,
)

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _mangle(name: str) -> str:
    """Append trailing underscore to Python keyword identifiers (GEN-04).

    Uses `keyword.iskeyword()` from the stdlib — stays correct across Python
    versions without a hardcoded list (T-04-01 mitigation).  Does NOT mangle
    soft keywords (match/case/type) or builtins in v1.0; the minimum
    requirement is that hard keywords make the output unparseable.
    """
    if keyword.iskeyword(name):
        return name + "_"
    return name


# Helper function source bodies — names are locked by Phase 3 context (03-CONTEXT D-06).
# These are emitted on-demand (only when the program uses them) for clean learner output.

_ATENA_INDEX_SRC: str = """\
def _atena_index(i):
    if i < 1:
        raise IndexError("List positions in Atena start at 1.")
    return i - 1
"""

_ATENA_CONCAT_SRC: str = """\
def _atena_concat(a, b):
    return str(a) + str(b)
"""


def _parse_helper(src: str) -> list[ast.stmt]:
    """Parse a helper function source string and return its AST statements."""
    module = ast.parse(src)
    return module.body


# ---------------------------------------------------------------------------
# Code Generator
# ---------------------------------------------------------------------------


class CodeGenerator:
    """Tree-walk code generator for the Atena transpiler.

    Reads the fully-analyzed Program AST (contract C) and produces a valid
    Python 3 source string (contract D) via stdlib ast.unparse().

    The driver (Phase 5) MUST gate on errors.is_empty() before calling
    generate(). This class assumes the tree is error-free and emits verbatim
    — it never re-derives indices or coercion marks (anti-pattern 4).
    """

    def __init__(self, program: Program) -> None:
        self._program: Program = program          # read-only — never mutated
        self._used_helpers: set[str] = set()      # tracks which _atena_* helpers were used
        self._loop_counter: int = 0               # monotonic counter for nested repeat vars

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    def generate(self) -> str:
        """Walk all top-level statements; return the Python source string.

        Applies the three D-02 post-patches after ast.unparse():
        1. Restore double-quoted strings (single-quote → double-quote, carefully).
        2. Blank lines between top-level function definitions.
        3. Header comment at the top.
        Then runs ast.parse() self-check (GEN-05) — a failure here is an
        internal bug, not a user error.
        """
        raise NotImplementedError("CodeGenerator.generate() not yet implemented")

    # -----------------------------------------------------------------------
    # Dispatch
    # -----------------------------------------------------------------------

    def _emit(self, node: Node) -> ast.stmt | ast.expr:
        """Dispatch to _emit_<NodeType>; raise TypeError for unknown nodes."""
        method = getattr(self, f"_emit_{type(node).__name__}", self._emit_default)
        return method(node)

    def _emit_default(self, node: Node) -> ast.expr:
        """Fallthrough for unhandled node types — always an internal bug."""
        raise TypeError(
            f"CodeGenerator has no emitter for {type(node).__name__}. "
            "This is an internal Atena bug."
        )

    # -----------------------------------------------------------------------
    # Statement emitters (stubs — raise NotImplementedError until Plan 02-05)
    # -----------------------------------------------------------------------

    def _emit_Program(self, node: Program) -> list[ast.stmt]:  # type: ignore[return]
        raise NotImplementedError("_emit_Program not yet implemented")

    def _emit_Assign(self, node: Assign) -> ast.Assign:  # type: ignore[return]
        raise NotImplementedError("_emit_Assign not yet implemented")

    def _emit_Show(self, node: Show) -> ast.Expr:  # type: ignore[return]
        raise NotImplementedError("_emit_Show not yet implemented")

    def _emit_Ask(self, node: Ask) -> ast.Assign:  # type: ignore[return]
        raise NotImplementedError("_emit_Ask not yet implemented")

    def _emit_If(self, node: If) -> ast.If:  # type: ignore[return]
        raise NotImplementedError("_emit_If not yet implemented")

    def _emit_While(self, node: While) -> ast.While:  # type: ignore[return]
        raise NotImplementedError("_emit_While not yet implemented")

    def _emit_Repeat(self, node: Repeat) -> ast.For:  # type: ignore[return]
        raise NotImplementedError("_emit_Repeat not yet implemented")

    def _emit_FunctionDef(self, node: FunctionDef) -> ast.FunctionDef:  # type: ignore[return]
        raise NotImplementedError("_emit_FunctionDef not yet implemented")

    def _emit_Return(self, node: Return) -> ast.Return:  # type: ignore[return]
        raise NotImplementedError("_emit_Return not yet implemented")

    def _emit_FunctionCall(self, node: FunctionCall) -> ast.expr:  # type: ignore[return]
        raise NotImplementedError("_emit_FunctionCall not yet implemented")

    def _emit_BinOp(self, node: BinOp) -> ast.expr:  # type: ignore[return]
        raise NotImplementedError("_emit_BinOp not yet implemented")

    def _emit_UnaryOp(self, node: UnaryOp) -> ast.expr:  # type: ignore[return]
        raise NotImplementedError("_emit_UnaryOp not yet implemented")

    def _emit_ListLiteral(self, node: ListLiteral) -> ast.List:  # type: ignore[return]
        raise NotImplementedError("_emit_ListLiteral not yet implemented")

    def _emit_DictLiteral(self, node: DictLiteral) -> ast.Dict:  # type: ignore[return]
        raise NotImplementedError("_emit_DictLiteral not yet implemented")

    def _emit_IndexAccess(self, node: IndexAccess) -> ast.Subscript:  # type: ignore[return]
        raise NotImplementedError("_emit_IndexAccess not yet implemented")

    def _emit_DotAccess(self, node: DotAccess) -> ast.Subscript:  # type: ignore[return]
        raise NotImplementedError("_emit_DotAccess not yet implemented")

    def _emit_ListAdd(self, node: ListAdd) -> ast.Expr:  # type: ignore[return]
        raise NotImplementedError("_emit_ListAdd not yet implemented")

    def _emit_ListRemove(self, node: ListRemove) -> ast.Expr:  # type: ignore[return]
        raise NotImplementedError("_emit_ListRemove not yet implemented")

    def _emit_Identifier(self, node: Identifier) -> ast.Name:  # type: ignore[return]
        raise NotImplementedError("_emit_Identifier not yet implemented")

    def _emit_NumberLiteral(self, node: NumberLiteral) -> ast.Constant:  # type: ignore[return]
        raise NotImplementedError("_emit_NumberLiteral not yet implemented")

    def _emit_StringLiteral(self, node: StringLiteral) -> ast.Constant:  # type: ignore[return]
        raise NotImplementedError("_emit_StringLiteral not yet implemented")

    def _emit_BoolLiteral(self, node: BoolLiteral) -> ast.Constant:  # type: ignore[return]
        raise NotImplementedError("_emit_BoolLiteral not yet implemented")
