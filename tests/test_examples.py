"""
Execution tests for the Atena concept-ladder examples.

One test per numbered rung (01-show through 09-dicts) plus one for the
school.atena capstone.  Every test runs `atena run <example>` via subprocess
so it exercises the real installed pipeline end-to-end — no monkeypatching.

Interactive rungs (02-ask, school.atena) feed canned stdin via subprocess
input= and use timeout=10 to guard against a hanging ask in CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


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


# ---------------------------------------------------------------------------
# Non-interactive rungs
# ---------------------------------------------------------------------------

def test_example_01_show_runs_to_completion() -> None:
    """01-show.atena exits 0 and produces output (no interactive input needed)."""
    result = run_cli("run", "examples/01-show.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert result.stdout.strip() != "", (
        f"Expected some output. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_03_variables_runs_to_completion() -> None:
    """03-variables.atena exits 0 and shows integer arithmetic (no floats)."""
    result = run_cli("run", "examples/03-variables.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    # Integers-only contract: 10 / 3 floor-divides to 3, never a float.
    assert "Quotient: 3" in result.stdout, (
        f"Expected integer quotient 'Quotient: 3'. Got: {result.stdout!r}"
    )
    assert "3.3" not in result.stdout, (
        f"Division must not produce a float. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_04_conditionals_runs_to_completion() -> None:
    """04-conditionals.atena exits 0 and prints the branch result."""
    result = run_cli("run", "examples/04-conditionals.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Passing" in result.stdout, (
        f"Expected 'Passing' in stdout. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_05_while_runs_to_completion() -> None:
    """05-while.atena exits 0 and counts from 1 to 5."""
    result = run_cli("run", "examples/05-while.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Count: 1" in result.stdout, (
        f"Expected counting output. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_06_repeat_runs_to_completion() -> None:
    """06-repeat.atena exits 0 and repeats the message 3 times."""
    result = run_cli("run", "examples/06-repeat.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert result.stdout.count("Atena is fun!") == 3, (
        f"Expected message repeated 3 times. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_07_functions_runs_to_completion() -> None:
    """07-functions.atena exits 0 and shows the doubled values."""
    result = run_cli("run", "examples/07-functions.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Double of 5 is: 10" in result.stdout, (
        f"Expected doubled result. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_08_lists_runs_to_completion() -> None:
    """08-lists.atena exits 0 and demonstrates 1-indexed list access."""
    result = run_cli("run", "examples/08-lists.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "First grade: 8" in result.stdout, (
        f"Expected 1-indexed access result. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_09_dicts_runs_to_completion() -> None:
    """09-dicts.atena exits 0 and demonstrates dot read and dot write."""
    result = run_cli("run", "examples/09-dicts.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Ana" in result.stdout, (
        f"Expected dot-read result. Got: {result.stdout!r}"
    )
    assert "Updated age: 21" in result.stdout, (
        f"Expected dot-write result. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Interactive rungs (use subprocess directly with input= and timeout=10)
# ---------------------------------------------------------------------------

def test_example_02_ask_runs_to_completion() -> None:
    """02-ask.atena exits 0 when given canned stdin 'Alice' and echoes the name back."""
    result = subprocess.run(
        [sys.executable, "-m", "atena", "run", "examples/02-ask.atena"],
        capture_output=True,
        text=True,
        input="Alice\n",
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Alice" in result.stdout, (
        f"Expected the input name echoed back. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr


def test_example_school_atena_capstone() -> None:
    """school.atena (capstone) exits 0 with canned stdin 'Ana' and prints 'Welcome, Ana'."""
    result = subprocess.run(
        [sys.executable, "-m", "atena", "run", "examples/school.atena"],
        capture_output=True,
        text=True,
        input="Ana\n",
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Welcome, Ana" in result.stdout, (
        f"Expected 'Welcome, Ana' in stdout. Got: {result.stdout!r}"
    )
    # Integers-only: average is floor division (30 // 4 == 7), never 7.5.
    assert "Your average is: 7" in result.stdout, (
        f"Expected integer average 'Your average is: 7'. Got: {result.stdout!r}"
    )
    assert "7.5" not in result.stdout, (
        f"Average must be an integer, not a float. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr
