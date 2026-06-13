"""Tests for the AST node data contracts (ast_nodes.py).

Plan 00-03 — RED phase: all tests must FAIL against the stub implementation.
"""

from __future__ import annotations

import sys

import pytest


def test_A1_all_22_node_types_importable():
    """All 22 concrete AST node types are importable in one statement."""
    from atena.ast_nodes import (
        Assign,
        Ask,
        BinOp,
        BoolLiteral,
        DictLiteral,
        DotAccess,
        FunctionCall,
        FunctionDef,
        Identifier,
        If,
        IndexAccess,
        ListAdd,
        ListLiteral,
        ListRemove,
        Node,
        NumberLiteral,
        Program,
        Repeat,
        Return,
        Show,
        StringLiteral,
        UnaryOp,
        While,
    )
    # If we get here, all 22 node types (+ Node base) are importable.
    assert True


def test_A2_program_construction_and_line():
    """Program node constructs and exposes line field."""
    from atena.ast_nodes import Program

    prog = Program(statements=[], line=0)
    assert prog.line == 0
    assert prog.statements == []


def test_A3_binop_construction():
    """BinOp constructs correctly and op field is accessible."""
    from atena.ast_nodes import BinOp, NumberLiteral

    binop = BinOp(
        op="+",
        left=NumberLiteral(value=1, line=1),
        right=NumberLiteral(value=2, line=1),
        line=1,
    )
    assert binop.op == "+"
    assert binop.left.value == 1
    assert binop.right.value == 2


def test_A4_assign_equality_via_dataclass():
    """Two identical Assign nodes compare equal."""
    from atena.ast_nodes import Assign, NumberLiteral

    a1 = Assign(name="x", value=NumberLiteral(value=5, line=1), line=1)
    a2 = Assign(name="x", value=NumberLiteral(value=5, line=1), line=1)
    assert a1 == a2


def test_A5_index_access_converted_defaults_false():
    """IndexAccess.index_converted defaults to False."""
    from atena.ast_nodes import Identifier, IndexAccess, NumberLiteral

    node = IndexAccess(
        target=Identifier(name="items", line=2),
        index=NumberLiteral(value=1, line=2),
        line=2,
    )
    assert node.index_converted is False


def test_A6_ast_nodes_import_isolation():
    """Importing atena.ast_nodes does NOT pull in atena.errors, tokens, cli, or pipeline."""
    # Ensure a fresh import state check — capture modules before we import
    # (The module may already be loaded from other tests; isolation still holds
    # since ast_nodes never imports those siblings.)
    import importlib

    # Remove the module from sys.modules to force a fresh import
    for mod in list(sys.modules.keys()):
        if mod.startswith("atena"):
            del sys.modules[mod]

    importlib.import_module("atena.ast_nodes")

    assert "atena.errors" not in sys.modules, "ast_nodes must not import atena.errors"
    assert "atena.tokens" not in sys.modules, "ast_nodes must not import atena.tokens"
    assert "atena.cli" not in sys.modules, "ast_nodes must not import atena.cli"
    assert "atena.pipeline" not in sys.modules, "ast_nodes must not import atena.pipeline"


def test_A7_dict_literal_construction():
    """DictLiteral with a string-keyed pair constructs correctly."""
    from atena.ast_nodes import DictLiteral, StringLiteral

    node = DictLiteral(
        pairs=[("name", StringLiteral(value="Ana", line=5))],
        line=5,
    )
    assert len(node.pairs) == 1
    assert node.pairs[0][0] == "name"
    assert node.pairs[0][1].value == "Ana"
