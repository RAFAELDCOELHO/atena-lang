"""
AST node dataclasses for the Atena transpiler.

Pure data module — no sibling-module imports. Every phase and test can
import this freely without creating circular dependencies. Nodes are
mutable @dataclasses so the semantic analyzer can rewrite them in place
(1→0 index rewrite, str() coercion injection).

All nodes carry `line: int` and `source_line: str` so any downstream
phase can produce "Error on line {N}: … → {source_line}" without
re-reading the file (DIAG-01).

Exports: Node, Program, Assign, Show, Ask, If, While, Repeat,
         FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
         ListLiteral, DictLiteral, IndexAccess, DotAccess,
         ListAdd, ListRemove, Identifier, NumberLiteral,
         StringLiteral, BoolLiteral
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Base node
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """Base class for all Atena AST nodes.

    Every node carries the 1-based line number of the corresponding source
    token (and the full text of that source line) so error messages can
    point to the exact line without re-reading the file.

    Concrete node subclasses add their structural fields AFTER the
    positional `line` field.  `source_line` defaults to "" so callers can
    omit it during simple construction while tests that need it can supply
    it explicitly.
    """

    line: int = 0
    source_line: str = ""


# ---------------------------------------------------------------------------
# Concrete statement nodes
# ---------------------------------------------------------------------------


@dataclass
class Program(Node):
    """Root node of an Atena program — a list of top-level statements."""

    statements: list[Node] = field(default_factory=list)


@dataclass
class Assign(Node):
    """Variable assignment: `name = value`."""

    name: str = ""
    value: Node = field(default_factory=lambda: Node())


@dataclass
class Show(Node):
    """Print statement: `show value`."""

    value: Node = field(default_factory=lambda: Node())


@dataclass
class Ask(Node):
    """Input statement: `ask "prompt" into target`."""

    prompt: str = ""
    target: str = ""


@dataclass
class If(Node):
    """Conditional: `if condition … (else …)`."""

    condition: Node = field(default_factory=lambda: Node())
    then_body: list[Node] = field(default_factory=list)
    else_body: list[Node] = field(default_factory=list)


@dataclass
class While(Node):
    """While loop: `while condition …`."""

    condition: Node = field(default_factory=lambda: Node())
    body: list[Node] = field(default_factory=list)


@dataclass
class Repeat(Node):
    """Count-controlled loop: `repeat count times …`."""

    count: Node = field(default_factory=lambda: Node())
    body: list[Node] = field(default_factory=list)


@dataclass
class FunctionDef(Node):
    """Function definition: `function name(params) …`."""

    name: str = ""
    params: list[str] = field(default_factory=list)
    body: list[Node] = field(default_factory=list)


@dataclass
class Return(Node):
    """Return statement: `return value`."""

    value: Node = field(default_factory=lambda: Node())


# ---------------------------------------------------------------------------
# Expression nodes
# ---------------------------------------------------------------------------


@dataclass
class FunctionCall(Node):
    """Function call expression: `name(args)`."""

    name: str = ""
    args: list[Node] = field(default_factory=list)


@dataclass
class BinOp(Node):
    """Binary operation: `left op right`.

    `op` is the operator string: "+", "-", "*", "/", "and", "or",
    "==", "!=", "<", ">", "<=", ">=".
    """

    op: str = ""
    left: Node = field(default_factory=lambda: Node())
    right: Node = field(default_factory=lambda: Node())


@dataclass
class UnaryOp(Node):
    """Unary operation: `op operand`.

    `op` is "not" or "-".
    """

    op: str = ""
    operand: Node = field(default_factory=lambda: Node())


@dataclass
class ListLiteral(Node):
    """List literal: `[elem, elem, …]`."""

    elements: list[Node] = field(default_factory=list)


@dataclass
class DictLiteral(Node):
    """Dict literal: `{key = value, …}`.

    `pairs` is a list of `(key_str, value_node)` tuples.
    """

    pairs: list[tuple[str, Node]] = field(default_factory=list)


@dataclass
class IndexAccess(Node):
    """Index access: `target[index]`.

    `index_converted` is set to True by the semantic analyzer after the
    1→0 index rewrite (ARCHITECTURE.md Pattern 11).  Defaults to False.
    The flag prevents the analyzer from shifting the index a second time
    if it visits the node again.
    """

    target: Node = field(default_factory=lambda: Node())
    index: Node = field(default_factory=lambda: Node())
    index_converted: bool = False


@dataclass
class DotAccess(Node):
    """Dot (attribute) access for dict fields: `target.name`."""

    target: Node = field(default_factory=lambda: Node())
    name: str = ""


@dataclass
class ListAdd(Node):
    """List append statement: `add value to target`."""

    target: str = ""
    value: Node = field(default_factory=lambda: Node())


@dataclass
class ListRemove(Node):
    """List remove statement: `remove value from target`."""

    target: str = ""
    value: Node = field(default_factory=lambda: Node())


# ---------------------------------------------------------------------------
# Leaf / literal nodes
# ---------------------------------------------------------------------------


@dataclass
class Identifier(Node):
    """A user-defined name (variable or parameter reference)."""

    name: str = ""


@dataclass
class NumberLiteral(Node):
    """An integer literal value."""

    value: int = 0


@dataclass
class StringLiteral(Node):
    """A double-quoted string literal value."""

    value: str = ""


@dataclass
class BoolLiteral(Node):
    """A boolean literal: `true` or `false`."""

    value: bool = False
