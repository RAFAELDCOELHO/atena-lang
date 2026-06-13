"""
Error collection and reporting for the Atena transpiler.

This is the single source of truth for the error format:
  Error on line {N}: {plain English message}
    → {offending source line}

ErrorCollector is injected into each pipeline phase and accumulates
errors across the entire run. The pipeline gates codegen on .is_empty().
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

ERROR_CAP: int = 10


@dataclass
class _ErrorRecord:
    """Internal record for a single collected error."""

    line: int
    message: str
    source_line: str


class ErrorCollector:
    """Accumulates plain-English errors across all transpiler phases."""

    def __init__(self) -> None:
        self._records: list[_ErrorRecord] = []

    def add(self, line: int, message: str, source_line: str) -> None:
        """Append a new error record (duplicates are collapsed at report time)."""
        self._records.append(_ErrorRecord(line=line, message=message, source_line=source_line))

    def is_empty(self) -> bool:
        """Return True if no errors have been recorded yet."""
        return len(self._records) == 0

    def report(self) -> str:
        """Return the full formatted error block, or empty string if no errors.

        Processing order:
        1. Dedup by (line, message) — keeps first occurrence, preserves order.
        2. Stable-sort by line number ascending.
        3. Split at ERROR_CAP (10).
        4. Format each of the first 10 as the canonical template.
        5. If overflow: append the overflow line.
        6. Join error blocks with blank-line separator; overflow line follows
           immediately after the last error block (single newline).
        """
        if not self._records:
            return ""

        # Step 1: dedup by (line, message), preserving first-occurrence order.
        seen: set[tuple[int, str]] = set()
        unique: list[_ErrorRecord] = []
        for rec in self._records:
            key = (rec.line, rec.message)
            if key not in seen:
                seen.add(key)
                unique.append(rec)

        # Step 2: stable sort by line number ascending.
        unique.sort(key=lambda r: r.line)

        # Step 3: split at cap.
        shown = unique[:ERROR_CAP]
        overflow_count = len(unique) - ERROR_CAP

        # Step 4: format each shown error using the canonical template.
        blocks = [
            f"Error on line {r.line}: {r.message}\n  → {r.source_line}"
            for r in shown
        ]

        # Step 5 + 6: join blocks; append overflow line if needed.
        result = "\n\n".join(blocks)
        if overflow_count > 0:
            result += f"\n…and {overflow_count} more. Fix some and run again to see the rest."

        return result


ATENA_KEYWORDS: list[str] = [
    "show", "ask", "if", "else", "while", "repeat", "times",
    "and", "or", "not", "function", "return", "add", "to",
    "remove", "from", "length", "true", "false",
]
"""All 19 Atena v1.0 reserved words as a plain list.

Phases that report unknown-name errors can build a candidate set like:
    user_candidates = list(ATENA_KEYWORDS) + known_variable_names
This list is maintained independently — errors.py must not import sibling
modules so it remains usable from any pipeline phase without circular imports.
"""


def suggest(name: str, candidates: list[str]) -> str | None:
    """Return a ready-to-append suggestion string, or None if no close match.

    Algorithm:
    1. Return None immediately if candidates is empty.
    2. Return None if name is already an exact match in candidates.
    3. Case-only check first (D-06): if any candidate matches case-insensitively,
       return the D-06 form with capitalization note.
    4. Fuzzy check via difflib.get_close_matches (cutoff=0.6, n=1).
    5. Return None if no match found.

    The candidate set is caller-supplied — this function accepts any arbitrary
    list of names (variables, keywords, or any mix). Candidate set size is
    bounded in practice by the number of names in one Atena program (a few
    hundred at most), so difflib's O(n*m) cost is not a concern.
    """
    if not candidates:
        return None
    if name in candidates:
        return None

    # Case-only check: find the first candidate whose lowercase matches.
    name_lower = name.lower()
    for candidate in candidates:
        if name_lower == candidate.lower():
            return f'Did you mean "{candidate}"? Names must match capitalization exactly.'

    # Fuzzy check: up to 1 match, at least 60% similarity.
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)
    if matches:
        return f'Did you mean "{matches[0]}"?'

    return None
