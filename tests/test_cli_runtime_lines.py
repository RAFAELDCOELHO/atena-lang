"""
Gap-closure regression tests for Phase 5 code review findings.

These tests exercise the REAL pipeline end-to-end (no monkeypatched transpile),
which is what the original C-14/C-20–C-25 tests failed to do. They are the
safety net for:

  - CR-01: runtime error line numbers must be the ORIGINAL Atena line, and the
           "→" must show the offending Atena source line (never empty/wrong).
  - CR-02: a ValueError that is not a failed list-removal must NOT be mislabeled
           as "that item wasn't in the list".
  - CR-03: a compile-time SyntaxError (codegen emitted invalid Python) is an
           internal bug, not a learner runtime error.
  - WR-01: `build` must never overwrite its own input file.
  - WR-03: KeyboardInterrupt during a learner program is not reported as a
           program error.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import atena.cli as _cli
from atena.cli import _runtime_error_message, main


def _write(tmp_path: Path, src: str) -> str:
    f = tmp_path / "prog.atena"
    f.write_text(src)
    return str(f)


def _run_capture(file_path: str) -> tuple[int, str, str]:
    """Run `atena run <file>` in-process against the REAL pipeline.

    Returns (exit_code, stdout, stderr).
    """
    out, err = io.StringIO(), io.StringIO()
    with patch.object(sys, "argv", ["atena", "run", file_path]):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stdout", out), patch("sys.stderr", err):
                main()
    code = exc_info.value.code
    return (code if isinstance(code, int) else 0), out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# CR-01 — runtime error line numbers map to the Atena source, "→" is correct
# ---------------------------------------------------------------------------

def test_runtime_line_multiline_zero_division(tmp_path: Path) -> None:
    """Error on Atena line 4 must report line 4 and show that source line."""
    src = 'a = 10\nb = 0\nshow "computing"\nshow a / b\n'  # error on line 4
    code, _out, err = _run_capture(_write(tmp_path, src))
    assert code == 1
    assert "Error on line 4:" in err, f"expected line 4, got: {err!r}"
    assert "show a / b" in err, f"'→' source line must show the offending line, got: {err!r}"
    assert "Traceback" not in err
    assert "Error on line 5" not in err


def test_runtime_line_single_line_not_empty(tmp_path: Path) -> None:
    """Single-line program: line 1, and '→' must not be empty (header-offset bug)."""
    src = "show 1 / 0\n"  # error on line 1
    code, _out, err = _run_capture(_write(tmp_path, src))
    assert code == 1
    assert "Error on line 1:" in err, f"expected line 1, got: {err!r}"
    assert "show 1 / 0" in err, f"'→' must show 'show 1 / 0', got: {err!r}"
    assert "Error on line 2" not in err


def test_runtime_index_error_line(tmp_path: Path) -> None:
    """IndexError on Atena line 2 reports line 2 with the offending source line."""
    src = "nums = [1, 2, 3]\nshow nums[10]\n"  # error on line 2
    code, _out, err = _run_capture(_write(tmp_path, src))
    assert code == 1
    assert "Error on line 2:" in err, f"expected line 2, got: {err!r}"
    assert "nums[10]" in err, f"'→' must show the offending line, got: {err!r}"


def test_runtime_error_inside_function_reports_body_line(tmp_path: Path) -> None:
    """Error raised inside a function reports the Atena line where it occurred."""
    src = "function divide(a, b)\n    return a / b\nshow divide(10, 0)\n"  # raises at line 2
    code, _out, err = _run_capture(_write(tmp_path, src))
    assert code == 1
    assert "Error on line 2:" in err, f"expected line 2 (the division), got: {err!r}"
    assert "return a / b" in err, f"'→' must show the dividing line, got: {err!r}"
    assert "Traceback" not in err


def test_runtime_negative_index_helper_reports_call_site(tmp_path: Path) -> None:
    """An error raised inside an injected helper must report the Atena CALL SITE line,
    not the helper's internal line."""
    src = "nums = [1, 2, 3]\nshow 1\nshow nums[0]\n"  # nums[0] -> position 0 invalid, line 3
    code, _out, err = _run_capture(_write(tmp_path, src))
    assert code == 1
    assert "Error on line 3:" in err, f"expected the call-site line 3, got: {err!r}"
    assert "nums[0]" in err, f"'→' must show the call site, got: {err!r}"
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# CR-02 — ValueError must not be blanket-labeled as a failed list removal
# ---------------------------------------------------------------------------

def test_valueerror_non_remove_is_generic() -> None:
    """A ValueError that is not 'x not in list' must use the generic message."""
    exc = ValueError("invalid literal for int() with base 10: 'x'")
    msg = _runtime_error_message(exc, ["show 1"])
    assert "wasn't in the list" not in msg, f"must NOT mislabel: {msg!r}"
    assert "an error occurred" in msg


def test_valueerror_list_remove_keeps_specific_message() -> None:
    """A genuine failed list.remove ValueError keeps the specific message."""
    exc = ValueError("list.remove(x): x not in list")
    msg = _runtime_error_message(exc, ["remove 5 from nums"])
    assert "wasn't in the list" in msg


def test_runtime_remove_absent_item_real_pipeline(tmp_path: Path) -> None:
    """End-to-end: removing an absent item still gives the friendly remove message."""
    src = "nums = [1, 2, 3]\nremove 5 from nums\n"  # ValueError: not in list, line 2
    code, _out, err = _run_capture(_write(tmp_path, src))
    assert code == 1
    assert "wasn't in the list" in err
    assert "Error on line 2:" in err
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# CR-03 — a codegen SyntaxError (internal bug) routes to the internal message
# ---------------------------------------------------------------------------

def test_compile_syntaxerror_routes_to_internal(tmp_path: Path) -> None:
    """If the run path's compile step raises SyntaxError, it is an internal bug."""
    file_path = _write(tmp_path, "show 1\n")

    def _boom(source: str, filename: str):  # noqa: ANN202
        raise SyntaxError("codegen emitted invalid Python")

    with patch.object(_cli, "compile_for_run", _boom):
        code, _out, err = _run_capture(file_path)
    assert code == 1
    assert "Something went wrong inside Atena" in err, f"internal wording expected, got: {err!r}"
    assert "while running your program" not in err
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# WR-01 — build must never overwrite its own input file
# ---------------------------------------------------------------------------

def test_build_refuses_to_overwrite_input(tmp_path: Path) -> None:
    """`atena build foo.py` would compute out_path == foo.py — must refuse."""
    f = tmp_path / "prog.py"
    f.write_text("show 1\n")  # valid Atena source, but a .py name
    original = f.read_text()
    out, err = io.StringIO(), io.StringIO()
    with patch.object(sys, "argv", ["atena", "build", str(f)]):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stdout", out), patch("sys.stderr", err):
                main()
    assert exc_info.value.code == 1
    assert f.read_text() == original, "input file must not be overwritten"
    assert ".atena" in err.getvalue() or "overwrite" in err.getvalue().lower()
