"""
AST node dataclasses for the Atena transpiler.

Pure data module — no sibling-module imports. Every phase and test can
import this freely without creating circular dependencies. Nodes are
mutable @dataclasses so the semantic analyzer can rewrite them in place
(1→0 index rewrite, str() coercion injection).

TODO: full node-set implemented in Plan 03
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """Base class for all Atena AST nodes.

    Every node carries the 1-based line number of the corresponding
    source token so error messages can point to the exact line.

    TODO: implemented in Plan 03
    """

    line: int


@dataclass
class Program(Node):
    """Root node of an Atena program — a list of top-level statements.

    TODO: implemented in Plan 03
    """

    statements: list = field(default_factory=list)
