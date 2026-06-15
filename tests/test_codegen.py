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


def test_G1_division_is_floor_division():
    """'show 10 / 3' → generated Python uses floor division '//' (integers only).

    Atena v1.0 is integers-only (PROJECT.md). Mapping '/' to Python true
    division would leak floats into a beginner curriculum, so codegen must
    emit '//' for the division operator.
    """
    result = _generate("show 10 / 3\n")
    assert "10 // 3" in result, f"Expected floor division '//'. Got:\n{result}"
    assert "10 / 3" not in result.replace("10 // 3", ""), (
        f"Division must not emit true division '/'. Got:\n{result}"
    )


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


def test_G2_division_executes_to_integer():
    """'show 10 / 3' → generated Python executes and prints '3' (no float).

    Floor division keeps the integers-only contract: a learner never sees
    a 17-digit float like 3.3333333333333335 on a basic arithmetic example.
    """
    python_src = _generate("show 10 / 3\n")
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "3", (
        f"Expected integer '3' from 10 / 3. Got: {result.stdout!r}"
    )


def test_G1_golden_school_roundtrip():
    """school.atena round-trips through the full pipeline to exactly school.expected.py.

    Reads the approved, locked golden fixture from disk, runs the full pipeline,
    and asserts byte-for-byte text equality.  Any pipeline regression that changes
    the generated output will be caught here.
    """
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "school.atena").read_text()
    expected = (fixtures / "school.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"Golden mismatch — pipeline output does not match locked snapshot.\n"
        f"--- expected ---\n{expected}\n"
        f"--- got ---\n{result}"
    )


def test_G2_school_execution_with_canned_stdin():
    """Generated school.expected.py runs correctly with canned stdin 'Ana'.

    Reads the locked golden snapshot, executes it as a subprocess with
    input='Ana\\n', and asserts:
    - returncode == 0 (no crashes)
    - 'Ana' appears in stdout (personalized greeting used the name)
    - a pass/fail verdict appears in stdout (if/else branch ran)
    """
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "school.expected.py").read_text()

    result = subprocess.run(
        [sys.executable, "-c", python_src],
        input="Ana\n",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert "Ana" in result.stdout, (
        f"Expected student name 'Ana' in output. Got:\n{result.stdout}"
    )
    stdout_lower = result.stdout.lower()
    assert "pass" in stdout_lower or "fail" in stdout_lower, (
        f"Expected a pass/fail verdict in output (if/else branch). Got:\n{result.stdout}"
    )


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


# ---------------------------------------------------------------------------
# Plan 04-04: Task 1 — Keyword mangling + nested-repeat uniqueness tests (G3_*)
# ---------------------------------------------------------------------------


def test_G3_keyword_mangling_class():
    """_mangle('class') returns 'class_' (trailing underscore for Python keyword).

    'class' triggers a Python-ism redirect in the Atena parser, so it cannot
    reach codegen via the full pipeline.  We test _mangle() directly, which is
    the function codegen calls for every identifier emission.  This satisfies
    GEN-04: the mangle function itself is correct for 'class'.
    """
    from atena.codegen import _mangle
    assert _mangle("class") == "class_"
    # Verify the mangled form parses as valid Python
    ast.parse("class_ = 5")


def test_G3_keyword_mangling_import():
    """_mangle('import') returns 'import_'.

    'import' is rejected by the Atena parser (Python-ism redirect), so tested
    directly via _mangle() — the same function codegen calls per GEN-04.
    """
    from atena.codegen import _mangle
    assert _mangle("import") == "import_"
    ast.parse("import_ = 10")


def test_G3_keyword_mangling_execution():
    """Mangled keyword variable produces correct output when executed.

    'pass' is a Python keyword that Atena accepts as an identifier (not caught
    by the parser's Python-ism redirect).  Verify 'pass = 42\\nshow pass' runs
    and prints '42' — confirming that mangling is consistent at both definition
    and use sites in the generated Python.
    """
    python_src = _generate("pass = 42\nshow pass\n")
    assert "pass_" in python_src
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "42"


def test_G3_all_python_keywords_mangled():
    """All Python keywords that pass through the Atena pipeline are mangled.

    For each keyword in keyword.kwlist that the Atena pipeline accepts as a
    variable name (not blocked by the lexer/parser's Python-ism detection),
    verify that:
    1. The generated Python contains the mangled name (keyword + '_').
    2. ast.parse() accepts the output.
    """
    import keyword as kw

    # These Python keywords are also Atena KEYWORD tokens or trigger Python-ism
    # redirects in the parser — they never reach codegen as identifiers.
    pipeline_blocked = {
        # Atena language keywords (lexed as KEYWORD tokens)
        "and", "or", "not", "if", "else", "while", "return",
        "True", "False",  # Atena uses 'true'/'false'; Python-cased forms are blocked
        # Python-ism redirects in the parser (generates a friendly error, stops pipeline)
        "class", "import", "for", "def", "elif", "from",
    }

    passable = [k for k in kw.kwlist if k not in pipeline_blocked]

    for k in passable:
        result = _generate(f"{k} = 1\nshow {k}\n")
        mangled = k + "_"
        assert mangled in result, (
            f"Expected '{mangled}' in generated output for keyword '{k}'.\n"
            f"Got:\n{result}"
        )
        try:
            ast.parse(result)
        except SyntaxError as exc:
            raise AssertionError(
                f"ast.parse() failed for mangled keyword '{k}':\n{exc}\n"
                f"Generated:\n{result}"
            ) from exc


def test_G3_three_sibling_repeats_unique_vars():
    """Three consecutive repeat loops use 3 distinct _atena_i* loop variables.

    The monotonic counter must never reset between sibling repeat loops,
    guaranteeing unique vars throughout the entire program.
    """
    import re
    source = (
        "repeat 1 times\n    show 1\n"
        "repeat 1 times\n    show 2\n"
        "repeat 1 times\n    show 3\n"
    )
    result = _generate(source)
    loop_vars = re.findall(r"_atena_i\d+", result)
    assert len(set(loop_vars)) == 3, (
        f"Expected 3 unique loop vars for 3 sibling repeats, got: {loop_vars}\n"
        f"Generated:\n{result}"
    )


def test_G2_nested_repeat_executes_correct_count():
    """Nested repeat loops execute the correct total iteration count.

    outer 3 * inner 2 = 6 increments of n.  Verifies that the two distinct
    loop variables (_atena_i0, _atena_i1) do not interfere with each other.
    """
    python_src = _generate(
        "n = 0\nrepeat 3 times\n    repeat 2 times\n        n = n + 1\nshow n\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "6"

# ---------------------------------------------------------------------------
# Plan 04-04: Task 2 — Helper body execution tests + verbatim-emission tests
# ---------------------------------------------------------------------------


def test_G2_atena_index_helper_blocks_zero():
    """_atena_index(0) raises an IndexError with the plain-English message at runtime.

    Source uses i=0 (dynamic index), which routes through _atena_index at runtime.
    At i=0, the helper raises IndexError('List positions in Atena start at 1.').
    """
    source = "i = 0\ngradeslist = [5, 7, 9]\nshow gradeslist[i]\n"
    python_src = _generate(source)
    assert "_atena_index" in python_src, (
        f"Expected _atena_index helper in generated output.\nGot:\n{python_src}"
    )
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    # Must exit non-zero (raised IndexError)
    assert result.returncode != 0, (
        f"Expected non-zero exit when index=0, but got:\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "List positions" in result.stderr, (
        f"Expected 'List positions in Atena start at 1.' in stderr.\n"
        f"Got stderr:\n{result.stderr}"
    )


def test_G2_atena_index_helper_valid():
    """_atena_index(1) returns 0 — valid 1-based index maps to Python index 0.

    Source uses i=1 (dynamic index); gradeslist[1] → Python index 0 → value 5.
    """
    source = "i = 1\ngradeslist = [5, 7, 9]\nshow gradeslist[i]\n"
    python_src = _generate(source)
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "5"


def test_G2_atena_concat_helper_string_result():
    """_atena_concat(3, 5) returns '35' (string concatenation, not numeric addition).

    Inside a function body, parameters 'a' and 'b' have unknown type, so
    'a + b' is routed through _atena_concat.  _atena_concat returns
    str(a) + str(b), so join(3, 5) produces '35', not 8.
    This confirms the _atena_concat helper correctly concatenates as strings.
    """
    source = "function join(a, b)\n    return a + b\nshow join(3, 5)\n"
    python_src = _generate(source)
    assert "_atena_concat" in python_src, (
        f"Expected _atena_concat helper in generated output.\nGot:\n{python_src}"
    )
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "35"


def test_G3_verbatim_no_str_wrap_number_plus_number():
    """Number + number BinOp emits 'x + y' verbatim — no str() wrapping.

    Analyzer assigns both x and y the 'number' type (from literal assignments),
    so the BinOp uses no_coerce.  Codegen must emit 'x + y', NOT 'str(x) + y'.
    """
    source = "x = 5\ny = 3\nshow x + y\n"
    result = _generate(source)
    assert "str(x)" not in result, (
        f"'str(x)' should NOT appear in generated output (verbatim no-coerce).\n"
        f"Got:\n{result}"
    )
    assert "str(y)" not in result, (
        f"'str(y)' should NOT appear in generated output (verbatim no-coerce).\n"
        f"Got:\n{result}"
    )
    assert "x + y" in result, (
        f"Expected 'x + y' (verbatim BinOp) in generated output.\nGot:\n{result}"
    )
    python_result = subprocess.run(
        [sys.executable, "-c", result],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert python_result.returncode == 0, f"Generated Python crashed:\n{python_result.stderr}"
    assert python_result.stdout.strip() == "8"


def test_G3_verbatim_no_double_shift():
    """Literal index 2 (Atena) is folded to 1 by analyzer — codegen emits [1] verbatim.

    After analyzer folds index 2→1, codegen must emit 'grades[1]', NOT 'grades[0]'
    (which would be a double-shift) and NOT 'grades[2]' (which would re-emit the
    original unfolded index).  grades[1] in Python is the second element, value 7.
    """
    source = "grades = [5, 7, 9]\nshow grades[2]\n"
    result = _generate(source)
    assert "grades[1]" in result, (
        f"Expected 'grades[1]' (verbatim folded index) in output.\nGot:\n{result}"
    )
    assert "grades[0]" not in result, (
        f"'grades[0]' must NOT appear — that would be a double-shift.\nGot:\n{result}"
    )
    assert "grades[2]" not in result, (
        f"'grades[2]' must NOT appear — should have been folded by analyzer.\nGot:\n{result}"
    )
    python_result = subprocess.run(
        [sys.executable, "-c", result],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert python_result.returncode == 0, f"Generated Python crashed:\n{python_result.stderr}"
    assert python_result.stdout.strip() == "7"


def test_G3_verbatim_nested_index_no_double_shift():
    """Nested literal index: grid[1][2] (Atena) → grid[0][1] in Python (no double-shift).

    Analyzer folds outer index 1→0 and inner index 2→1.  Codegen must emit
    'grid[0][1]' verbatim — both indices shifted exactly once.
    grid[0][1] = second element of first sublist = 2.
    """
    source = "grid = [[1, 2], [3, 4]]\nshow grid[1][2]\n"
    result = _generate(source)
    assert "grid[0][1]" in result, (
        f"Expected 'grid[0][1]' (both indices folded once, verbatim) in output.\n"
        f"Got:\n{result}"
    )
    python_result = subprocess.run(
        [sys.executable, "-c", result],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert python_result.returncode == 0, f"Generated Python crashed:\n{python_result.stderr}"
    assert python_result.stdout.strip() == "2"


# ---------------------------------------------------------------------------
# Plan 04-05: Task 3 — Targeted fixture tests (G1_*_fixture + G2_*_execution)
# ---------------------------------------------------------------------------


def test_G1_keyword_mangle_fixture():
    """keyword_mangle.atena round-trips to exactly keyword_mangle.expected.py.

    The fixture uses 'pass' (a Python keyword) as a variable name.  The pipeline
    must mangle it to 'pass_' so the generated Python parses cleanly.
    """
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "keyword_mangle.atena").read_text()
    expected = (fixtures / "keyword_mangle.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"keyword_mangle fixture mismatch.\n--- expected ---\n{expected}\n--- got ---\n{result}"
    )
    assert "pass_" in result, (
        f"Expected mangled 'pass_' in generated output.\nGot:\n{result}"
    )


def test_G2_keyword_mangle_execution():
    """keyword_mangle.expected.py executes and prints '5'."""
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "keyword_mangle.expected.py").read_text()
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "5"


def test_G1_nested_repeat_fixture():
    """nested_repeat.atena round-trips to exactly nested_repeat.expected.py.

    Two nested repeat loops must use 2 distinct _atena_i* loop variables.
    """
    import re
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "nested_repeat.atena").read_text()
    expected = (fixtures / "nested_repeat.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"nested_repeat fixture mismatch.\n--- expected ---\n{expected}\n--- got ---\n{result}"
    )
    loop_vars = re.findall(r"_atena_i\d+", result)
    assert len(set(loop_vars)) == 2, (
        f"Expected 2 distinct _atena_i* loop variables in nested_repeat output.\n"
        f"Found: {set(loop_vars)}\nGot:\n{result}"
    )


def test_G2_nested_repeat_execution():
    """nested_repeat.expected.py executes and prints '6' (3 * 2 iterations)."""
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "nested_repeat.expected.py").read_text()
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "6"


def test_G1_dynamic_index_fixture():
    """dynamic_index.atena round-trips to exactly dynamic_index.expected.py.

    A variable index 'i' must route through the _atena_index runtime helper.
    """
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "dynamic_index.atena").read_text()
    expected = (fixtures / "dynamic_index.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"dynamic_index fixture mismatch.\n--- expected ---\n{expected}\n--- got ---\n{result}"
    )
    assert "_atena_index" in result, (
        f"Expected '_atena_index' helper in generated output for dynamic index.\nGot:\n{result}"
    )


def test_G2_dynamic_index_execution():
    """dynamic_index.expected.py executes and prints '5' (grades[i] where i=1, value at index 1)."""
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "dynamic_index.expected.py").read_text()
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "5"


def test_G1_concat_helper_fixture():
    """concat_helper.atena round-trips to exactly concat_helper.expected.py.

    A function with unknown-typed parameters using '+' must route through
    the _atena_concat runtime helper.
    """
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "concat_helper.atena").read_text()
    expected = (fixtures / "concat_helper.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"concat_helper fixture mismatch.\n--- expected ---\n{expected}\n--- got ---\n{result}"
    )
    assert "_atena_concat" in result, (
        f"Expected '_atena_concat' helper in generated output.\nGot:\n{result}"
    )


def test_G2_concat_helper_execution():
    """concat_helper.expected.py executes and prints '35' (str(3)+str(5), not 8)."""
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "concat_helper.expected.py").read_text()
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert result.stdout.strip() == "35"


def test_G1_dict_dot_write_fixture():
    """dict_dot_write.atena round-trips to exactly dict_dot_write.expected.py.

    Dict dot-write (student.name = 'Ana') must emit a subscript Store
    assignment (student['name'] = 'Ana') in the generated Python.
    """
    fixtures = Path(__file__).parent / "fixtures"
    source = (fixtures / "dict_dot_write.atena").read_text()
    expected = (fixtures / "dict_dot_write.expected.py").read_text()
    result = _generate(source)
    assert result == expected, (
        f"dict_dot_write fixture mismatch.\n--- expected ---\n{expected}\n--- got ---\n{result}"
    )


def test_G2_dict_dot_write_execution():
    """dict_dot_write.expected.py executes and prints 'Ana' then '9'."""
    fixtures = Path(__file__).parent / "fixtures"
    python_src = (fixtures / "dict_dot_write.expected.py").read_text()
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
    assert "Ana" in result.stdout, (
        f"Expected 'Ana' in output from dict dot-write fixture.\nGot:\n{result.stdout}"
    )
    assert "9" in result.stdout, (
        f"Expected '9' in output from dict dot-write fixture.\nGot:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# CR-01: Function-call site must mangle Python-keyword names
# ---------------------------------------------------------------------------


def test_CR01_keyword_function_call_mangled():
    """CR-01: Defining and calling a function whose name is a Python keyword must not crash.

    'function pass(n)\\n    return n\\nshow pass(5)\\n' previously raised an
    uncaught SyntaxError from the GEN-05 ast.parse() self-check because
    _emit_FunctionDef mangled the def name to 'pass_' but _emit_FunctionCall
    emitted the raw name 'pass', producing invalid Python.

    After the fix the call name is also mangled, so the generated Python
    contains 'def pass_' and 'pass_(5)', passes ast.parse(), and executing
    it prints '5'.
    """
    source = "function pass(n)\n    return n\nshow pass(5)\n"

    # Pipeline must not raise — _generate() calls generate() which runs GEN-05
    python_src = _generate(source)

    # Generated source must contain the mangled def AND the mangled call
    assert "def pass_" in python_src, (
        f"Expected 'def pass_' (mangled def) in generated output.\nGot:\n{python_src}"
    )
    assert "pass_(5)" in python_src, (
        f"Expected 'pass_(5)' (mangled call) in generated output.\nGot:\n{python_src}"
    )

    # Generated Python must parse cleanly (GEN-05 self-check already verified,
    # but assert explicitly so the failure message is clear)
    try:
        ast.parse(python_src)
    except SyntaxError as exc:
        raise AssertionError(
            f"CR-01: generated Python is not parseable after keyword mangling.\n"
            f"SyntaxError: {exc}\nGenerated:\n{python_src}"
        ) from exc

    # Generated Python must execute and print '5'
    result = subprocess.run(
        [sys.executable, "-c", python_src],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, (
        f"CR-01: generated Python crashed at runtime.\n"
        f"stderr:\n{result.stderr}\nGenerated:\n{python_src}"
    )
    assert result.stdout.strip() == "5", (
        f"CR-01: expected stdout '5', got {result.stdout.strip()!r}.\n"
        f"Generated:\n{python_src}"
    )
