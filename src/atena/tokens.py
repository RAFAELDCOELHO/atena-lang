"""
Token types and Token dataclass for the Atena transpiler.

Pure data module — no sibling-module imports. Every phase and test can
import this freely without creating circular dependencies.

TODO: TokenType enum and full token classification implemented in Plan 03
"""

from __future__ import annotations

from dataclasses import dataclass


class TokenType:
    """Stub — will become an Enum in Plan 03."""

    pass


@dataclass
class Token:
    """A single lexical token produced by the Atena lexer.

    Fields
    ------
    type        : Token classification (keyword, identifier, literal, etc.)
    value       : The raw text of the token as it appeared in the source.
    line        : 1-based line number in the source file.
    col         : 1-based column number of the token's first character.
    source_line : The full text of the line the token appears on
                  (used verbatim in error messages).

    TODO: implemented in Plan 03
    """

    type: object
    value: str
    line: int
    col: int
    source_line: str
