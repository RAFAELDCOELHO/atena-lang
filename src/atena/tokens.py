"""
Token types and Token dataclass for the Atena transpiler.

Pure data module — no sibling-module imports. Every phase and test can
import this freely without creating circular dependencies.

Exports: TokenType, Token, KEYWORDS
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class TokenType(enum.Enum):
    """All lexical token types produced by the Atena lexer.

    19 members — covers every token category in REQUIREMENTS.md LEX-01.

    KEYWORD     : reserved Atena keyword (show, ask, if, else, while, …)
    IDENTIFIER  : user-defined name (variable, function, parameter)
    STRING      : double-quoted string literal  "hello"
    NUMBER      : integer literal               42
    OPERATOR    : arithmetic operator           + - * /
    COMPARISON  : comparison operator           == != < > <= >=
    ASSIGN      : assignment symbol             =
    LPAREN      : (
    RPAREN      : )
    LBRACKET    : [
    RBRACKET    : ]
    LBRACE      : {
    RBRACE      : }
    COMMA       : ,
    DOT         : .
    NEWLINE     : end-of-logical-line
    INDENT      : block-open (indentation increase)
    DEDENT      : block-close (indentation decrease)
    EOF         : end of token stream
    """

    STRING = "STRING"
    NUMBER = "NUMBER"
    IDENTIFIER = "IDENTIFIER"
    KEYWORD = "KEYWORD"
    OPERATOR = "OPERATOR"
    COMPARISON = "COMPARISON"
    ASSIGN = "ASSIGN"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COMMA = "COMMA"
    DOT = "DOT"
    NEWLINE = "NEWLINE"
    INDENT = "INDENT"
    DEDENT = "DEDENT"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    """A single lexical token produced by the Atena lexer.

    Frozen — tokens are immutable after creation (mutation raises
    FrozenInstanceError).

    Fields
    ------
    type        : Token classification (see TokenType).
    value       : The raw text of the token as it appeared in the source.
    line        : 1-based line number in the source file.
    col         : 0-based column offset of the token's first character.
    source_line : The full text of the line the token appears on.
                  Stored verbatim so any downstream phase can produce
                  "Error on line {N}: … → {source_line}" without re-reading
                  the file (DIAG-01).
    """

    type: TokenType
    value: str
    line: int
    col: int
    source_line: str


# KEYWORDS maps every Atena reserved word (as it appears in source) to
# TokenType.KEYWORD.  When the lexer scans an identifier-shaped token it
# looks the text up here; a hit means it is a keyword, a miss means it is
# a user-defined IDENTIFIER.
#
# Full set from REQUIREMENTS.md LEX-06 (18 keywords):
#   show ask if else while repeat times and or not
#   function return add to remove from length true false
KEYWORDS: dict[str, TokenType] = {
    "show": TokenType.KEYWORD,
    "ask": TokenType.KEYWORD,
    "if": TokenType.KEYWORD,
    "else": TokenType.KEYWORD,
    "while": TokenType.KEYWORD,
    "repeat": TokenType.KEYWORD,
    "times": TokenType.KEYWORD,
    "and": TokenType.KEYWORD,
    "or": TokenType.KEYWORD,
    "not": TokenType.KEYWORD,
    "function": TokenType.KEYWORD,
    "return": TokenType.KEYWORD,
    "add": TokenType.KEYWORD,
    "to": TokenType.KEYWORD,
    "remove": TokenType.KEYWORD,
    "from": TokenType.KEYWORD,
    "length": TokenType.KEYWORD,
    "true": TokenType.KEYWORD,
    "false": TokenType.KEYWORD,
}
