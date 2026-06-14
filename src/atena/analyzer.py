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
        """Visit the assigned value for type inference and register its type.

        Basic type tracking (for + coercion decisions on subsequent uses) is
        implemented here so that tests like test_A1_string_concat_no_coerce
        and test_A1_number_plus_number_no_coerce can resolve correctly.
        Full scope/arity enforcement (undefined-name errors, two-level scope,
        ask registration) is implemented in Plan 03.
        """
        inferred = self._visit(node.value)
        # Register the variable's inferred type in the current scope so that
        # subsequent uses (visit_Identifier) can return the correct type for
        # coercion decisions.
        scope = self._locals if self._locals is not None else self._globals
        scope[node.name] = inferred
        return "unknown"

    def visit_Show(self, node: Show) -> str:
        self._visit(node.value)
        return "unknown"

    def visit_Ask(self, node: Ask) -> str:
        """Register the ask target as "str" in the current scope (D-03).

        ask results are always typed str because Python's input() returns text.
        """
        scope = self._locals if self._locals is not None else self._globals
        scope[node.target] = "str"
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
        """Function definition scope management (SEM-07, D-07).

        Registers the function name and arity BEFORE visiting the body so that
        recursive self-calls resolve correctly (no hoisting for external calls
        though — D-09). Pushes a fresh local scope (params only) for the body,
        then restores the previous scope unconditionally via try/finally so that
        no scope leaks even on internal Python errors.
        """
        # Register BEFORE visiting body (self-recursion resolves; no external hoisting).
        self._functions[node.name] = len(node.params)
        self._globals[node.name] = "function"  # top-level code can call it after this point

        # Push local scope (D-07: pure functions — params + local assignments only).
        saved_locals = self._locals
        saved_fn = self._current_fn
        self._locals = {p: "unknown" for p in node.params}
        self._current_fn = node.name
        try:
            for stmt in node.body:
                self._visit(stmt)
        finally:
            # Unconditional restore — scope never leaks regardless of internal errors.
            self._locals = saved_locals
            self._current_fn = saved_fn
        return "unknown"

    def visit_Return(self, node: Return) -> str:
        self._visit(node.value)
        return "unknown"

    def visit_FunctionCall(self, node: FunctionCall) -> str:
        """Visit all args bottom-up, then enforce defined-before-called and arity (SEM-07).

        Built-in helpers (length, str, _atena_concat, _atena_index) are always
        reachable and never arity-checked — they are injected by the analyzer
        itself and have no user-visible arity constraint.
        """
        # Step 1: Visit args first (bottom-up expression evaluation).
        for arg in node.args:
            self._visit(arg)

        # Step 2: Built-in pass-through — never in self._functions, never error.
        if node.name in {"length", "str", "_atena_concat", "_atena_index"}:
            return "unknown"

        # Step 3: Defined-before-called check (no hoisting — D-09, PITFALLS 20).
        if node.name not in self._functions:
            if node.name in self._globals:
                # Name exists but is a variable, not a function.
                self._errors.add(
                    node.line,
                    f'"{node.name}" is not a function — it\'s a value you stored.'
                    ' You cannot call it.',
                    node.source_line,
                )
            else:
                # Completely unknown or defined later in the file.
                candidates = list(self._globals.keys()) + list(ATENA_KEYWORDS)
                hint = suggest(node.name, candidates)
                msg = (
                    f'I don\'t know a function called "{node.name}" yet'
                    ' — define it above this line first.'
                )
                if hint:
                    msg = f'{msg} {hint}'
                self._errors.add(node.line, msg, node.source_line)
            return "unknown"

        # Step 4: Arity check.
        expected = self._functions[node.name]
        given = len(node.args)
        if expected != given:
            plural = "s" if expected != 1 else ""
            self._errors.add(
                node.line,
                f'"{node.name}" expects {expected} value{plural}, but you gave {given}.',
                node.source_line,
            )
        return "unknown"

    def visit_BinOp(self, node: BinOp) -> str:
        """Type-check and coerce the "+" operator (D-01, D-02, D-04).

        Non-"+" operators are not type-checked in v1.0 (D-04).
        For "+":
          - Both types known → consult _COERCE_TABLE for outcome.
          - Either type unknown → convert this BinOp node in-place to a
            FunctionCall("_atena_concat", [left, right]) so Phase 4 can emit
            the runtime helper without re-deriving the decision (D-02).
            In-place node class mutation (node.__class__ = FunctionCall) keeps
            the same object reference visible to all callers (e.g., assign.value)
            without needing parent context.
        """
        left_type = self._visit(node.left)
        right_type = self._visit(node.right)

        if node.op != "+":
            # Non-+ operators: no static type-checking in v1.0 (D-04).
            return "unknown"

        # Short-circuit: if either side is unknown, route through runtime helper (D-02).
        if left_type == "unknown" or right_type == "unknown":
            orig_left = node.left
            orig_right = node.right
            # Convert this BinOp in-place to a FunctionCall so that all references
            # (e.g. assign.value, show.value) immediately see a FunctionCall.
            node.__class__ = FunctionCall  # type: ignore[assignment]
            node.name = "_atena_concat"  # type: ignore[attr-defined]
            node.args = [orig_left, orig_right]  # type: ignore[attr-defined]
            return "unknown"

        # Both types known — consult the coercion table.
        outcome = _COERCE_TABLE.get((left_type, right_type), "error")

        if outcome == "error":
            msg = (
                f"I can't add a {_HUMAN_TYPE.get(left_type, left_type)} and a "
                f"{_HUMAN_TYPE.get(right_type, right_type)} together"
                " — try making them the same kind first."
            )
            self._errors.add(node.line, msg, node.source_line)
            return "unknown"

        if outcome == "coerce_right":
            # Wrap right operand in str() (D-01: string + number/bool)
            node.right = FunctionCall(
                name="str",
                args=[node.right],
                line=node.right.line,
                source_line=node.right.source_line,
            )
            return "str"

        if outcome == "coerce_left":
            # Wrap left operand in str() (D-01: number/bool + string)
            node.left = FunctionCall(
                name="str",
                args=[node.left],
                line=node.left.line,
                source_line=node.left.source_line,
            )
            return "str"

        # outcome == "no_coerce": both sides same type, no wrapping needed.
        return left_type

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
        """Rewrite 1-based literal indices to 0-based; route dynamic indices
        through the _atena_index runtime helper (D-05, D-06).

        Idempotency: the index_converted flag prevents a double-shift when the
        same node is visited more than once (PITFALLS 6).  For nested access
        like grid[2][3], visiting the outer node triggers _visit(inner_node)
        first (step 1 below), so the inner rewrite happens before the outer.
        """
        # Step 1: Visit the target first so nested IndexAccess rewrites happen
        # bottom-up (inner subscript shifts before outer).
        self._visit(node.target)

        # Step 2: Idempotency guard — never shift an already-converted index.
        if node.index_converted:
            self._visit(node.index)
            return "unknown"

        # Step 3: Literal positive / zero / negative index — resolved at compile time.
        if isinstance(node.index, NumberLiteral):
            if node.index.value == 0:
                # Compile-time literal 0: canonical error (SEM-04).
                self._errors.add(
                    node.line,
                    "Lists in Atena start at 1, not 0.",
                    node.source_line,
                )
                # Do NOT rewrite; do NOT set index_converted.
            else:
                # Positive literal n: fold 1-based → 0-based in place.
                node.index.value -= 1
                node.index_converted = True

        # Step 4: Literal negative index (UnaryOp "-" wrapping a NumberLiteral).
        # Negatives parsed as UnaryOp("-", NumberLiteral) — distinct message (D-06).
        elif (
            isinstance(node.index, UnaryOp)
            and node.index.op == "-"
            and isinstance(node.index.operand, NumberLiteral)
        ):
            self._errors.add(
                node.line,
                "Atena lists count from 1 — there are no negative positions."
                " The last item is at length, not -1.",
                node.source_line,
            )
            # Do NOT rewrite; do NOT set index_converted.

        # Step 5: Dynamic index — any Identifier, BinOp, FunctionCall result, etc.
        # Route through _atena_index runtime helper so the 1→0 shift and the
        # i < 1 bound check happen at runtime (D-05, PITFALLS 5).
        else:
            orig_index = node.index
            helper = FunctionCall(
                name="_atena_index",
                args=[orig_index],
                line=node.line,
                source_line=node.source_line,
            )
            node.index = helper
            node.index_converted = True

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
        """Look up the identifier's type in the current scope.

        Four-case resolution (SEM-06, D-08, D-09):
        1. Name in current scope → return its type (no error).
        2. Inside a function and name is a known function → return "unknown"
           (callable, not a value; type irrelevant here).
        3. Inside a function and name is a top-level variable → D-08 tailored
           teaching message; poison in locals to suppress cascade.
        4. Fully undefined → generic "don't know what X is" + suggest() hint;
           poison in current scope to suppress cascade errors (PITFALLS 12).
        """
        name = node.name
        # Case 1: Check the current execution scope first.
        scope = self._locals if self._locals is not None else self._globals
        if name in scope:
            return scope[name]

        # Case 2: Inside a function — can still call earlier-defined functions.
        if self._locals is not None and name in self._functions:
            return "unknown"

        # Case 3: Inside a function — name exists at top level but is not in
        # local scope (D-08 tailored outer-variable teaching message).
        if self._locals is not None and name in self._globals:
            self._errors.add(
                node.line,
                f'A function can only use its own inputs — pass "{name}" in as a parameter.',
                node.source_line,
            )
            self._locals[name] = "unknown"  # poison in locals to suppress cascade
            return "unknown"

        # Case 4: Fully undefined — generic error with suggest() hint.
        candidates = list(scope.keys()) + list(ATENA_KEYWORDS)
        hint = suggest(name, candidates)
        msg = f'I don\'t know what "{name}" is yet. Did you forget to create it first?'
        if hint:
            msg = f'{msg} {hint}'
        self._errors.add(node.line, msg, node.source_line)
        scope[name] = "unknown"  # poison: suppress cascade errors (D-09, PITFALLS 12)
        return "unknown"

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        return "number"

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        return "str"

    def visit_BoolLiteral(self, node: BoolLiteral) -> str:
        return "bool"
