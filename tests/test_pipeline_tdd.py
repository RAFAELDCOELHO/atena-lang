"""
TDD RED-phase test for pipeline.transpile() — Task 1.

This file confirms transpile() raises NotImplementedError before the
real implementation is wired in Phase 5. Tests here will fail until
pipeline.py is implemented; that is the expected RED state.
"""

from __future__ import annotations

import pytest

from atena.pipeline import transpile


def test_transpile_show_number_returns_str() -> None:
    """transpile('show 1\\n', ...) must return a str containing 'print', not raise."""
    result = transpile("show 1\n", "test.atena")
    assert result is not None, "transpile returned None; expected a Python string"
    assert "print" in result, f"Expected 'print' in output, got: {result!r}"


def test_transpile_lexer_error_returns_none() -> None:
    """transpile with an unterminated string must return None (lexer error path)."""
    result = transpile('show "\n', "test.atena")
    assert result is None, f"Expected None for lexer error, got: {result!r}"


def test_transpile_signature() -> None:
    """transpile must accept (source: str, filename: str) without raising TypeError."""
    # If the stub raises NotImplementedError the test will fail at the assertion.
    try:
        transpile("show 1\n", "test.atena")
    except NotImplementedError as exc:
        pytest.fail(f"transpile raised NotImplementedError: {exc}")
    except TypeError as exc:
        pytest.fail(f"transpile signature is wrong: {exc}")
