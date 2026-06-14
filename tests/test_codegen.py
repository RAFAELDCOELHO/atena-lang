"""
TDD tests for the Atena Code Generator — Phase 4 RED phase.

Layer 1 (golden snapshot tests): run the full pipeline on a valid snippet,
    assert the generated Python source text-matches the expected string.
    The canonical golden is school.atena → school.expected.py (GEN-06).

Layer 2 (execution tests): compile and run the generated Python in a
    subprocess with canned stdin, assert stdout matches the expected
    learner output. These catch runnable-but-wrong bugs (index/coercion)
    that text-match cannot.

Layer 3 (self-check + edge tests): ast.parse() self-check fires on every
    generate() call; targeted fixtures for mangling, nested-repeat loop vars,
    _atena_concat path, _atena_index path, dict dot-write, etc.

Cross-req (Gx_*): double-quote patch, header comment, on-demand helpers.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from atena.errors import ErrorCollector
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
)
from atena.lexer import Lexer
from atena.parser import Parser
from atena.analyzer import SemanticAnalyzer
from atena.codegen import CodeGenerator


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------


def _generate(source: str) -> str:
    """Full pipeline: lex → parse → analyze → generate; return Python source.

    Asserts no pipeline errors so test failures are readable.
    The ErrorCollector is shared across all phases (pipeline contract).
    """
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    program = Parser(tokens, ec).parse()
    SemanticAnalyzer(program, ec).analyze()
    assert ec.is_empty(), f"Pipeline errors before codegen:\n{ec.report()}"
    return CodeGenerator(program).generate()


# ---------------------------------------------------------------------------
# Layer 1 — Golden snapshot tests (G1_*)
# ---------------------------------------------------------------------------


def test_G1_show_string_literal():
    """'show "hello"' → generated Python contains 'print("hello")'."""
    result = _generate('show "hello"\n')
    assert 'print("hello")' in result


def test_G1_assign_number():
    """'x = 5' → generated Python contains 'x = 5'."""
    result = _generate("x = 5\n")
    assert "x = 5" in result


def test_G1_repeat_generates_for_loop():
    """'repeat 3 times\\n    show 1\\n' → generated Python contains 'range(3)'."""
    result = _generate("repeat 3 times\n    show 1\n")
    assert "range(3)" in result


def test_G1_if_else_generates_correctly():
    """Basic if/else → generated Python contains 'if' and 'else:'."""
    result = _generate("x = 5\nif x > 0\n    show x\nelse\n    show 0\n")
    assert "if " in result
    assert "else:" in result


def test_G1_dict_literal():
    """'student = {name = "Ana"}' → generated Python contains '{"name": "Ana"}'."""
    result = _generate('student = {name = "Ana"}\n')
    assert '{"name": "Ana"}' in result


def test_G1_list_add_generates_append():
    """'add 5 to grades' → generated Python contains '.append(5)'."""
    result = _generate("grades = []\nadd 5 to grades\n")
    assert ".append(5)" in result


# ---------------------------------------------------------------------------
# Layer 2 — Execution tests (G2_*)
# ---------------------------------------------------------------------------


def test_G2_show_number_executes():
    """'show 42' → generated Python executes and prints '42'."""
    python_src = _generate("show 42\n")
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "42"


def test_G2_arithmetic_executes():
    """'show 2 + 3 * 4' → generated Python executes and prints '14'."""
    python_src = _generate("show 2 + 3 * 4\n")
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "14"


def test_G2_school_execution_placeholder():
    """Placeholder: school.atena execution test — fails until school.atena is authored."""
    pytest.fail("school.atena not yet authored")


# ---------------------------------------------------------------------------
# Layer 3 — Self-check + edge tests (G3_*)
# ---------------------------------------------------------------------------


def test_G3_ast_parse_selfcheck_all_snippets():
    """Every generate() call produces output that ast.parse() accepts without error."""
    snippets = [
        'show "hello"\n',
        "x = 5\nshow x\n",
        "items = [1, 2, 3]\nshow items[1]\n",
    ]
    for snippet in snippets:
        python_src = _generate(snippet)
        # ast.parse() raises SyntaxError on malformed output — that means codegen bug
        ast.parse(python_src)


def test_G3_keyword_mangling_pass():
    """'pass = 5' (Python keyword, valid Atena name) → mangled as 'pass_' in output.

    'class', 'import', 'for', 'def', 'elif' are caught by the parser's
    Python-ism redirect and never reach codegen.  'pass' is a Python keyword
    that Atena allows as a variable name (not in Atena's 19-keyword set), so
    it reaches codegen and must be mangled to avoid a SyntaxError in the output.
    """
    result = _generate("pass = 5\n")
    assert "pass_" in result, f"Expected 'pass_' (mangled) in output:\n{result}"
    ast.parse(result)   # must parse cleanly after mangling


def test_G3_nested_repeat_unique_loop_vars():
    """Nested 'repeat' loops use distinct _atena_i* variables so inner never shadows outer."""
    import re
    source = "repeat 3 times\n    repeat 2 times\n        show 1\n"
    result = _generate(source)
    loop_vars = re.findall(r"_atena_i\d+", result)
    assert len(set(loop_vars)) == 2, f"Expected 2 unique loop vars, got: {loop_vars}"


def test_G3_zero_error_gate():
    """CodeGenerator is never called when pipeline has errors (GEN-03).

    Verifies the hard gate contract: if ec is not empty after any pipeline
    phase, the caller must not invoke CodeGenerator.generate().
    This test runs the pipeline on malformed input, asserts errors are collected,
    and verifies that the gate check (ec.is_empty()) correctly signals STOP.
    The test itself never calls generate() — that would violate the contract.
    """
    ec = ErrorCollector()
    tokens = Lexer("x = \n", ec).tokenize()     # parse error: missing RHS
    program = Parser(tokens, ec).parse()
    SemanticAnalyzer(program, ec).analyze()
    # ec must be non-empty — the malformed input should produce at least one error.
    assert not ec.is_empty(), "Expected parse/analyze errors for malformed source"
    # GEN-03 hard gate: the driver (Phase 5) must check is_empty() before calling
    # generate().  We verify the gate signal here; calling generate() on an errored
    # tree is undefined behavior — stop here.
    # Negative check: _generate() would raise AssertionError here, proving the gate.
    try:
        _generate("x = \n")
        assert False, "_generate() should have raised AssertionError for errored pipeline"
    except AssertionError as exc:
        assert "Pipeline errors before codegen" in str(exc), (
            f"Expected 'Pipeline errors before codegen' in AssertionError, got: {exc}"
        )


def test_G3_ast_parse_selfcheck_broader():
    """ast.parse() self-check fires on outputs for all core construct types."""
    snippets = [
        'show "hello"\n',
        "x = 5\nshow x\n",
        "repeat 3 times\n    show 1\n",
        "if true\n    show 1\nelse\n    show 2\n",
    ]
    for snippet in snippets:
        python_src = _generate(snippet)
        try:
            ast.parse(python_src)
        except SyntaxError as exc:
            raise AssertionError(
                f"GEN-05 self-check: ast.parse() failed for snippet {snippet!r}.\n"
                f"SyntaxError: {exc}\n"
                f"Generated output:\n{python_src}"
            ) from exc


# ---------------------------------------------------------------------------
# Cross-requirement tests (Gx_*)
# ---------------------------------------------------------------------------


def test_Gx_double_quote_patch():
    """Generated Python uses double quotes for string literals (D-02 patch)."""
    result = _generate('show "hello"\n')
    # The generated source must contain "hello" in double quotes
    assert '"hello"' in result, f"Expected double-quoted string in output:\n{result}"
    # No single-quoted version of the same string should appear
    assert "'hello'" not in result, f"Single-quoted string leaked into output:\n{result}"


def test_Gx_header_comment():
    """Generated output starts with a '#' comment line (D-02 patch)."""
    result = _generate("x = 5\n")
    lines = result.splitlines()
    assert lines, "Generated output must not be empty"
    assert lines[0].startswith("#"), (
        f"First line of generated output must be a comment. Got: {lines[0]!r}"
    )


def test_Gx_on_demand_helpers_absent_when_unused():
    """A simple program with no lists/concat has no _atena_index or _atena_concat in output."""
    result = _generate("x = 5\nshow x\n")
    assert "_atena_index" not in result, (
        f"_atena_index helper should not be emitted for a program that doesn't use it"
    )
    assert "_atena_concat" not in result, (
        f"_atena_concat helper should not be emitted for a program that doesn't use it"
    )


# ---------------------------------------------------------------------------
# Task 1 tests: list/dict/index/dot/listop execution tests (G2_*)
# ---------------------------------------------------------------------------


def test_G2_index_access_executes_verbatim():
    """grades[1] (Atena) runs as grades[0] in Python (no double-shift).

    The analyzer rewrites literal index 1 → 0; codegen emits [0] verbatim.
    Result: grades[0] prints 5 (first element).
    """
    python_src = _generate("grades = [5, 7, 9]\nshow grades[1]\n")
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "5"


def test_G2_dict_dot_read_executes():
    """student.name (dict dot-read) emits student["name"] and runs correctly."""
    python_src = _generate('student = {name = "Ana"}\nshow student.name\n')
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "Ana"


def test_G2_list_add_remove_executes():
    """add/remove/length list operations execute correctly.

    Start with [1], add 2 → [1, 2], remove 1 → [2], length → 1.
    """
    python_src = _generate(
        "grades = [1]\nadd 2 to grades\nremove 1 from grades\nshow length grades\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "1"


# ---------------------------------------------------------------------------
# Task 2 tests: FunctionDef/Return/on-demand helpers (G1_function, G2_function, Gx_*)
# ---------------------------------------------------------------------------


def test_G1_function_def_emit():
    """function definition emits a Python def statement."""
    result = _generate("function greet(name)\n    show name\n")
    assert "def greet(name):" in result


def test_G2_function_call_executes():
    """Define and call a function, verify the output."""
    python_src = _generate(
        'function greet(name)\n    show name\ngreet("Ana")\n'
    )
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "Ana"


def test_G2_function_with_return_executes():
    """Function with return statement executes and produces correct result."""
    python_src = _generate("function square(n)\n    return n * n\nshow square(4)\n")
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "16"


def test_Gx_on_demand_index_helper_present_when_used():
    """A program with a dynamic list index has _atena_index prepended in output."""
    result = _generate("i = 1\ngradeslist = [5, 7, 9]\nshow gradeslist[i]\n")
    assert "def _atena_index" in result, (
        f"_atena_index helper should be emitted for programs with dynamic indices.\n"
        f"Got:\n{result}"
    )
