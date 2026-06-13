"""
Error collection and reporting for the Atena transpiler.

This is the single source of truth for the error format:
  Error on line {N}: {plain English message}
    → {offending source line}

ErrorCollector is injected into each pipeline phase and accumulates
errors across the entire run. The pipeline gates codegen on .is_empty().
"""

from __future__ import annotations

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


ATENA_KEYWORDS: list[str] = []  # TODO: populated in Plan 04


def suggest(name: str, candidates: list[str]) -> str | None:
    """Return the single closest candidate name, or None if no close match.

    TODO: implemented in Plan 04
    """
    ...
