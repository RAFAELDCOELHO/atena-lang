"""
Error collection and reporting for the Atena transpiler.

This is the single source of truth for the error format:
  Error on line {N}: {plain English message}
    → {offending source line}

ErrorCollector is injected into each pipeline phase and accumulates
errors across the entire run. The pipeline gates codegen on .is_empty().

TODO: implemented in Plan 02
"""

from __future__ import annotations


class ErrorCollector:
    """Accumulates plain-English errors across all transpiler phases."""

    def add(self, line: int, message: str, source_line: str) -> None:
        ...

    def is_empty(self) -> bool:
        ...

    def report(self) -> str:
        ...


def suggest(name: str, candidates: list[str]) -> str | None:
    """Return the single closest candidate name, or None if no close match.

    TODO: implemented in Plan 02
    """
    ...
