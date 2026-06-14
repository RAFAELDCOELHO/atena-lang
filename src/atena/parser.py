"""
Parser for the Atena transpiler.

Converts a fully-materialised list[Token] (contract A) into a Program AST
(contract B). Implements recursive descent for statements and Pratt
precedence-climbing for expressions. Syntax errors are collected through
the injected ErrorCollector and recovered via synchronization on NEWLINE/
DEDENT boundaries — the parser never raises to the user and never emits a
Python traceback.
"""

from __future__ import annotations

from atena.tokens import TokenType, Token
from atena.errors import ErrorCollector
from atena.ast_nodes import (
    Program, Assign, Show, Ask, If, While, Repeat,
    FunctionDef, Return, FunctionCall, BinOp, UnaryOp,
    ListLiteral, DictLiteral, IndexAccess, DotAccess,
    ListAdd, ListRemove, Identifier, NumberLiteral,
    StringLiteral, BoolLiteral,
    Node,
)

# ---------------------------------------------------------------------------
# Binding-power table — single source of truth for Pratt precedence.
# Higher number = tighter binding. All operators are left-associative
# (right operand is parsed with min_bp = bp, not bp-1).
# "not" is unary — handled in _parse_unary, not in this table.
# Postfix [] . () are handled as a tight loop in _parse_postfix, not here.
# ---------------------------------------------------------------------------

_BINARY_BP: dict[str, int] = {
    "or":  1,
    "and": 2,
    "==":  3,
    "!=":  3,
    "<":   3,
    ">":   3,
    "<=":  3,
    ">=":  3,
    "+":   4,
    "-":   4,
    "*":   5,
    "/":   5,
}


# ---------------------------------------------------------------------------
# Internal control-flow exception
# ---------------------------------------------------------------------------


class _ParseError(Exception):
    """Internal control-flow exception — caught only at statement boundaries.

    Never surfaced to the user. The parser catches this inside _parse_statement()
    and calls self._errors.add() before synchronizing.
    """

    def __init__(self, line: int, message: str, source_line: str) -> None:
        self.line = line
        self.message = message
        self.source_line = source_line


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class Parser:
    """Parses a list[Token] into a Program AST.

    Implements:
    - Recursive descent for statements (if, while, repeat, function, show,
      ask, return, add/remove, assignment, bare function call).
    - Pratt / precedence-climbing for expressions using _BINARY_BP.
    - INDENT/DEDENT block parsing (the lexer pre-balanced these tokens).
    - Error recovery via synchronization on NEWLINE/DEDENT boundaries.
    - Python-ism redirects collected as plain-English errors (D-04).
    - Progress invariant: every recovery path consumes >= 1 token (PITFALLS §13).
    """

    def __init__(self, tokens: list[Token], errors: ErrorCollector) -> None:
        self._tokens = tokens           # fully-materialised list from the Lexer
        self._errors = errors           # injected — never instantiate internally
        self._pos = 0                   # index into self._tokens
        self._fn_depth = 0              # tracks function nesting for top-level return check (D-04 item 3)

    # -----------------------------------------------------------------------
    # Cursor helpers
    # -----------------------------------------------------------------------

    def _current(self) -> Token:
        """Return the token at the current position (never None — returns EOF sentinel)."""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]   # EOF token is always the last element

    def _peek(self) -> Token:
        """Return the token one position ahead (returns EOF sentinel if past end)."""
        pos = self._pos + 1
        if pos < len(self._tokens):
            return self._tokens[pos]
        return self._tokens[-1]

    def _advance(self) -> Token:
        """Consume and return the current token; advance the position (but not past EOF)."""
        tok = self._current()
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        """Return True if the current token's type is one of the given types."""
        return self._current().type in types

    def _match(self, *types: TokenType) -> Token | None:
        """Consume and return the current token if its type matches; else return None."""
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, tok_type: TokenType, message: str) -> Token:
        """Consume a token of the given type; raise _ParseError if not found."""
        if self._check(tok_type):
            return self._advance()
        tok = self._current()
        raise _ParseError(tok.line, message, tok.source_line)

    def _at_end(self) -> bool:
        """Return True when at the EOF token."""
        return self._current().type == TokenType.EOF

    # -----------------------------------------------------------------------
    # Block parsing
    # -----------------------------------------------------------------------

    def _parse_block(self) -> list[Node]:
        """Parse an INDENT … DEDENT block; return the list of body statements.

        Expects the current token to be INDENT. Loops parsing statements until
        DEDENT or EOF, then expects DEDENT. The lexer guarantees balanced
        INDENT/DEDENT tokens, so a missing DEDENT only occurs on truly malformed
        input (e.g. EOF inside a block).
        """
        self._expect(TokenType.INDENT, "Expected an indented block here.")
        body: list[Node] = []
        while not self._check(TokenType.DEDENT) and not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                body.append(stmt)
        self._expect(TokenType.DEDENT, "Expected the end of the indented block.")
        return body

    # -----------------------------------------------------------------------
    # Error recovery
    # -----------------------------------------------------------------------

    def _synchronize(self) -> None:
        """Discard tokens until a safe statement-restart point.

        Sync tokens: NEWLINE and DEDENT — the statement/block boundaries.
        Progress invariant: always consumes >= 1 token (PITFALLS §13).
        """
        while not self._at_end():
            if self._current().type in (TokenType.NEWLINE, TokenType.DEDENT):
                self._advance()   # consume the sync token itself
                return
            self._advance()

    def _parse_statement(self) -> Node | None:
        """Parse one statement; catch _ParseError and synchronize on error.

        Loop guard: track position before dispatch; force-advance if position
        did not change after a full iteration (progress invariant backstop,
        PITFALLS §13).
        """
        pos_before = self._pos
        try:
            return self._dispatch_statement()
        except _ParseError as e:
            self._errors.add(e.line, e.message, e.source_line)
            self._synchronize()
            return None
        finally:
            # Backstop: if position did not advance at all, force-advance one token.
            if self._pos == pos_before:
                self._advance()

    # -----------------------------------------------------------------------
    # Statement dispatcher (stub — Plan 03 fills in the full dispatch)
    # -----------------------------------------------------------------------

    def _dispatch_statement(self) -> Node | None:
        """STUB: consume NEWLINE tokens and return None; return None at EOF.

        Plan 03 replaces this with the full statement dispatch. For now the
        only purpose is to let parse() terminate cleanly on empty input so
        test_Px_empty_program passes in the RED phase.
        """
        # Skip blank lines (NEWLINE without content)
        if self._check(TokenType.NEWLINE):
            self._advance()
            return None
        # At EOF — terminate cleanly
        if self._at_end():
            return None
        # Any other token: consume it (skeleton progress) and return None.
        # Plan 03 will replace this with real dispatch logic.
        self._advance()
        return None

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    def parse(self) -> Program:
        """Parse all tokens and return the Program root node.

        Returns a (potentially partial) Program even when errors were collected.
        The driver gates later phases on errors.is_empty(); it is the driver's
        responsibility to check, not the parser's.
        """
        program = Program(line=1, source_line="")
        while not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                program.statements.append(stmt)
        return program
