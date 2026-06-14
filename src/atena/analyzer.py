"""
Semantic Analyzer for the Atena transpiler.

Takes the parser's Program AST (contract B) and enriches it in place,
producing the analyzed AST (contract C) the Phase-4 generator emits
verbatim. Semantic errors are collected through the injected ErrorCollector.
The analyzer never raises to the user and never emits a Python traceback.
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

# ---------------------------------------------------------------------------
# Module-level constants (stubs — logic added in Plan 02)
# ---------------------------------------------------------------------------

_HUMAN_TYPE: dict[str, str] = {}

_COERCE_TABLE: dict[tuple[str, str], str] = {}


# ---------------------------------------------------------------------------
# SemanticAnalyzer
# ---------------------------------------------------------------------------


class SemanticAnalyzer:
    """Tree-walk semantic analyzer for the Atena transpiler.

    Mutates the Program AST in place (contract B → C) and reports errors
    through the injected ErrorCollector.  The driver gates codegen on
    errors.is_empty(); it is the driver's responsibility to check.
    """

    def __init__(self, program: Program, errors: ErrorCollector) -> None:
        self._program: Program = program        # mutated in place (contract B → C)
        self._errors: ErrorCollector = errors   # injected — never instantiate internally
        # Symbol table: two-level scope (D-07)
        self._globals: dict[str, str] = {}         # name → inferred type
        self._locals: dict[str, str] | None = None  # set while inside a FunctionDef
        self._functions: dict[str, int] = {}       # name → arity
        self._current_fn: str | None = None        # name of enclosing function (or None)

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    def analyze(self) -> Program:
        """Walk all top-level statements; return the mutated Program.

        Returns a (potentially partial) Program even when errors were collected.
        The driver gates codegen on errors.is_empty(); it is the driver's
        responsibility to check, not the analyzer's.
        """
        for stmt in self._program.statements:
            self._visit(stmt)
        return self._program

    # -----------------------------------------------------------------------
    # Dispatch
    # -----------------------------------------------------------------------

    def _visit(self, node: Node) -> str:
        """Dispatch to visit_<NodeType>; return the inferred type string for expressions."""
        method = getattr(self, f"visit_{type(node).__name__}", self._visit_default)
        return method(node)

    def _visit_default(self, node: Node) -> str:
        """Fallthrough for node types the analyzer does not need to examine."""
        return "unknown"

    # -----------------------------------------------------------------------
    # Stub visit methods (all 22 node types — return "unknown", no logic)
    # -----------------------------------------------------------------------

    def visit_Program(self, node: Program) -> str:
        return "unknown"

    def visit_Assign(self, node: Assign) -> str:
        return "unknown"

    def visit_Show(self, node: Show) -> str:
        return "unknown"

    def visit_Ask(self, node: Ask) -> str:
        return "unknown"

    def visit_If(self, node: If) -> str:
        return "unknown"

    def visit_While(self, node: While) -> str:
        return "unknown"

    def visit_Repeat(self, node: Repeat) -> str:
        return "unknown"

    def visit_FunctionDef(self, node: FunctionDef) -> str:
        return "unknown"

    def visit_Return(self, node: Return) -> str:
        return "unknown"

    def visit_FunctionCall(self, node: FunctionCall) -> str:
        return "unknown"

    def visit_BinOp(self, node: BinOp) -> str:
        return "unknown"

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        return "unknown"

    def visit_ListLiteral(self, node: ListLiteral) -> str:
        return "unknown"

    def visit_DictLiteral(self, node: DictLiteral) -> str:
        return "unknown"

    def visit_IndexAccess(self, node: IndexAccess) -> str:
        return "unknown"

    def visit_DotAccess(self, node: DotAccess) -> str:
        return "unknown"

    def visit_ListAdd(self, node: ListAdd) -> str:
        return "unknown"

    def visit_ListRemove(self, node: ListRemove) -> str:
        return "unknown"

    def visit_Identifier(self, node: Identifier) -> str:
        return "unknown"

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        return "unknown"

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        return "unknown"

    def visit_BoolLiteral(self, node: BoolLiteral) -> str:
        return "unknown"
