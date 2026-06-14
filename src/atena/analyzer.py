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
# Module-level constants
# ---------------------------------------------------------------------------

# Maps internal type lattice names to plain-English labels for error messages.
_HUMAN_TYPE: dict[str, str] = {
    "str":     "text",
    "number":  "number",
    "bool":    "true/false",
    "list":    "list",
    "dict":    "dictionary",
    "unknown": "unknown",
}

# (left_type, right_type) → outcome for the "+" operator.
# Covers all known-type (str / number / bool) pairings explicitly.
# Any pair involving "list", "dict", or an unlisted combination falls to the
# `.get(..., "error")` fallback in visit_BinOp — the fallback produces the
# same "error" outcome and keeps this table readable.
# "unknown" on either side is handled by a short-circuit BEFORE table lookup
# (D-02) so "unknown" keys are intentionally absent.
_COERCE_TABLE: dict[tuple[str, str], str] = {
    ("str",    "str"):    "no_coerce",
    ("str",    "number"): "coerce_right",   # wrap number in str()
    ("str",    "bool"):   "coerce_right",   # wrap bool in str()
    ("number", "str"):    "coerce_left",    # wrap number in str()
    ("number", "number"): "no_coerce",
    ("number", "bool"):   "error",
    ("bool",   "str"):    "coerce_left",    # wrap bool in str()
    ("bool",   "number"): "error",
    ("bool",   "bool"):   "error",
}


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
        """Visit the assigned value for type inference.

        Symbol table registration is implemented in Plan 03 (scope/arity).
        """
        self._visit(node.value)
        return "unknown"

    def visit_Show(self, node: Show) -> str:
        self._visit(node.value)
        return "unknown"

    def visit_Ask(self, node: Ask) -> str:
        """ask results are always typed str (D-03).

        Symbol table registration (node.target → "str") is Plan 03 scope work.
        """
        return "unknown"

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

    def visit_Repeat(self, node: Repeat) -> str:
        self._visit(node.count)
        for stmt in node.body:
            self._visit(stmt)
        return "unknown"

    def visit_FunctionDef(self, node: FunctionDef) -> str:
        """Function definition scope management.

        Arity registration and two-level scope push/pop are Plan 03 scope work.
        For now, visit the body so nested expressions (coercions, index rewrites)
        are still processed.
        """
        for stmt in node.body:
            self._visit(stmt)
        return "unknown"

    def visit_Return(self, node: Return) -> str:
        self._visit(node.value)
        return "unknown"

    def visit_FunctionCall(self, node: FunctionCall) -> str:
        """Visit all args bottom-up.

        Arity checking and undefined-name detection are Plan 03 scope work.
        """
        for arg in node.args:
            self._visit(arg)
        return "unknown"

    def visit_BinOp(self, node: BinOp) -> str:
        return "unknown"

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        return "unknown"

    def visit_ListLiteral(self, node: ListLiteral) -> str:
        for elem in node.elements:
            self._visit(elem)
        return "list"

    def visit_DictLiteral(self, node: DictLiteral) -> str:
        for _key, val in node.pairs:
            self._visit(val)
        return "dict"

    def visit_IndexAccess(self, node: IndexAccess) -> str:
        return "unknown"

    def visit_DotAccess(self, node: DotAccess) -> str:
        self._visit(node.target)
        return "unknown"

    def visit_ListAdd(self, node: ListAdd) -> str:
        self._visit(node.value)
        return "unknown"

    def visit_ListRemove(self, node: ListRemove) -> str:
        self._visit(node.value)
        return "unknown"

    def visit_Identifier(self, node: Identifier) -> str:
        return "unknown"

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        return "number"

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        return "str"

    def visit_BoolLiteral(self, node: BoolLiteral) -> str:
        return "bool"
