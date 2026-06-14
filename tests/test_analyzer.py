"""
TDD tests for the Atena Semantic Analyzer — Phase 3 RED phase.

Layer 1 (golden mutated-AST snapshots): run the analyzer on a valid snippet,
    assert the mutated node equals the expected shape (index_converted=True,
    injected FunctionCall("str"/...), updated field values).

Layer 2 (error-path tests): feed source with semantic errors, assert exact
    key phrase in ec.report(), error count, and line numbers — no crash,
    no hang.

Layer 3 (cross-requirement tests): multiple errors collected in one run,
    poison suppresses cascades, arity checks, no-hoisting enforcement.
"""

from __future__ import annotations

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


def _analyze(source: str) -> tuple[Program, ErrorCollector]:
    """Helper: lex + parse + analyze source; return (program_ast, errors).

    Chains through the real Lexer and Parser so tests use production ASTs.
    The ErrorCollector is shared across all three phases — each phase appends
    to the same collector (matching the pipeline contract).
    """
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    program = Parser(tokens, ec).parse()
    SemanticAnalyzer(program, ec).analyze()
    return program, ec


# ---------------------------------------------------------------------------
# Layer 1 — Golden mutated-AST snapshot tests (A1_*)
# ---------------------------------------------------------------------------


def test_A1_index_literal_rewritten():
    """'x = items[1]' → analyzer sets index.value=0 and index_converted=True."""
    program, ec = _analyze("items = [10, 20]\nx = items[1]\n")
    assert ec.is_empty()
    assign = program.statements[1]
    assert isinstance(assign, Assign)
    access = assign.value
    assert isinstance(access, IndexAccess)
    assert access.index_converted is True
    assert isinstance(access.index, NumberLiteral)
    assert access.index.value == 0   # 1→0 rewrite


def test_A1_nested_index_rewritten():
    """'x = grid[2][3]' → outer index.value==1, inner index.value==2, both index_converted==True."""
    program, ec = _analyze("grid = [[1, 2], [3, 4]]\nx = grid[2][3]\n")
    assert ec.is_empty()
    assign = program.statements[1]
    assert isinstance(assign, Assign)
    # grid[2][3] parses as IndexAccess(IndexAccess(grid, 2), 3)
    outer_access = assign.value
    assert isinstance(outer_access, IndexAccess)
    assert outer_access.index_converted is True
    assert isinstance(outer_access.index, NumberLiteral)
    assert outer_access.index.value == 2   # 3→2 rewrite
    inner_access = outer_access.target
    assert isinstance(inner_access, IndexAccess)
    assert inner_access.index_converted is True
    assert isinstance(inner_access.index, NumberLiteral)
    assert inner_access.index.value == 1   # 2→1 rewrite


def test_A1_string_concat_no_coerce():
    """'x="a"+"b"; y=x+1' → x+b BinOp unchanged, and x+1 has right side coerced to str()."""
    # Two-line program: first line establishes x as str; second uses x so the
    # analyzer must track x's type to decide whether to coerce the 1.
    program, ec = _analyze('x = "a" + "b"\ny = x + 1\n')
    assert ec.is_empty()
    # First assignment: "a"+"b" — both str, no coercion
    binop1 = program.statements[0].value
    assert isinstance(binop1, BinOp)
    assert isinstance(binop1.left, StringLiteral)    # not wrapped
    assert isinstance(binop1.right, StringLiteral)   # not wrapped
    # Second assignment: x+"b" — x is str, 1 is number → right side must be wrapped
    binop2 = program.statements[1].value
    assert isinstance(binop2, BinOp)
    assert isinstance(binop2.right, FunctionCall)    # 1 wrapped in str()
    assert binop2.right.name == "str"


def test_A1_str_coerce_number_rhs():
    """'x = "hello" + 5' → right side wrapped in FunctionCall("str", [NumberLiteral(5)])."""
    program, ec = _analyze('x = "hello" + 5\n')
    assert ec.is_empty()
    binop = program.statements[0].value
    assert isinstance(binop, BinOp)
    assert isinstance(binop.left, StringLiteral)
    assert isinstance(binop.right, FunctionCall)
    assert binop.right.name == "str"
    assert len(binop.right.args) == 1
    assert isinstance(binop.right.args[0], NumberLiteral)
    assert binop.right.args[0].value == 5


def test_A1_str_coerce_number_lhs():
    """'x = 1 + "x"' → left side wrapped in FunctionCall("str", [NumberLiteral(1)])."""
    program, ec = _analyze('x = 1 + "x"\n')
    assert ec.is_empty()
    binop = program.statements[0].value
    assert isinstance(binop, BinOp)
    assert isinstance(binop.left, FunctionCall)
    assert binop.left.name == "str"
    assert len(binop.left.args) == 1
    assert isinstance(binop.left.args[0], NumberLiteral)
    assert binop.left.args[0].value == 1
    assert isinstance(binop.right, StringLiteral)


def test_A1_number_plus_number_no_coerce():
    """'x=1+2; y="prefix"+x' → 1+2 unchanged; x tracked as number → right side of y=str(x)."""
    # Three lines: first establishes x=1+2 (both literals, no coerce); second uses x
    # in a string-concat context.  If x is correctly tracked as "number", then
    # "prefix" + x → coerce_right (wrap x in str()).  The stub does NOT track x's type
    # (x stays "unknown"), so the stub would NOT inject str() — it would instead route
    # the whole expression through _atena_concat — causing the assertion below to fail.
    program, ec = _analyze('x = 1 + 2\ny = "prefix" + x\n')
    assert ec.is_empty()
    # First BinOp: 1+2 — both NumberLiteral, no coercion
    binop1 = program.statements[0].value
    assert isinstance(binop1, BinOp)
    assert isinstance(binop1.left, NumberLiteral)
    assert isinstance(binop1.right, NumberLiteral)
    # Second BinOp: "prefix"+x — x is number (tracked), str+number → coerce_right
    binop2 = program.statements[1].value
    assert isinstance(binop2, BinOp)
    assert isinstance(binop2.left, StringLiteral)
    # x must be wrapped in str() because the analyzer tracked x as "number"
    assert isinstance(binop2.right, FunctionCall)
    assert binop2.right.name == "str"
    assert isinstance(binop2.right.args[0], Identifier)
    assert binop2.right.args[0].name == "x"


def test_A1_str_coerce_bool_rhs():
    """'x = "a" + true' → right side wrapped in FunctionCall("str")."""
    program, ec = _analyze('x = "a" + true\n')
    assert ec.is_empty()
    binop = program.statements[0].value
    assert isinstance(binop, BinOp)
    assert isinstance(binop.left, StringLiteral)
    assert isinstance(binop.right, FunctionCall)
    assert binop.right.name == "str"


def test_A1_unknown_plus_uses_concat_helper():
    """'x = result + 1' where result is a function call result (unknown type) → _atena_concat helper node."""
    source = "function getValue()\n    return 5\nx = getValue() + 1\n"
    program, ec = _analyze(source)
    # The call result has unknown type, so + routes through _atena_concat
    assign = program.statements[1]
    assert isinstance(assign, Assign)
    # The rhs should use the _atena_concat helper because getValue() has unknown type
    rhs = assign.value
    # Either the BinOp left/right was replaced, or the whole expression is a FunctionCall
    assert isinstance(rhs, FunctionCall) and rhs.name == "_atena_concat"


def test_A1_variable_index_uses_atena_index_helper():
    """'x = items[i]' (variable index) → index is FunctionCall(name='_atena_index')."""
    source = "items = [10, 20]\ni = 1\nx = items[i]\n"
    program, ec = _analyze(source)
    assert ec.is_empty()
    assign = program.statements[2]
    assert isinstance(assign, Assign)
    access = assign.value
    assert isinstance(access, IndexAccess)
    assert access.index_converted is True
    assert isinstance(access.index, FunctionCall)
    assert access.index.name == "_atena_index"


def test_A1_ask_registers_str_type():
    """'answer = ask "name?"; answer + "!" → right side NOT wrapped (both str, no coerce needed)."""
    source = 'answer = ask "What is your name?"\nx = answer + "!"\n'
    program, ec = _analyze(source)
    assert ec.is_empty()
    assign = program.statements[1]
    assert isinstance(assign, Assign)
    binop = assign.value
    assert isinstance(binop, BinOp)
    # answer is str, "!" is str → no coercion needed; right side should stay StringLiteral
    assert isinstance(binop.right, StringLiteral)


def test_A1_bool_literal_type_inferred():
    """'x = true; x + 1' → bool+number is an error (NOT unknown)."""
    source = "x = true\ny = x + 1\n"
    _, ec = _analyze(source)
    # bool + number is a "can't add" error, not silent unknown routing
    assert not ec.is_empty()
    report = ec.report()
    assert "can't add" in report or "can't" in report or "Cannot" in report or "can't combine" in report.lower() or "true/false" in report or "bool" in report.lower()


# ---------------------------------------------------------------------------
# Layer 2 — Error-path tests (A2_*)
# ---------------------------------------------------------------------------


def test_A2_index_zero_error():
    """'x = items[0]' produces the canonical '...start at 1, not 0.' error."""
    items_assign = "items = [10, 20, 30]\n"
    _, ec = _analyze(f"{items_assign}x = items[0]\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "start at 1, not 0" in report
    assert "Error on line 2" in report


def test_A2_index_negative_error():
    """'x = items[-3]' produces 'no negative positions' error."""
    _, ec = _analyze("items = [10, 20, 30]\nx = items[-3]\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "negative" in report


def test_A2_cannot_combine_number_bool():
    """'x = 1 + true' → "can't add" error on line 1."""
    _, ec = _analyze("x = 1 + true\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "can't add" in report or "can't" in report.lower()
    assert "Error on line 1" in report


def test_A2_cannot_combine_list_str():
    """'x = [1] + 1' → "can't add" error."""
    _, ec = _analyze('x = [1] + 1\n')
    assert not ec.is_empty()
    report = ec.report()
    assert "can't add" in report or "can't" in report.lower()


def test_A2_undefined_variable():
    """Using 'score' before assigning it produces the canonical undefined-name error."""
    _, ec = _analyze("show score\n")
    assert not ec.is_empty()
    report = ec.report()
    assert '"score"' in report
    assert "Error on line 1" in report


def test_A2_undefined_suggests_close_name():
    """'x=1; show xx' → 'Did you mean' in report (suggest fires)."""
    _, ec = _analyze("x = 1\nshow xx\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "Did you mean" in report


def test_A2_call_before_defined():
    """Calling 'greet()' before its 'function greet()' definition is a compile error."""
    source = "greet()\nfunction greet()\n    show 1\n"
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "greet" in report
    assert "Error on line 1" in report


def test_A2_wrong_arity_too_many():
    """Calling greet("Ana","extra") when greet expects 1 arg → 'expects 1' and 'gave 2' in report."""
    source = 'function greet(name)\n    show name\ngreet("Ana", "extra")\n'
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "greet" in report
    assert "expects 1" in report
    assert "gave 2" in report


def test_A2_wrong_arity_too_few():
    """Calling combine(1) when combine expects 2 args → 'expects 2' and 'gave 1' in report."""
    source = "function combine(a, b)\n    return a + b\ncombine(1)\n"
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "expects 2" in report
    assert "gave 1" in report


def test_A2_function_reads_outer_var():
    """'x=1; function f() show x' → tailored "pass as parameter" message (D-08)."""
    source = "x = 1\nfunction f()\n    show x\n"
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "pass" in report and "parameter" in report


# ---------------------------------------------------------------------------
# Layer 3 — Cross-requirement tests (Ax_*)
# ---------------------------------------------------------------------------


def test_Ax_poison_suppresses_cascade():
    """Undefined 'score' on line 1 produces exactly 1 error; line 2 'show score' does NOT add a second."""
    source = "show score\nshow score\n"
    _, ec = _analyze(source)
    report = ec.report()
    # Poison fires: second reference to score should not generate a second error
    assert report.count("Error on line") == 1


def test_Ax_multiple_errors_collected():
    """Three independent errors in one program are all collected."""
    source = "show undefined1\nshow undefined2\nx = items[0]\n"
    _, ec = _analyze(source)
    report = ec.report()
    assert report.count("Error on line") >= 3


def test_Ax_empty_program_no_errors():
    """Empty source produces no semantic errors; a minimal valid program also produces none."""
    _, ec1 = _analyze("")
    assert ec1.is_empty()
    # Also verify a minimal valid program with a known-type variable produces no errors,
    # AND that using the variable in a follow-up expression works cleanly.
    # This ensures the symbol table is actually populated (not just no-op pass).
    program, ec2 = _analyze('name = "Alice"\nshow name\n')
    assert ec2.is_empty()
    # The show statement visited the Identifier 'name' — it must have resolved cleanly
    # to 'str' type. Verify by adding a coercion use: name + 1 should produce no error
    # (str+number → coerce_right) when the real analyzer tracks name as str.
    program2, ec3 = _analyze('name = "Alice"\nx = name + 1\n')
    assert ec3.is_empty()
    binop = program2.statements[1].value
    assert isinstance(binop, BinOp)
    # name is str, 1 is number → right side should be wrapped in str()
    assert isinstance(binop.right, FunctionCall)
    assert binop.right.name == "str"


def test_Ax_index_converted_idempotent():
    """Analyzing the same IndexAccess node twice does not double-shift the index."""
    source = "items = [10, 20, 30]\nx = items[2]\n"
    program, ec = _analyze(source)
    assert ec.is_empty()
    assign = program.statements[1]
    access = assign.value
    assert isinstance(access, IndexAccess)
    assert access.index_converted is True
    assert isinstance(access.index, NumberLiteral)
    first_value = access.index.value  # should be 1 (2→1 rewrite)
    assert first_value == 1

    # Re-analyze the same program object — should NOT shift again
    SemanticAnalyzer(program, ec).analyze()
    assert access.index.value == 1   # still 1, not 0 (no double-shift)


def test_Ax_chain_coercion_correct():
    """'x = "a" + 1 + 2' → ec.is_empty() and coercion nodes are injected correctly."""
    source = 'x = "a" + 1 + 2\n'
    program, ec = _analyze(source)
    # The chain "a" + 1 + 2 should coerce correctly with no errors
    assert ec.is_empty()
    # The outer BinOp should have its right side (NumberLiteral 2) wrapped in str()
    # The inner BinOp should have its right side (NumberLiteral 1) wrapped in str()
    assign = program.statements[0]
    outer_binop = assign.value
    assert isinstance(outer_binop, BinOp)
    # Outer right (2) should be str-coerced
    assert isinstance(outer_binop.right, FunctionCall)
    assert outer_binop.right.name == "str"
    # Inner binop is in outer_binop.left
    inner_binop = outer_binop.left
    assert isinstance(inner_binop, BinOp)
    assert isinstance(inner_binop.right, FunctionCall)
    assert inner_binop.right.name == "str"


def test_Ax_nested_subscript_independent():
    """'x = grid[2][3]' → outer index becomes 2 (3-1), inner index becomes 1 (2-1), not double-shifted."""
    source = "grid = [[1, 2], [3, 4], [5, 6]]\nx = grid[2][3]\n"
    program, ec = _analyze(source)
    assert ec.is_empty()
    assign = program.statements[1]
    outer_access = assign.value
    assert isinstance(outer_access, IndexAccess)
    assert outer_access.index_converted is True
    assert isinstance(outer_access.index, NumberLiteral)
    assert outer_access.index.value == 2   # 3→2 rewrite
    inner_access = outer_access.target
    assert isinstance(inner_access, IndexAccess)
    assert inner_access.index_converted is True
    assert isinstance(inner_access.index, NumberLiteral)
    assert inner_access.index.value == 1   # 2→1 rewrite


# ---------------------------------------------------------------------------
# WR-01: Guard helper names — _atena_ prefix reserved, builtin shadowing handled
# ---------------------------------------------------------------------------


def test_A2_atena_prefix_assign_rejected():
    """Assigning to a name starting with '_atena_' produces a plain-English error."""
    _, ec = _analyze("_atena_index = 5\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "_atena_" in report or "reserved" in report.lower() or "internal" in report.lower()


def test_A2_atena_prefix_function_def_rejected():
    """Defining a function named '_atena_concat' produces a plain-English error."""
    source = "function _atena_concat(a, b)\n    return a\n"
    _, ec = _analyze(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "_atena_" in report or "reserved" in report.lower() or "internal" in report.lower()


def test_A2_builtin_function_user_redefined_checked():
    """User defines 'function str(x)' with wrong arity and calls str(5, 6) — arity IS checked."""
    source = "function str(x)\n    return x\nshow str(5, 6)\n"
    _, ec = _analyze(source)
    # The user redefined str — normal arity check should fire (expects 1, gave 2)
    assert not ec.is_empty()
    report = ec.report()
    assert "expects 1" in report or "str" in report


# ---------------------------------------------------------------------------
# CR-02: add/remove validate list target (defined-before-use)
# ---------------------------------------------------------------------------


def test_A2_add_to_undefined_list_errors():
    """'add 1 to mylist' where mylist is never defined produces a plain-English error."""
    _, ec = _analyze("add 1 to mylist\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "mylist" in report
    assert "Error on line 1" in report


def test_A2_remove_from_undefined_list_errors():
    """'remove 1 from mylist' where mylist is never defined produces a plain-English error."""
    _, ec = _analyze("remove 1 from mylist\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "mylist" in report
    assert "Error on line 1" in report


# ---------------------------------------------------------------------------
# CR-01: str() coercion idempotency
# ---------------------------------------------------------------------------


def test_Ax_coercion_idempotent():
    """Re-analyzing a 'str + number' program must NOT corrupt the AST.

    After the first pass 'x = "a" + 1' becomes BinOp(left=StringLiteral, right=FunctionCall("str")).
    A second analyze() on the same program must leave the tree unchanged
    (no double-wrap, no conversion to _atena_concat).
    """
    source = 'x = "a" + 1\n'
    program, ec = _analyze(source)
    assert ec.is_empty()
    binop = program.statements[0].value
    assert isinstance(binop, BinOp)
    assert isinstance(binop.right, FunctionCall)
    assert binop.right.name == "str"

    # Re-analyze the same program object — must NOT change tree shape
    ec2 = ErrorCollector()
    SemanticAnalyzer(program, ec2).analyze()
    assert ec2.is_empty()
    # Tree shape must be unchanged: still a BinOp (not FunctionCall("_atena_concat"))
    binop_again = program.statements[0].value
    assert isinstance(binop_again, BinOp), (
        "Second analyze pass corrupted AST: BinOp was converted to FunctionCall"
    )
    assert isinstance(binop_again.right, FunctionCall)
    assert binop_again.right.name == "str"
    # Must NOT have been double-wrapped
    assert not isinstance(binop_again.right.args[0], FunctionCall), (
        "Second analyze pass double-wrapped the right operand"
    )
