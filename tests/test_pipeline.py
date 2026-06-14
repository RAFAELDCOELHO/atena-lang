"""
Pipeline smoke tests — tests for transpile() in src/atena/pipeline.py.

Covers:
  - Happy path: 'show 1' → str containing 'print'
  - Lexer error path: unterminated string → None + stderr
  - Parser error path: bare 'if' → None
  - Semantic analyzer error path: undefined variable → None
  - school.atena golden fixture: full program → non-None Python source with
    expected constructs (make_greeting function, input() call)
  - stderr output: canonical 'Error on line ...' format confirmed via capsys

No subprocess calls — these are direct unit-level calls into pipeline.transpile().
Subprocess-level CLI tests live in tests/test_cli.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from atena.pipeline import transpile


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_transpile_show_number() -> None:
    """'show 1' transpiles to a str containing 'print'."""
    result = transpile("show 1\n", "t.atena")
    assert result is not None, "transpile returned None; expected a Python string"
    assert "print" in result, f"Expected 'print' in output. Got: {result!r}"


def test_transpile_show_number_contains_print_1() -> None:
    """'show 1' transpiles to a str that evaluates to printing 1."""
    result = transpile("show 1\n", "t.atena")
    assert result is not None
    assert "print(1)" in result, f"Expected 'print(1)' in output. Got: {result!r}"


def test_transpile_show_string() -> None:
    """'show \"hello\"' transpiles to a str containing 'print'."""
    result = transpile('show "hello"\n', "t.atena")
    assert result is not None, "transpile returned None; expected a Python string"
    assert "print" in result, f"Expected 'print' in output. Got: {result!r}"


# ---------------------------------------------------------------------------
# Error paths — each should return None
# ---------------------------------------------------------------------------

def test_transpile_lexer_error_returns_none() -> None:
    """Unterminated string forces a lexer error; transpile must return None."""
    result = transpile('show "\n', "t.atena")
    assert result is None, f"Expected None for lexer error. Got: {result!r}"


def test_transpile_parser_error_returns_none() -> None:
    """Bare 'if' with no condition is a parser-level syntax error → None."""
    result = transpile("if\n", "t.atena")
    assert result is None, f"Expected None for parser error. Got: {result!r}"


def test_transpile_analyzer_error_returns_none() -> None:
    """'show xyz' where xyz is undefined is an analyzer error → None."""
    result = transpile("show xyz\n", "t.atena")
    assert result is None, f"Expected None for analyzer error. Got: {result!r}"


# ---------------------------------------------------------------------------
# school.atena golden fixture
# ---------------------------------------------------------------------------

def test_transpile_school_atena() -> None:
    """school.atena transpiles to a non-None Python source with expected constructs."""
    school_path = Path(__file__).parent.parent / "examples" / "school.atena"
    source = school_path.read_text(encoding="utf-8")
    result = transpile(source, "school.atena")

    assert result is not None, (
        "school.atena transpile returned None; expected a complete Python program"
    )
    assert "def make_greeting" in result, (
        f"Expected 'def make_greeting' function in output. Got excerpt: {result[:300]!r}"
    )
    assert "input(" in result, (
        f"Expected 'input(' (from 'ask' statement) in output. Got excerpt: {result[:300]!r}"
    )


# ---------------------------------------------------------------------------
# stderr output: canonical format check
# ---------------------------------------------------------------------------

def test_transpile_error_printed_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    """On a lexer error, 'Error on line' is printed to stderr before returning None."""
    result = transpile('show "\n', "t.atena")
    assert result is None
    captured = capsys.readouterr()
    assert "Error on line" in captured.err, (
        f"Expected canonical error format in stderr. Got: {captured.err!r}"
    )
    assert "Traceback" not in captured.err, (
        f"Python traceback must not appear in stderr. Got: {captured.err!r}"
    )
