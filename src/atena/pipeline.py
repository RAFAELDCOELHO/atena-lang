"""
Top-level pipeline: runs Lexer → Parser → Analyzer → Generator in sequence.

The real transpile() implementation and four-phase wiring belong to Phase 5.
Phase 0 provides only this importable stub so later plans can reference the
contract without import errors.

# Phase 5: wired in pipeline integration phase
"""

from __future__ import annotations


def transpile(source: str, filename: str) -> str | None:
    """Transpile Atena source to a Python 3 source string.

    Returns the generated Python string on success, or None if errors
    were collected (the ErrorCollector is populated with plain-English
    error messages).

    # Phase 5: wired in pipeline integration phase
    """
    ...
