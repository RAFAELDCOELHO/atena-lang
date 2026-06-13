"""
TDD tests for ErrorCollector — the diagnostics spine.

All tests are written BEFORE the implementation (RED phase).
They assert exact string output as specified in PLAN 00-02.
"""

from __future__ import annotations

import inspect
import re

import pytest

from atena.errors import ErrorCollector, suggest, ATENA_KEYWORDS


# ---------------------------------------------------------------------------
# Test 1 — Empty collector
# ---------------------------------------------------------------------------

def test_empty_collector_is_empty() -> None:
    """A fresh ErrorCollector has no errors."""
    ec = ErrorCollector()
    assert ec.is_empty() is True


def test_empty_collector_report_is_empty_string() -> None:
    """report() on an empty collector returns empty string."""
    ec = ErrorCollector()
    assert ec.report() == ""


# ---------------------------------------------------------------------------
# Test 2 — Single error format (canonical exemplar)
# ---------------------------------------------------------------------------

def test_single_error_format() -> None:
    """Single error produces exact canonical format."""
    ec = ErrorCollector()
    ec.add(4, 'I don\'t know what "score" is yet.', "show score")
    expected = 'Error on line 4: I don\'t know what "score" is yet.\n  → show score'
    assert ec.report() == expected


# ---------------------------------------------------------------------------
# Test 3 — Multi-error sort by line number
# ---------------------------------------------------------------------------

def test_multi_error_sort_order() -> None:
    """Errors are sorted by line number ascending regardless of insertion order."""
    ec = ErrorCollector()
    ec.add(9, "error on nine", "line nine")
    ec.add(1, "error on one", "line one")
    ec.add(4, "error on four", "line four")

    report = ec.report()
    pos_1 = report.index("Error on line 1")
    pos_4 = report.index("Error on line 4")
    pos_9 = report.index("Error on line 9")

    assert pos_1 < pos_4 < pos_9, "Errors must appear sorted by line number"


# ---------------------------------------------------------------------------
# Test 4 — All errors collected (not just first)
# ---------------------------------------------------------------------------

def test_all_three_errors_appear() -> None:
    """report() contains all three Error on line headers."""
    ec = ErrorCollector()
    ec.add(9, "error nine", "src nine")
    ec.add(1, "error one", "src one")
    ec.add(4, "error four", "src four")

    report = ec.report()
    assert "Error on line 1" in report
    assert "Error on line 4" in report
    assert "Error on line 9" in report


# ---------------------------------------------------------------------------
# Test 5 — Dedup: identical (line, message) collapses to one
# ---------------------------------------------------------------------------

def test_dedup_identical_error() -> None:
    """Adding the same (line, message, source_line) twice shows only one block."""
    ec = ErrorCollector()
    ec.add(3, "same message", "x")
    ec.add(3, "same message", "x")

    report = ec.report()
    # Count exact occurrences of "Error on line 3" in report
    count = report.count("Error on line 3")
    assert count == 1, f"Expected 1 occurrence of 'Error on line 3', got {count}"


# ---------------------------------------------------------------------------
# Test 6 — Same line, different message → both appear
# ---------------------------------------------------------------------------

def test_same_line_different_message_both_appear() -> None:
    """Two errors on same line with different messages both appear in report."""
    ec = ErrorCollector()
    ec.add(3, "message A", "x")
    ec.add(3, "message B", "x")

    report = ec.report()
    assert "message A" in report
    assert "message B" in report


# ---------------------------------------------------------------------------
# Test 7 — Cap at ERROR_CAP (10); overflow line appended
# ---------------------------------------------------------------------------

def test_cap_at_ten_with_overflow_line() -> None:
    """14 distinct errors → 10 error blocks + overflow line for remaining 4."""
    ec = ErrorCollector()
    for i in range(1, 15):  # lines 1..14
        ec.add(i, f"error message {i}", f"source line {i}")

    report = ec.report()

    # Exactly 10 "Error on line" blocks shown
    error_block_count = len(re.findall(r"^Error on line \d+", report, re.MULTILINE))
    assert error_block_count == 10, (
        f"Expected 10 error blocks, got {error_block_count}"
    )

    # Overflow line present and exact
    assert "…and 4 more. Fix some and run again to see the rest." in report

    # No 11th error block
    assert report.count("Error on line") == 10


# ---------------------------------------------------------------------------
# Test 8 — Dedup before cap: 8 unique + 5 duplicates → 8 shown, no overflow
# ---------------------------------------------------------------------------

def test_dedup_before_cap() -> None:
    """8 unique errors + 5 duplicates of #1 → 8 shown, no overflow line."""
    ec = ErrorCollector()
    # 8 unique errors
    for i in range(1, 9):
        ec.add(i, f"unique error {i}", f"source {i}")
    # 5 duplicates of error #1
    for _ in range(5):
        ec.add(1, "unique error 1", "source 1")

    report = ec.report()

    error_block_count = len(re.findall(r"^Error on line \d+", report, re.MULTILINE))
    assert error_block_count == 8, (
        f"Expected 8 error blocks after dedup, got {error_block_count}"
    )
    assert "more. Fix some" not in report, "No overflow line expected for 8 unique errors"


# ---------------------------------------------------------------------------
# Test 9 — is_empty() returns False after add()
# ---------------------------------------------------------------------------

def test_is_empty_false_after_add() -> None:
    """is_empty() returns False after any add() call."""
    ec = ErrorCollector()
    assert ec.is_empty() is True
    ec.add(1, "some error", "some source")
    assert ec.is_empty() is False


# ---------------------------------------------------------------------------
# Test 10 — No Python jargon in any string literal inside errors.py
# ---------------------------------------------------------------------------

def test_no_jargon_in_errors_py() -> None:
    """No forbidden Python jargon appears in any string literal in errors.py."""
    import atena.errors as _errors_mod

    source = inspect.getsource(_errors_mod)
    forbidden = ["token", "AST", "DEDENT", "arity", "NoneType"]

    # Extract only string literals by removing comments and non-string lines.
    # We look for the forbidden words in string literals only.
    # Simple approach: find all quoted strings (single, double, triple) in the source.
    # The format template itself must not use jargon.
    string_literal_pattern = re.compile(
        r'"""[\s\S]*?"""|'   # triple double-quoted
        r"'''[\s\S]*?'''|"   # triple single-quoted
        r'"[^"\n]*"|'        # double-quoted
        r"'[^'\n]*'",        # single-quoted
        re.MULTILINE,
    )
    string_literals = " ".join(string_literal_pattern.findall(source))

    for word in forbidden:
        assert word not in string_literals, (
            f"Forbidden jargon word '{word}' found in a string literal in errors.py"
        )


# ---------------------------------------------------------------------------
# Tests S-1 through S-11 — suggest() and ATENA_KEYWORDS (Plan 00-04)
# ---------------------------------------------------------------------------

def test_s1_typo_caught() -> None:
    """S-1: A close typo returns 'Did you mean "score"?'."""
    result = suggest("scr", ["score", "show", "ask"])
    assert result == 'Did you mean "score"?'


def test_s2_keyword_typo_caught() -> None:
    """S-2: A keyword typo returns 'Did you mean "show"?'."""
    result = suggest("shwo", list(ATENA_KEYWORDS))
    assert result == 'Did you mean "show"?'


def test_s3_wild_miss_silenced() -> None:
    """S-3: A wild miss with no close candidate returns None."""
    result = suggest("banana", ["score", "show", "ask"])
    assert result is None


def test_s4_case_only_mismatch() -> None:
    """S-4: Case-only mismatch returns the D-06 form with capitalization note."""
    result = suggest("Score", ["score", "show", "ask"])
    assert result == 'Did you mean "score"? Names must match capitalization exactly.'


def test_s5_case_only_takes_priority() -> None:
    """S-5: Case-only mismatch takes priority over fuzzy matching."""
    result = suggest("Score", ["score"])
    assert result == 'Did you mean "score"? Names must match capitalization exactly.'


def test_s6_single_best_result() -> None:
    """S-6: Only ONE suggestion returned even when multiple candidates are close."""
    result = suggest("scre", ["score", "screech"])
    assert result == 'Did you mean "score"?'


def test_s7_deterministic_tie_breaking() -> None:
    """S-7: Repeated calls return the same result — no randomness."""
    results = {suggest("ab", ["ac", "ad"]) for _ in range(10)}
    assert len(results) == 1, "suggest() must be deterministic across calls"


def test_s8_empty_candidate_list() -> None:
    """S-8: Empty candidate list returns None without crashing."""
    result = suggest("xyz", [])
    assert result is None


def test_s9_exact_match_not_suggested() -> None:
    """S-9: Exact match in candidates returns None — no suggestion needed."""
    result = suggest("score", ["score"])
    assert result is None


def test_s10_atena_keywords_count_and_membership() -> None:
    """S-10: ATENA_KEYWORDS has exactly 19 entries including 'show' and 'function'.

    The plan spec lists 19 keywords (show ask if else while repeat times and or
    not function return add to remove from length true false), consistent with
    tokens.KEYWORDS which also has 19 entries and its own comment noting 18 — that
    comment had an off-by-one; the authoritative count comes from the enumerated list.
    """
    assert len(ATENA_KEYWORDS) == 19
    assert "show" in ATENA_KEYWORDS
    assert "function" in ATENA_KEYWORDS


def test_s11_case_only_check_case_insensitive() -> None:
    """S-11: SHOW (all caps) vs 'show' in keywords triggers the D-06 message."""
    result = suggest("SHOW", list(ATENA_KEYWORDS))
    assert result == 'Did you mean "show"? Names must match capitalization exactly.'


# ---------------------------------------------------------------------------
# Test S-12 — WR-03: duplicate-candidate contract pinned
# ---------------------------------------------------------------------------

def test_s12_duplicate_candidate_exact_match_returns_none() -> None:
    """S-12: suggest("x", ["x", "X", "xx"]) returns None — exact same-case match wins.

    Pins the contract: candidates may contain duplicates; the first exact
    same-case match short-circuits and returns None (no suggestion needed).
    "X" (different case) and "xx" (typo) do not override the exact hit.
    """
    result = suggest("x", ["x", "X", "xx"])
    assert result is None, (
        f'Expected None for exact match "x" in candidates, got: {result!r}'
    )


# ---------------------------------------------------------------------------
# Test S-13 — WR-02: fuzzy match beats misleading case-only match
# ---------------------------------------------------------------------------

def test_s13_fuzzy_beats_case_only_mismatch() -> None:
    """S-13: suggest("scor", ["score", "SCOR"]) returns the same-case fuzzy match.

    "SCOR" is an exact case-insensitive hit, but "score" is a better same-case
    fuzzy match. The fixed algorithm runs fuzzy first and should return "score"
    with the plain 'Did you mean' form (not a misleading capitalisation note).
    """
    result = suggest("scor", ["score", "SCOR"])
    assert result == 'Did you mean "score"?', (
        f'Expected plain fuzzy suggestion for "score", got: {result!r}'
    )
