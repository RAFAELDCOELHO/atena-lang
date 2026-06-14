"""
TDD tests for the Atena Parser — Phase 2 RED phase.

Layer 1 (golden AST snapshots): parse a valid snippet, assert produced node
    equals the expected node literal using @dataclass __eq__. All tests in
    this layer fail until Plans 02-03 implement the full statement and
    expression dispatch.

Layer 2 (error-path tests): feed malformed source, assert exact key phrase in
    ec.report(), error count, and line numbers — no crash, no hang. Fails
    until Plan 03-04 implement the Python-ism redirects and validation.

Layer 3 (cross-requirement tests): multiple errors collected in one run, no
    infinite loop on malformed input, progress invariant holds. Fails until
    Plans 03-04 prove the recovery works across compound inputs.
"""

from __future__ import annotations

import pytest

from atena.tokens import TokenType, Token
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


def _parse(source: str) -> tuple[Program, ErrorCollector]:
    """Helper: lex + parse source and return (program_ast, errors) for inspection.

    Chains through the real Lexer so tests use production token streams.
    The ErrorCollector is shared across both phases — lexer and parser
    both append to the same collector (matching the pipeline contract).
    """
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    program = Parser(tokens, ec).parse()
    return program, ec


# ---------------------------------------------------------------------------
# Layer 1 — Golden AST snapshot tests (PARSE-01 through PARSE-05)
# ---------------------------------------------------------------------------


def test_P1_assign_number():
    """'x = 5' produces Assign(name='x', value=NumberLiteral(value=5)) on line 1."""
    program, ec = _parse("x = 5\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert stmt.name == "x"
    assert isinstance(stmt.value, NumberLiteral)
    assert stmt.value.value == 5


def test_P1_assign_string():
    """'name = "Ana"' produces Assign(name='name', value=StringLiteral(value='Ana'))."""
    program, ec = _parse('name = "Ana"\n')
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert stmt.name == "name"
    assert isinstance(stmt.value, StringLiteral)
    assert stmt.value.value == "Ana"


def test_P1_assign_bool_true():
    """'flag = true' produces Assign(name='flag', value=BoolLiteral(value=True))."""
    program, ec = _parse("flag = true\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert stmt.name == "flag"
    assert isinstance(stmt.value, BoolLiteral)
    assert stmt.value.value is True


def test_P1_assign_bool_false():
    """'flag = false' produces Assign(name='flag', value=BoolLiteral(value=False))."""
    program, ec = _parse("flag = false\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert stmt.name == "flag"
    assert isinstance(stmt.value, BoolLiteral)
    assert stmt.value.value is False


def test_P1_show_string():
    """'show "hello"' produces Show(value=StringLiteral(value='hello'))."""
    program, ec = _parse('show "hello"\n')
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Show)
    assert isinstance(stmt.value, StringLiteral)
    assert stmt.value.value == "hello"


def test_P1_show_identifier():
    """'show x' produces Show(value=Identifier(name='x'))."""
    program, ec = _parse("show x\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Show)
    assert isinstance(stmt.value, Identifier)
    assert stmt.value.name == "x"


def test_P1_ask_basic():
    """'name = ask "What is your name?" produces Ask(prompt=..., target="name") as the statement.

    Per D-01/D-02: ask is a dedicated statement form. 'name = ask "..."' maps to
    Ask(prompt="What is your name?", target="name") — NOT Assign wrapping Ask.
    The Ask node carries both prompt and target, so it IS the statement node.
    """
    program, ec = _parse('name = ask "What is your name?"\n')
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Ask)
    assert stmt.prompt == "What is your name?"
    assert stmt.target == "name"


def test_P1_binop_add():
    """'x = 2 + 3' produces Assign with BinOp(op='+', left=NumberLiteral(2), right=NumberLiteral(3))."""
    program, ec = _parse("x = 2 + 3\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, BinOp)
    assert stmt.value.op == "+"
    assert isinstance(stmt.value.left, NumberLiteral)
    assert stmt.value.left.value == 2
    assert isinstance(stmt.value.right, NumberLiteral)
    assert stmt.value.right.value == 3


def test_P1_binop_precedence_mul_over_add():
    """'x = 2 + 3 * 4' → * binds tighter: BinOp('+', NumberLiteral(2), BinOp('*', 3, 4))."""
    program, ec = _parse("x = 2 + 3 * 4\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, BinOp)
    assert val.op == "+"
    assert isinstance(val.left, NumberLiteral)
    assert val.left.value == 2
    assert isinstance(val.right, BinOp)
    assert val.right.op == "*"
    assert isinstance(val.right.left, NumberLiteral)
    assert val.right.left.value == 3
    assert isinstance(val.right.right, NumberLiteral)
    assert val.right.right.value == 4


def test_P1_left_associativity():
    """'x = 10 - 3 - 2' → left-assoc: BinOp('-', BinOp('-', 10, 3), 2)."""
    program, ec = _parse("x = 10 - 3 - 2\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, BinOp)
    assert val.op == "-"
    assert isinstance(val.left, BinOp)
    assert val.left.op == "-"
    assert isinstance(val.left.left, NumberLiteral)
    assert val.left.left.value == 10
    assert isinstance(val.left.right, NumberLiteral)
    assert val.left.right.value == 3
    assert isinstance(val.right, NumberLiteral)
    assert val.right.value == 2


def test_P1_unary_minus():
    """'x = -5' produces Assign with UnaryOp(op='-', operand=NumberLiteral(5))."""
    program, ec = _parse("x = -5\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, UnaryOp)
    assert stmt.value.op == "-"
    assert isinstance(stmt.value.operand, NumberLiteral)
    assert stmt.value.operand.value == 5


def test_P1_unary_minus_binary():
    """'x = a - -b' → BinOp('-', Identifier('a'), UnaryOp('-', Identifier('b')))."""
    program, ec = _parse("x = a - -b\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, BinOp)
    assert val.op == "-"
    assert isinstance(val.left, Identifier)
    assert val.left.name == "a"
    assert isinstance(val.right, UnaryOp)
    assert val.right.op == "-"
    assert isinstance(val.right.operand, Identifier)
    assert val.right.operand.name == "b"


def test_P1_logical_and():
    """'x = a and b' produces BinOp(op='and', left=Identifier('a'), right=Identifier('b'))."""
    program, ec = _parse("x = a and b\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, BinOp)
    assert val.op == "and"
    assert isinstance(val.left, Identifier)
    assert val.left.name == "a"
    assert isinstance(val.right, Identifier)
    assert val.right.name == "b"


def test_P1_logical_or_lower_than_and():
    """'x = a or b and c' → or has lower precedence: BinOp('or', a, BinOp('and', b, c))."""
    program, ec = _parse("x = a or b and c\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, BinOp)
    assert val.op == "or"
    assert isinstance(val.left, Identifier)
    assert val.left.name == "a"
    assert isinstance(val.right, BinOp)
    assert val.right.op == "and"
    assert isinstance(val.right.left, Identifier)
    assert val.right.left.name == "b"
    assert isinstance(val.right.right, Identifier)
    assert val.right.right.name == "c"


def test_P1_not_unary():
    """'x = not a' produces Assign with UnaryOp(op='not', operand=Identifier('a'))."""
    program, ec = _parse("x = not a\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, UnaryOp)
    assert stmt.value.op == "not"
    assert isinstance(stmt.value.operand, Identifier)
    assert stmt.value.operand.name == "a"


def test_P1_comparison():
    """'x = a == b' produces Assign with BinOp(op='==', left=Identifier('a'), right=Identifier('b'))."""
    program, ec = _parse("x = a == b\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, BinOp)
    assert val.op == "=="
    assert isinstance(val.left, Identifier)
    assert val.left.name == "a"
    assert isinstance(val.right, Identifier)
    assert val.right.name == "b"


def test_P1_postfix_index():
    """'x = items[1]' → IndexAccess(target=Identifier('items'), index=NumberLiteral(1), index_converted=False)."""
    program, ec = _parse("x = items[1]\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, IndexAccess)
    assert isinstance(val.target, Identifier)
    assert val.target.name == "items"
    assert isinstance(val.index, NumberLiteral)
    assert val.index.value == 1
    assert val.index_converted is False


def test_P1_postfix_chain_double_index():
    """'x = grid[2][3]' → IndexAccess(IndexAccess(Identifier('grid'), 2), 3), both index_converted=False."""
    program, ec = _parse("x = grid[2][3]\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    outer = stmt.value
    assert isinstance(outer, IndexAccess)
    assert outer.index_converted is False
    assert isinstance(outer.index, NumberLiteral)
    assert outer.index.value == 3
    inner = outer.target
    assert isinstance(inner, IndexAccess)
    assert inner.index_converted is False
    assert isinstance(inner.target, Identifier)
    assert inner.target.name == "grid"
    assert isinstance(inner.index, NumberLiteral)
    assert inner.index.value == 2


def test_P1_dot_access():
    """'x = student.name' produces Assign with DotAccess(target=Identifier('student'), name='name')."""
    program, ec = _parse("x = student.name\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, DotAccess)
    assert isinstance(val.target, Identifier)
    assert val.target.name == "student"
    assert val.name == "name"


def test_P1_function_call():
    """'greet()' as a bare statement → FunctionCall(name='greet', args=[])."""
    program, ec = _parse("greet()\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, FunctionCall)
    assert stmt.name == "greet"
    assert stmt.args == []


def test_P1_function_call_args():
    """'greet("Ana", 5)' → FunctionCall(name='greet', args=[StringLiteral('Ana'), NumberLiteral(5)])."""
    program, ec = _parse('greet("Ana", 5)\n')
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, FunctionCall)
    assert stmt.name == "greet"
    assert len(stmt.args) == 2
    assert isinstance(stmt.args[0], StringLiteral)
    assert stmt.args[0].value == "Ana"
    assert isinstance(stmt.args[1], NumberLiteral)
    assert stmt.args[1].value == 5


def test_P1_list_literal():
    """'x = [1, 2, 3]' → Assign with ListLiteral(elements=[NumberLiteral(1), NumberLiteral(2), NumberLiteral(3)])."""
    program, ec = _parse("x = [1, 2, 3]\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, ListLiteral)
    assert len(val.elements) == 3
    assert isinstance(val.elements[0], NumberLiteral)
    assert val.elements[0].value == 1
    assert isinstance(val.elements[1], NumberLiteral)
    assert val.elements[1].value == 2
    assert isinstance(val.elements[2], NumberLiteral)
    assert val.elements[2].value == 3


def test_P1_dict_literal():
    """'x = {name = "Ana"}' → DictLiteral(pairs=[("name", StringLiteral("Ana"))]).

    Note: Atena's dict literal uses = (ASSIGN) as the key-value separator,
    NOT Python's colon. The lexer already emits LBRACE / IDENTIFIER / ASSIGN /
    STRING / RBRACE for this syntax.
    """
    program, ec = _parse('x = {name = "Ana"}\n')
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, DictLiteral)
    assert len(val.pairs) == 1
    key, value = val.pairs[0]
    assert key == "name"
    assert isinstance(value, StringLiteral)
    assert value.value == "Ana"


def test_P1_length():
    """'x = length items' → Assign with FunctionCall(name='length', args=[Identifier('items')]).

    Atena has no LengthOf AST node; 'length' is parsed as a keyword that wraps
    its single argument into a FunctionCall so codegen can emit len(items).
    """
    program, ec = _parse("x = length items\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, Assign)
    val = stmt.value
    assert isinstance(val, FunctionCall)
    assert val.name == "length"
    assert len(val.args) == 1
    assert isinstance(val.args[0], Identifier)
    assert val.args[0].name == "items"


def test_P1_if_no_else():
    """'if x > 1\\n    show x\\n' → If(condition=BinOp('>'), then_body=[Show(...)], else_body=[])."""
    program, ec = _parse("if x > 1\n    show x\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.condition, BinOp)
    assert stmt.condition.op == ">"
    assert len(stmt.then_body) == 1
    assert isinstance(stmt.then_body[0], Show)
    assert stmt.else_body == []


def test_P1_if_else():
    """'if x > 1\\n    show x\\nelse\\n    show 0\\n' → If with non-empty else_body."""
    program, ec = _parse("if x > 1\n    show x\nelse\n    show 0\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.condition, BinOp)
    assert len(stmt.then_body) == 1
    assert isinstance(stmt.then_body[0], Show)
    assert len(stmt.else_body) == 1
    assert isinstance(stmt.else_body[0], Show)


def test_P1_while():
    """'while x > 0\\n    x = x - 1\\n' → While(condition=BinOp('>'), body=[Assign(...)])."""
    program, ec = _parse("while x > 0\n    x = x - 1\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, While)
    assert isinstance(stmt.condition, BinOp)
    assert stmt.condition.op == ">"
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], Assign)


def test_P1_repeat():
    """'repeat 3 times\\n    show x\\n' → Repeat(count=NumberLiteral(3), body=[Show(...)])."""
    program, ec = _parse("repeat 3 times\n    show x\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, Repeat)
    assert isinstance(stmt.count, NumberLiteral)
    assert stmt.count.value == 3
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], Show)


def test_P1_function_def():
    """'function greet(name)\\n    show name\\n' → FunctionDef(name='greet', params=['name'], body=[Show(...)])."""
    program, ec = _parse("function greet(name)\n    show name\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, FunctionDef)
    assert stmt.name == "greet"
    assert stmt.params == ["name"]
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], Show)


def test_P1_function_def_no_params():
    """'function run()\\n    show 1\\n' → FunctionDef(name='run', params=[], body=[...])."""
    program, ec = _parse("function run()\n    show 1\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, FunctionDef)
    assert stmt.name == "run"
    assert stmt.params == []
    assert len(stmt.body) == 1


def test_P1_return():
    """'function f()\\n    return 1\\n' → FunctionDef body contains Return(value=NumberLiteral(1))."""
    program, ec = _parse("function f()\n    return 1\n")
    assert ec.is_empty()
    stmt = program.statements[0]
    assert isinstance(stmt, FunctionDef)
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], Return)
    assert isinstance(stmt.body[0].value, NumberLiteral)
    assert stmt.body[0].value.value == 1


def test_P1_list_add():
    """'add x to items' → ListAdd(target='items', value=Identifier('x'))."""
    program, ec = _parse("add x to items\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, ListAdd)
    assert stmt.target == "items"
    assert isinstance(stmt.value, Identifier)
    assert stmt.value.name == "x"


def test_P1_list_remove():
    """'remove x from items' → ListRemove(target='items', value=Identifier('x'))."""
    program, ec = _parse("remove x from items\n")
    assert ec.is_empty()
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, ListRemove)
    assert stmt.target == "items"
    assert isinstance(stmt.value, Identifier)
    assert stmt.value.name == "x"


def test_P1_nested_blocks():
    """Two-level nesting (if inside while) produces correct nesting in the AST."""
    source = "while x > 0\n    if x > 5\n        show x\n    x = x - 1\n"
    program, ec = _parse(source)
    assert ec.is_empty()
    assert len(program.statements) == 1
    outer = program.statements[0]
    assert isinstance(outer, While)
    assert len(outer.body) == 2
    inner = outer.body[0]
    assert isinstance(inner, If)
    assert len(inner.then_body) == 1
    assert isinstance(inner.then_body[0], Show)


def test_P1_line_numbers():
    """'x = 5\\nshow x\\n' → first statement line==1, second statement line==2."""
    program, ec = _parse("x = 5\nshow x\n")
    assert ec.is_empty()
    assert len(program.statements) == 2
    assert program.statements[0].line == 1
    assert program.statements[1].line == 2


# ---------------------------------------------------------------------------
# Layer 2 — Error-path tests (PARSE-06: Python-ism redirects + bad forms)
# ---------------------------------------------------------------------------


def test_P2_def_redirect():
    """'def greet()' produces the 'function' redirect error on line 1."""
    _, ec = _parse("def greet()\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "function" in report
    assert "Error on line 1" in report


def test_P2_elif_redirect():
    """'elif x' produces a redirect guiding toward nested if/else."""
    _, ec = _parse("elif x\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "nested" in report


def test_P2_for_redirect():
    """'for i in items' produces a redirect guiding toward repeat/while."""
    _, ec = _parse("for i in items\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "repeat" in report


def test_P2_class_redirect():
    """'class Foo' produces a redirect informing that Atena has no classes."""
    _, ec = _parse("class Foo\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "classes" in report


def test_P2_import_redirect():
    """'import os' produces a redirect informing that Atena is a single file."""
    _, ec = _parse("import os\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "single file" in report


def test_P2_eq_as_assignment():
    """'x == 5' as a statement produces the = vs == redirect error."""
    _, ec = _parse("x == 5\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "==" in report or "save a value" in report


def test_P2_top_level_return():
    """'return x' at top level produces the 'inside a function' error on line 1."""
    _, ec = _parse("return x\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "inside a function" in report
    assert "Error on line 1" in report


def test_P2_ask_misused_in_show():
    """'show ask "hi"' produces an error about ask needing to save into a name (D-02 redirect)."""
    _, ec = _parse('show ask "hi"\n')
    assert not ec.is_empty()
    report = ec.report()
    assert "save" in report or "answer" in report


def test_P2_missing_times():
    """'repeat 5\\n    show x\\n' (missing 'times') produces an error mentioning 'times'."""
    _, ec = _parse("repeat 5\n    show x\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "times" in report


def test_P2_unclosed_paren():
    """'show (x' (unclosed paren) produces an error mentioning ')'."""
    _, ec = _parse("show (x\n")
    assert not ec.is_empty()
    report = ec.report()
    assert '")"' in report or ")" in report


def test_P2_unclosed_bracket():
    """'x = items[' (unclosed bracket) produces an error mentioning ']'."""
    _, ec = _parse("x = items[\n")
    assert not ec.is_empty()
    report = ec.report()
    assert '"]"' in report or "]" in report


# ---------------------------------------------------------------------------
# Layer 3 — Cross-requirement tests (progress invariant, multi-error collection)
# ---------------------------------------------------------------------------


def test_Px_three_bad_statements_three_errors():
    """Three syntactically bad statements produce exactly 3 errors (one per bad line, no per-token spam)."""
    source = "def foo()\nelif x\nfor i in items\n"
    _, ec = _parse(source)
    report = ec.report()
    error_count = report.count("Error on line")
    assert error_count == 3


def test_Px_malformed_no_infinite_loop():
    """Heavily malformed source (== == == / != !=) terminates without hanging and collects errors."""
    source = "== == ==\n!= !=\n"
    program, ec = _parse(source)
    # If we reach here without timeout, the progress invariant held.
    assert not ec.is_empty()


def test_Px_multiple_errors_different_lines():
    """Two redirect errors on different lines produce 'Error on line 1' and 'Error on line 2'."""
    source = "def foo()\nelif x\n"
    _, ec = _parse(source)
    report = ec.report()
    assert "Error on line 1" in report
    assert "Error on line 2" in report


def test_Px_return_inside_function_no_error():
    """'return' inside a function body produces no error (return is only invalid at top level)."""
    program, ec = _parse("function f()\n    return 1\n")
    assert ec.is_empty()


def test_Px_empty_program():
    """Empty source '' produces Program(statements=[]) with no errors."""
    program, ec = _parse("")
    assert ec.is_empty()
    assert isinstance(program, Program)
    assert program.statements == []
