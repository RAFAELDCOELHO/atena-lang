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
# Operator maps for BinOp dispatch
# ---------------------------------------------------------------------------

_ARITH_OPS: dict[str, ast.operator] = {
    "+": ast.Add(),
    "-": ast.Sub(),
    "*": ast.Mult(),
    "/": ast.Div(),
}

_CMP_OPS: dict[str, ast.cmpop] = {
    "==": ast.Eq(),
    "!=": ast.NotEq(),
    "<": ast.Lt(),
    "<=": ast.LtE(),
    ">": ast.Gt(),
    ">=": ast.GtE(),
}

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

    def build_module(self) -> ast.Module:
        """Build the Python ``ast.Module`` for the program.

        Each emitted Python node carries the ``lineno`` of the Atena source
        line it came from (set in ``_emit``/``_emit_as_stmt``), so compiling
        this module directly — rather than the unparsed string — yields a code
        object whose runtime tracebacks report the learner's ORIGINAL Atena
        line, not a line in the generated Python (CR-01).  The ``atena run``
        path compiles this module; ``generate()`` unparses it for ``build``.
        """
        body_stmts: list[ast.stmt] = []
        for stmt in self._program.statements:
            result = self._emit_as_stmt(stmt)
            if isinstance(result, list):
                body_stmts.extend(result)
            else:
                body_stmts.append(result)  # type: ignore[arg-type]

        # Prepend on-demand helper bodies (GEN-04, Claude's Discretion: on-demand)
        preamble = self._build_preamble()
        module = ast.Module(body=preamble + body_stmts, type_ignores=[])
        # fix_missing_locations fills any unstamped node (and propagates a
        # parent's Atena lineno down to children that lack one).
        ast.fix_missing_locations(module)
        return module

    def generate(self) -> str:
        """Walk all top-level statements; return the Python source string.

        Applies the three D-02 post-patches after ast.unparse():
        1. Restore double-quoted strings (single-quote -> double-quote, carefully).
        2. Blank lines between top-level function definitions.
        3. Header comment at the top.
        Then runs ast.parse() self-check (GEN-05) — a failure here is an
        internal bug, not a user error.

        Line numbers are irrelevant to this string form (``ast.unparse`` ignores
        them); the Atena-line provenance is consumed only via ``build_module()``
        on the run path.
        """
        module = self.build_module()
        python_source = ast.unparse(module)

        # D-02 post-patches
        python_source = self._patch_double_quotes(python_source)
        python_source = self._patch_blank_lines(python_source)
        python_source = self._patch_header(python_source)

        # GEN-05 self-check — always run after patches
        ast.parse(python_source)   # raises SyntaxError on internal bug
        return python_source

    # -----------------------------------------------------------------------
    # D-02 post-patches
    # -----------------------------------------------------------------------

    def _patch_double_quotes(self, src: str) -> str:
        """Restore double-quoted strings after ast.unparse() singles them.

        Uses a targeted regex: replaces 'content' with "content" only when
        content contains no single-quote or backslash.  Strings that contain
        a single quote are already emitted with double-quotes by ast.unparse()
        so they won't match the pattern.  GEN-05 ast.parse() self-check runs
        after this to catch any regex regression.
        """
        return re.sub(r"'([^'\\]*)'", r'"\1"', src)

    def _patch_blank_lines(self, src: str) -> str:
        """Insert a blank line before each top-level 'def' that lacks one.

        Applies once (not globally) to avoid triple-blank-lines.
        """
        return re.sub(r"\n(def )", r"\n\n\1", src)

    def _patch_header(self, src: str) -> str:
        """Prepend a friendly header comment at the top of the source."""
        return "# Generated by Atena\n" + src

    # -----------------------------------------------------------------------
    # Preamble (on-demand helper bodies)
    # -----------------------------------------------------------------------

    def _build_preamble(self) -> list[ast.stmt]:
        """Emit helper function bodies only when the program uses them."""
        stmts: list[ast.stmt] = []
        if "_atena_index" in self._used_helpers:
            stmts.extend(_parse_helper(_ATENA_INDEX_SRC))
        if "_atena_concat" in self._used_helpers:
            stmts.extend(_parse_helper(_ATENA_CONCAT_SRC))
        return stmts

    # -----------------------------------------------------------------------
    # Dispatch
    # -----------------------------------------------------------------------

    @staticmethod
    def _stamp(py_node: ast.AST, atena_node: Node) -> None:
        """Carry the Atena source line onto the emitted Python node (CR-01).

        Only ``lineno``/``end_lineno`` are set — that is all a runtime traceback
        needs to point at the learner's line.  Column offsets are left to
        ``fix_missing_locations``.  Nodes without a real line (e.g. analyzer-
        injected coercions) are skipped and inherit their parent's line.
        """
        line = getattr(atena_node, "line", 0)
        if isinstance(line, int) and line > 0 and isinstance(py_node, (ast.stmt, ast.expr)):
            py_node.lineno = line
            py_node.end_lineno = line

    def _emit(self, node: Node) -> ast.stmt | ast.expr:
        """Dispatch to _emit_<NodeType>; raise TypeError for unknown nodes."""
        method = getattr(self, f"_emit_{type(node).__name__}", self._emit_default)
        result = method(node)
        self._stamp(result, node)
        return result

    def _emit_as_stmt(self, node: Node) -> ast.stmt | list[ast.stmt]:
        """Emit node as a statement, wrapping bare expressions in ast.Expr.

        FunctionCall at statement level (e.g. top-level `greet("Ana")` or
        inside a body list) returns ast.Call (an expr).  Python's AST requires
        expression-statements to be wrapped in ast.Expr — without the wrapper
        ast.unparse() concatenates the call to the preceding statement on the
        same line, producing a SyntaxError.
        """
        result = self._emit(node)
        if isinstance(result, ast.expr):
            wrapper = ast.Expr(value=result)
            self._stamp(wrapper, node)
            return wrapper
        return result  # type: ignore[return-value]

    def _emit_default(self, node: Node) -> ast.expr:
        """Fallthrough for unhandled node types — always an internal bug."""
        raise TypeError(
            f"CodeGenerator has no emitter for {type(node).__name__}. "
            "This is an internal Atena bug."
        )

    # -----------------------------------------------------------------------
    # Statement emitters
    # -----------------------------------------------------------------------

    def _emit_Program(self, node: Program) -> list[ast.stmt]:
        """Emit all statements in a Program node (used only if Program is nested)."""
        return [self._emit(s) for s in node.statements]  # type: ignore[return-value]

    def _emit_Assign(self, node: Assign) -> ast.Assign:
        """name = value  OR  target.field = value (dot-write via _dot_target)."""
        if hasattr(node, "_dot_target"):
            # Dot-write: student.grade = 10  ->  student["grade"] = 10
            dot: DotAccess = node._dot_target  # type: ignore[attr-defined]
            target_ast: ast.expr = ast.Subscript(
                value=self._emit(dot.target),  # type: ignore[arg-type]
                slice=ast.Constant(value=dot.name),
                ctx=ast.Store(),
            )
        else:
            target_ast = ast.Name(id=_mangle(node.name), ctx=ast.Store())

        return ast.Assign(
            targets=[target_ast],
            value=self._emit(node.value),  # type: ignore[arg-type]
        )

    def _emit_Show(self, node: Show) -> ast.Expr:
        """show value  ->  print(value)"""
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[self._emit(node.value)],  # type: ignore[list-item]
                keywords=[],
            )
        )

    def _emit_Ask(self, node: Ask) -> ast.Assign:
        """ask "prompt" into target  ->  target = input("prompt")"""
        return ast.Assign(
            targets=[ast.Name(id=_mangle(node.target), ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id="input", ctx=ast.Load()),
                args=[ast.Constant(value=node.prompt)],
                keywords=[],
            ),
        )

    def _emit_If(self, node: If) -> ast.If:
        """if condition ... (else ...)  ->  ast.If"""
        return ast.If(
            test=self._emit(node.condition),  # type: ignore[arg-type]
            body=[self._emit_as_stmt(s) for s in node.then_body],  # type: ignore[list-item]
            orelse=[self._emit_as_stmt(s) for s in node.else_body],  # type: ignore[list-item]
        )

    def _emit_While(self, node: While) -> ast.While:
        """while condition ...  ->  ast.While"""
        return ast.While(
            test=self._emit(node.condition),  # type: ignore[arg-type]
            body=[self._emit_as_stmt(s) for s in node.body],  # type: ignore[list-item]
            orelse=[],
        )

    def _emit_Repeat(self, node: Repeat) -> ast.For:
        """repeat N times  ->  for _atena_i{counter} in range(N):

        Loop counter is MONOTONIC — incremented before emitting the body,
        never decremented afterward.  This guarantees unique loop variable
        names across the entire program regardless of nesting depth.
        """
        loop_var = f"_atena_i{self._loop_counter}"
        self._loop_counter += 1  # monotonic: never decrement
        body = [self._emit_as_stmt(s) for s in node.body]  # type: ignore[list-item]
        return ast.For(
            target=ast.Name(id=loop_var, ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id="range", ctx=ast.Load()),
                args=[self._emit(node.count)],  # type: ignore[list-item]
                keywords=[],
            ),
            body=body,  # type: ignore[arg-type]
            orelse=[],
        )

    def _emit_FunctionDef(self, node: FunctionDef) -> ast.FunctionDef:
        """function name(params) ...  ->  def name(params): ..."""
        return ast.FunctionDef(
            name=_mangle(node.name),
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=_mangle(p)) for p in node.params],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=[self._emit_as_stmt(s) for s in node.body] or [ast.Pass()],  # type: ignore[list-item]
            decorator_list=[],
        )

    def _emit_Return(self, node: Return) -> ast.Return:
        """return value  ->  ast.Return"""
        return ast.Return(value=self._emit(node.value))  # type: ignore[arg-type]

    def _emit_ListAdd(self, node: ListAdd) -> ast.Expr:
        """add value to target  ->  target.append(value)"""
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=_mangle(node.target), ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
                args=[self._emit(node.value)],  # type: ignore[list-item]
                keywords=[],
            )
        )

    def _emit_ListRemove(self, node: ListRemove) -> ast.Expr:
        """remove value from target  ->  target.remove(value)"""
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=_mangle(node.target), ctx=ast.Load()),
                    attr="remove",
                    ctx=ast.Load(),
                ),
                args=[self._emit(node.value)],  # type: ignore[list-item]
                keywords=[],
            )
        )

    # -----------------------------------------------------------------------
    # Expression emitters
    # -----------------------------------------------------------------------

    def _emit_FunctionCall(self, node: FunctionCall) -> ast.expr:
        """name(args)  ->  ast.Call

        Tracks helper usage for on-demand preamble emission.
        Special cases:
          - "length" → len(...) (Atena keyword maps to Python builtin)
          - "str" → str(...) (coercion injected by analyzer, emitted verbatim)
          - "_atena_concat"/"_atena_index" → add to _used_helpers, then emit normally
        """
        func_name = node.name

        # Atena "length" keyword → Python "len" builtin (GEN-02 mapping)
        if func_name == "length":
            return ast.Call(
                func=ast.Name(id="len", ctx=ast.Load()),
                args=[self._emit(a) for a in node.args],  # type: ignore[list-item]
                keywords=[],
            )

        if func_name in ("_atena_concat", "_atena_index"):
            self._used_helpers.add(func_name)

        # GEN-04: mangle Python-keyword user-function names so the call site
        # matches the mangled definition site (e.g. 'pass' → 'pass_').
        # _mangle() is a no-op for non-keywords (including the _atena_* helpers
        # and "str"), so this is safe for all branches above.
        return ast.Call(
            func=ast.Name(id=_mangle(func_name), ctx=ast.Load()),
            args=[self._emit(a) for a in node.args],  # type: ignore[list-item]
            keywords=[],
        )

    def _emit_BinOp(self, node: BinOp) -> ast.expr:
        """Binary operation — dispatches to ast.BinOp, ast.Compare, or ast.BoolOp."""
        op = node.op
        left = self._emit(node.left)   # type: ignore[arg-type]
        right = self._emit(node.right)  # type: ignore[arg-type]

        if op in _ARITH_OPS:
            return ast.BinOp(left=left, op=_ARITH_OPS[op], right=right)  # type: ignore[arg-type]

        if op in _CMP_OPS:
            return ast.Compare(left=left, ops=[_CMP_OPS[op]], comparators=[right])  # type: ignore[arg-type]

        if op == "and":
            return ast.BoolOp(op=ast.And(), values=[left, right])  # type: ignore[list-item]

        if op == "or":
            return ast.BoolOp(op=ast.Or(), values=[left, right])  # type: ignore[list-item]

        raise TypeError(
            f"CodeGenerator._emit_BinOp: unknown operator {op!r}. "
            "This is an internal Atena bug."
        )

    def _emit_UnaryOp(self, node: UnaryOp) -> ast.expr:
        """Unary operation: 'not' -> ast.Not(), '-' -> ast.USub()."""
        operand = self._emit(node.operand)  # type: ignore[arg-type]
        if node.op == "not":
            return ast.UnaryOp(op=ast.Not(), operand=operand)  # type: ignore[arg-type]
        if node.op == "-":
            return ast.UnaryOp(op=ast.USub(), operand=operand)  # type: ignore[arg-type]
        raise TypeError(
            f"CodeGenerator._emit_UnaryOp: unknown operator {node.op!r}. "
            "This is an internal Atena bug."
        )

    def _emit_ListLiteral(self, node: ListLiteral) -> ast.List:
        """[elem, ...]  ->  ast.List"""
        return ast.List(
            elts=[self._emit(e) for e in node.elements],  # type: ignore[list-item]
            ctx=ast.Load(),
        )

    def _emit_DictLiteral(self, node: DictLiteral) -> ast.Dict:
        """{key = value, ...}  ->  {"key": value, ...}"""
        keys: list[ast.expr] = [ast.Constant(value=k) for k, _ in node.pairs]
        values: list[ast.expr] = [self._emit(v) for _, v in node.pairs]  # type: ignore[misc]
        return ast.Dict(keys=keys, values=values)

    def _emit_IndexAccess(self, node: IndexAccess) -> ast.Subscript:
        """target[index]  ->  ast.Subscript (index already 0-based from analyzer)."""
        return ast.Subscript(
            value=self._emit(node.target),  # type: ignore[arg-type]
            slice=self._emit(node.index),   # type: ignore[arg-type]
            ctx=ast.Load(),
        )

    def _emit_DotAccess(self, node: DotAccess) -> ast.Subscript:
        """student.name  ->  student["name"]"""
        return ast.Subscript(
            value=self._emit(node.target),  # type: ignore[arg-type]
            slice=ast.Constant(value=node.name),
            ctx=ast.Load(),
        )

    def _emit_Identifier(self, node: Identifier) -> ast.Name:
        """Variable reference  ->  ast.Name(id=mangled_name, ctx=Load)"""
        return ast.Name(id=_mangle(node.name), ctx=ast.Load())

    def _emit_NumberLiteral(self, node: NumberLiteral) -> ast.Constant:
        """Integer literal  ->  ast.Constant(value=int)"""
        return ast.Constant(value=node.value)

    def _emit_StringLiteral(self, node: StringLiteral) -> ast.Constant:
        """String literal  ->  ast.Constant(value=str)

        ast.unparse() will emit single quotes; the D-02 double-quote patch
        restores them post-unparse.
        """
        return ast.Constant(value=node.value)

    def _emit_BoolLiteral(self, node: BoolLiteral) -> ast.Constant:
        """Boolean literal  ->  ast.Constant(value=True/False)"""
        return ast.Constant(value=node.value)
