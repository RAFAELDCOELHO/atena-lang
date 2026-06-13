"""
TDD tests for the Atena CLI — argparse, file errors, placeholder, internal-error fallback.

Tests C-1 through C-10 written BEFORE the implementation (RED phase).
Tests C-1 to C-6, C-9, C-10 use subprocess; C-7 and C-8 monkey-patch transpile and call main().
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from atena.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI as a subprocess with the given arguments."""
    return subprocess.run(
        [sys.executable, "-m", "atena", *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def existing_atena_file(tmp_path: Path) -> str:
    """Create a temporary .atena file and return its path."""
    f = tmp_path / "prog.atena"
    f.write_text("show 1\n")
    return str(f)


# ---------------------------------------------------------------------------
# C-1 — atena run <existing_file> → placeholder, exit 0
# ---------------------------------------------------------------------------

def test_c1_run_existing_file_shows_placeholder(existing_atena_file: str) -> None:
    """C-1: 'atena run <file>' with existing file prints placeholder and exits 0."""
    result = run_cli("run", existing_atena_file)
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "Atena can read your program, but running it isn't built yet" in combined, (
        f"Expected placeholder message in output. Got: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-2 — atena build <existing_file> → placeholder, exit 0
# ---------------------------------------------------------------------------

def test_c2_build_existing_file_shows_placeholder(existing_atena_file: str) -> None:
    """C-2: 'atena build <file>' with existing file prints placeholder and exits 0."""
    result = run_cli("build", existing_atena_file)
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "Atena can read your program, but running it isn't built yet" in combined, (
        f"Expected placeholder message in output. Got: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-3 — atena run <missing_file> → plain-English error, exit 1
# ---------------------------------------------------------------------------

def test_c3_run_missing_file_plain_english_error() -> None:
    """C-3: 'atena run missing.atena' prints exact file-not-found message and exits 1."""
    result = run_cli("run", "missing.atena")
    assert result.returncode == 1, (
        f"Expected exit 1, got {result.returncode}"
    )
    combined = result.stdout + result.stderr
    assert 'I couldn\'t find a file called "missing.atena".' in combined, (
        f"Expected file-not-found message. Got: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-4 — atena build <missing_file> → plain-English error, exit 1
# ---------------------------------------------------------------------------

def test_c4_build_missing_file_plain_english_error() -> None:
    """C-4: 'atena build missing.atena' prints exact file-not-found message and exits 1."""
    result = run_cli("build", "missing.atena")
    assert result.returncode == 1, (
        f"Expected exit 1, got {result.returncode}"
    )
    combined = result.stdout + result.stderr
    assert 'I couldn\'t find a file called "missing.atena".' in combined, (
        f"Expected file-not-found message. Got: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-5 — atena --help → usage text, exit 0, no traceback
# ---------------------------------------------------------------------------

def test_c5_help_no_traceback() -> None:
    """C-5: 'atena --help' prints usage text, exits 0, and contains no traceback."""
    result = run_cli("--help")
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "usage" in combined.lower(), (
        f"Expected 'usage' in help output. Got: {combined!r}"
    )
    assert "Traceback" not in combined, (
        f"Python traceback found in help output: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-6 — atena run --help → usage text, exit 0, no traceback
# ---------------------------------------------------------------------------

def test_c6_subcommand_help_no_traceback() -> None:
    """C-6: 'atena run --help' prints usage text, exits 0, no traceback."""
    result = run_cli("run", "--help")
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "usage" in combined.lower(), (
        f"Expected 'usage' in run --help output. Got: {combined!r}"
    )
    assert "Traceback" not in combined, (
        f"Python traceback found in subcommand help output: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-7 — internal error fallback, no line: stderr has friendly message, no traceback
# ---------------------------------------------------------------------------

def test_c7_internal_error_no_line(
    existing_atena_file: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-7: RuntimeError from transpile → friendly internal-error message, no traceback."""
    import atena.pipeline as _pipeline

    def _boom(source: str, filename: str) -> str | None:
        raise RuntimeError("internal boom")

    monkeypatch.setattr(_pipeline, "transpile", _boom)

    # Re-import main after patching so it picks up the new transpile
    import atena.cli as _cli
    monkeypatch.setattr(_cli, "transpile", _boom)

    import io

    captured_stderr = io.StringIO()
    monkeypatch.setattr(sys, "argv", ["atena", "run", existing_atena_file])
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.stderr", captured_stderr):
            _cli.main.__module__  # touch module
            _cli.main()

    assert exc_info.value.code == 1, (
        f"Expected SystemExit(1), got SystemExit({exc_info.value.code})"
    )
    err_output = captured_stderr.getvalue()
    assert "Something went wrong inside Atena" in err_output, (
        f"Expected internal-error message in stderr. Got: {err_output!r}"
    )
    assert "near line" not in err_output, (
        f"'near line N' should NOT appear when no atena_line on exception: {err_output!r}"
    )
    assert "Traceback" not in err_output, (
        f"Python traceback must not appear in stderr: {err_output!r}"
    )
    assert "this isn't your fault" in err_output, (
        f"Expected blame-free message. Got: {err_output!r}"
    )


# ---------------------------------------------------------------------------
# C-8 — internal error fallback, with line: stderr has "near line 7", no traceback
# ---------------------------------------------------------------------------

def test_c8_internal_error_with_line(
    existing_atena_file: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-8: Exception with atena_line=7 → 'near line 7' in message, no traceback."""
    import atena.cli as _cli

    def _boom_with_line(source: str, filename: str) -> str | None:
        err = RuntimeError("with line info")
        err.atena_line = 7  # type: ignore[attr-defined]
        raise err

    monkeypatch.setattr(_cli, "transpile", _boom_with_line)

    import io

    captured_stderr = io.StringIO()
    monkeypatch.setattr(sys, "argv", ["atena", "run", existing_atena_file])
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.stderr", captured_stderr):
            _cli.main()

    assert exc_info.value.code == 1, (
        f"Expected SystemExit(1), got SystemExit({exc_info.value.code})"
    )
    err_output = captured_stderr.getvalue()
    assert "near line 7" in err_output, (
        f"Expected 'near line 7' in stderr. Got: {err_output!r}"
    )
    assert "Traceback" not in err_output, (
        f"Python traceback must not appear in stderr: {err_output!r}"
    )
    assert "this isn't your fault" in err_output, (
        f"Expected blame-free message. Got: {err_output!r}"
    )


# ---------------------------------------------------------------------------
# C-9 — atena with no args → exit 0 or 2, no Python traceback
# ---------------------------------------------------------------------------

def test_c9_no_subcommand_no_traceback() -> None:
    """C-9: 'atena' with no args exits 0 or 2; no Python traceback in output."""
    result = run_cli()
    combined = result.stdout + result.stderr
    assert result.returncode in (0, 2), (
        f"Expected exit 0 or 2, got {result.returncode}. Output: {combined!r}"
    )
    assert "Traceback" not in combined, (
        f"Python traceback found in no-args output: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-10 — unreadable file → plain-English error, exit 1
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix file permissions not applicable on Windows",
)
@pytest.mark.skipif(
    os.getuid() == 0,  # type: ignore[attr-defined]
    reason="Root user can read any file; permission test is meaningless as root",
)
def test_c10_unreadable_file(tmp_path: Path) -> None:
    """C-10: A file with 000 permissions → 'I couldn't read' message, exit 1."""
    f = tmp_path / "locked.atena"
    f.write_text("show 1\n")
    f.chmod(0o000)  # no permissions

    try:
        result = run_cli("run", str(f))
        assert result.returncode == 1, (
            f"Expected exit 1, got {result.returncode}"
        )
        combined = result.stdout + result.stderr
        assert "I couldn't read" in combined, (
            f"Expected unreadable-file message. Got: {combined!r}"
        )
    finally:
        # Restore permissions so tmp_path cleanup can delete the file
        f.chmod(stat.S_IRUSR | stat.S_IWUSR)
