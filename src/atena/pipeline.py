"""
Top-level pipeline: runs Lexer → Parser → Analyzer → Generator in sequence.

The real transpile() implementation and four-phase wiring belong to Phase 5.
Phase 0 provides only this importable stub so later plans can reference the
contract without import errors.
"""

from __future__ import annotations


def transpile(source: str, filename: str) -> str | None:
    """Transpile Atena source to a Python 3 source string.

    Returns the generated Python string on success, or None if errors
    were collected (the ErrorCollector is populated with plain-English
    error messages).

    Phase 5 will replace this body with the real four-phase pipeline.
    """
    raise NotImplementedError("Pipeline not built yet — Phase 5")
