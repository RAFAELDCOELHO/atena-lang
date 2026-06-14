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
# C-1 — atena run <existing_file> → executes program, exit 0
# ---------------------------------------------------------------------------

def test_c1_run_existing_file_executes(existing_atena_file: str) -> None:
    """C-1: 'atena run <file>' with a valid program executes it and exits 0.

    The fixture writes 'show 1\\n', which transpiles to print(1) → output '1'.
    Phase 5 replaces the old placeholder assertion with the real output check.
    """
    result = run_cli("run", existing_atena_file)
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    assert "1" in result.stdout, (
        f"Expected '1' in stdout from 'show 1'. Got stdout: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr, (
        f"Python traceback must not appear. Got: {result.stdout + result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# C-2 — atena build <existing_file> → emits .py file, exit 0
# ---------------------------------------------------------------------------

def test_c2_build_existing_file_emits_py(existing_atena_file: str) -> None:
    """C-2: 'atena build <file>' with a valid program writes the .py file and exits 0.

    Phase 5 replaces the old placeholder assertion with the real 'Built' message check.
    """
    result = run_cli("build", existing_atena_file)
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert 'Built "prog.py".' in combined, (
        f"Expected 'Built ...' message in output. Got: {combined!r}"
    )
    assert "Traceback" not in combined, (
        f"Python traceback must not appear. Got: {combined!r}"
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


# ---------------------------------------------------------------------------
# C-11 — directory-as-file → "is a folder" message, exit 1, no traceback (WR-04)
# ---------------------------------------------------------------------------

def test_c11_directory_as_file_plain_english_error(tmp_path: Path) -> None:
    """C-11: 'atena run <directory>' → folder-not-a-file message, exit 1, no traceback."""
    result = run_cli("run", str(tmp_path))
    assert result.returncode == 1, (
        f"Expected exit 1, got {result.returncode}"
    )
    combined = result.stdout + result.stderr
    assert "is a folder" in combined, (
        f"Expected folder-not-a-file message. Got: {combined!r}"
    )
    assert "Traceback" not in combined, (
        f"Python traceback must not appear: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-12 — non-UTF-8 file → "doesn't look like a text file" message, exit 1, no traceback (WR-05)
# ---------------------------------------------------------------------------

def test_c12_non_utf8_file_plain_english_error(tmp_path: Path) -> None:
    """C-12: Binary file → 'doesn't look like a text file' message, exit 1, no traceback."""
    f = tmp_path / "binary.atena"
    # Write raw bytes that are not valid UTF-8 (Latin-1 encoded text with 0x80-0xFF)
    f.write_bytes(b"\xff\xfe\x00\x01non-utf8 content")

    result = run_cli("run", str(f))
    assert result.returncode == 1, (
        f"Expected exit 1, got {result.returncode}"
    )
    combined = result.stdout + result.stderr
    assert "doesn't look like a text file" in combined, (
        f"Expected non-UTF-8 message. Got: {combined!r}"
    )
    assert "Traceback" not in combined, (
        f"Python traceback must not appear: {combined!r}"
    )


# ---------------------------------------------------------------------------
# C-13 — build to read-only directory → plain-English write error, exit 1, no traceback (WR-01)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix file permissions not applicable on Windows",
)
@pytest.mark.skipif(
    os.getuid() == 0,  # type: ignore[attr-defined]
    reason="Root user can write anywhere; permission test is meaningless as root",
)
def test_c13_build_unwritable_output_plain_english_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-13: 'atena build' with unwritable output dir → plain-English error, exit 1, no traceback."""
    import atena.cli as _cli
    import io

    # Put the source file inside a read-only sub-directory so the .py output
    # would also land inside it (same dir, same stem).
    src_dir = tmp_path / "readonly"
    src_dir.mkdir()
    f = src_dir / "prog.atena"
    f.write_text("show 1\n")
    # Make the directory read-only (no write permission) AFTER writing the source file
    src_dir.chmod(0o555)

    # Simulate transpile returning generated Python so the build-write path is reached
    def _transpile_ok(source: str, filename: str) -> str | None:
        return "x = 1\n"

    monkeypatch.setattr(_cli, "transpile", _transpile_ok)
    monkeypatch.setattr(sys, "argv", ["atena", "build", str(f)])

    captured_stderr = io.StringIO()
    try:
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", captured_stderr):
                _cli.main()

        assert exc_info.value.code == 1, (
            f"Expected SystemExit(1), got SystemExit({exc_info.value.code})"
        )
        err_output = captured_stderr.getvalue()
        assert "I couldn't" in err_output, (
            f"Expected a plain-English I-couldn't message. Got: {err_output!r}"
        )
        assert "Traceback" not in err_output, (
            f"Python traceback must not appear: {err_output!r}"
        )
    finally:
        src_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# C-14 — exec runtime error → plain-English message, exit 1, no traceback (CR-01)
# ---------------------------------------------------------------------------

def test_c14_exec_runtime_error_no_traceback(
    existing_atena_file: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-14: Division-by-zero in exec'd code → plain-English message, no traceback."""
    import atena.cli as _cli
    import io

    # Simulate transpile returning code that raises ZeroDivisionError at runtime
    def _transpile_boom(source: str, filename: str) -> str | None:
        return "x = 1 / 0\n"

    monkeypatch.setattr(_cli, "transpile", _transpile_boom)
    monkeypatch.setattr(sys, "argv", ["atena", "run", existing_atena_file])

    captured_stderr = io.StringIO()
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.stderr", captured_stderr):
            _cli.main()

    assert exc_info.value.code == 1, (
        f"Expected SystemExit(1), got SystemExit({exc_info.value.code})"
    )
    err_output = captured_stderr.getvalue()
    assert "Something went wrong inside Atena" in err_output, (
        f"Expected internal-error message. Got: {err_output!r}"
    )
    assert "Traceback" not in err_output, (
        f"Python traceback must not appear: {err_output!r}"
    )
    assert "ZeroDivisionError" not in err_output, (
        f"Raw exception class name must not appear: {err_output!r}"
    )
