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

# Comparison operators. Atena does not support Python-style comparison
# chaining (1 < 2 < 3): all comparisons share bp=3 and chain left-
# associatively, so the AST would emit (1 < 2) < 3 → True < 3, which is NOT
# what a learner intends and NOT what the equivalent Python source means.
# Rather than silently mis-evaluate, the parser rejects a comparison whose
# left operand is itself a comparison (WR-05).
_COMPARISON_OPS: frozenset[str] = frozenset({"==", "!=", "<", ">", "<=", ">="})


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

    def _skip_orphaned_block(self) -> None:
        """Consume a balanced INDENT … DEDENT block left over from an errored header.

        When an erroneous statement header (e.g. a stray 'else') is followed by an
        indented block, synchronize lands the cursor on the orphaned INDENT. There
        is no statement to parse there — reporting on it would emit a meaningless
        'I didn't expect "" here' (INDENT's value is the empty string). Instead we
        swallow the whole block silently so a single mistake yields a single error
        (WR-02).

        Progress invariant: the opening INDENT is always consumed first, so this
        always advances >= 1 token. Nested INDENT/DEDENT pairs are tracked by depth.
        A missing DEDENT (truly malformed input / EOF inside the block) terminates
        the loop at EOF rather than hanging.
        """
        if not self._check(TokenType.INDENT):
            return
        self._advance()            # consume the opening INDENT (guarantees progress)
        depth = 1
        while depth > 0 and not self._at_end():
            tok = self._current()
            if tok.type == TokenType.INDENT:
                depth += 1
            elif tok.type == TokenType.DEDENT:
                depth -= 1
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
    # Expression parser (Pratt precedence-climbing)
    # -----------------------------------------------------------------------

    def _parse_expression(self, min_bp: int = 0) -> Node:
        """Pratt expression parser entry point.

        Implements precedence-climbing using _BINARY_BP. Calls _parse_unary()
        to get the left operand, then loops consuming binary operators whose
        binding power exceeds min_bp.

        Left-associativity: right operand is parsed with min_bp=bp (not bp-1).
        This means an operator of the same precedence on the right is NOT
        absorbed (bp > min_bp is false when equal), giving left-association.
        Verified: "10 - 3 - 2" → second "-" has bp=4, right call runs with
        min_bp=4, 4 > 4 is false, so it cannot absorb the second "-".
        (PITFALLS.md §8)
        """
        left = self._parse_unary()
        while True:
            op_tok = self._current()
            # Determine the operator string from the current token.
            # OPERATOR/COMPARISON tokens carry the value directly ("+" "==" etc.).
            # KEYWORD tokens for "and"/"or" also use their value.
            op_str = op_tok.value
            bp = _BINARY_BP.get(op_str, 0)
            if bp <= min_bp:
                break
            self._advance()                        # consume the operator token
            # Reject chained comparisons (1 < 2 < 3, a == b == c): if we are about
            # to build a comparison and the left operand is already a comparison,
            # the learner's intent (and the meaning of the equivalent Python) is
            # silently lost. Emit a plain-English hint instead (WR-05).
            if op_str in _COMPARISON_OPS and isinstance(left, BinOp) and left.op in _COMPARISON_OPS:
                raise _ParseError(
                    op_tok.line,
                    'Compare two things at a time — write "1 < 2 and 2 < 3" instead of "1 < 2 < 3".',
                    op_tok.source_line,
                )
            right = self._parse_expression(bp)     # left-assoc: same bp for right
            left = BinOp(
                op=op_str,
                left=left,
                right=right,
                line=op_tok.line,
                source_line=op_tok.source_line,
            )
        return left

    def _parse_unary(self) -> Node:
        """Parse unary 'not' and unary '-', then fall through to postfix loop.

        'not' is right-recursive: 'not not x' is valid.
        Unary '-' binds tighter than any binary op — only applies to the
        immediate primary+postfix (PITFALLS.md §7).
        """
        tok = self._current()
        if tok.type == TokenType.KEYWORD and tok.value == "not":
            self._advance()
            operand = self._parse_unary()   # right-recursive
            return UnaryOp(
                op="not",
                operand=operand,
                line=tok.line,
                source_line=tok.source_line,
            )
        if tok.type == TokenType.OPERATOR and tok.value == "-":
            self._advance()
            # Unary minus binds tightest — only to immediate primary+postfix,
            # never absorbs a binary op on the right.
            operand = self._parse_postfix(self._parse_primary())
            return UnaryOp(
                op="-",
                operand=operand,
                line=tok.line,
                source_line=tok.source_line,
            )
        return self._parse_postfix(self._parse_primary())

    def _parse_postfix(self, node: Node) -> Node:
        """Tight postfix loop for [] . () — left-associative, highest binding (PITFALLS.md §9).

        Loops consuming [] (subscript), . (field), and () (call) until none match.
        IndexAccess is always constructed with index_converted=False — the
        semantic analyzer sets it to True during the 1→0 rewrite (Pitfall 8/T-02-08).
        """
        while True:
            tok = self._current()
            if tok.type == TokenType.LBRACKET:
                self._advance()   # consume '['
                # If we immediately hit end-of-line or EOF, the bracket was never closed.
                if self._check(TokenType.NEWLINE, TokenType.EOF):
                    raise _ParseError(
                        tok.line,
                        'I reached the end of the line still waiting for a "]".',
                        tok.source_line,
                    )
                index = self._parse_expression()
                self._expect(TokenType.RBRACKET, 'I reached the end of the line still waiting for a "]".')
                node = IndexAccess(
                    target=node,
                    index=index,
                    index_converted=False,
                    line=tok.line,
                    source_line=tok.source_line,
                )
            elif tok.type == TokenType.DOT:
                self._advance()   # consume '.'
                name_tok = self._expect(TokenType.IDENTIFIER, 'Expected a field name after ".".')
                node = DotAccess(
                    target=node,
                    name=name_tok.value,
                    line=tok.line,
                    source_line=tok.source_line,
                )
            elif tok.type == TokenType.LPAREN:
                self._advance()   # consume '('
                args: list[Node] = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._parse_expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._parse_expression())
                self._expect(TokenType.RPAREN, 'I reached the end of the line still waiting for a ")".')
                if isinstance(node, Identifier):
                    node = FunctionCall(
                        name=node.name,
                        args=args,
                        line=tok.line,
                        source_line=tok.source_line,
                    )
                else:
                    raise _ParseError(tok.line, 'Only named functions can be called.', tok.source_line)
            else:
                break
        return node

    def _parse_primary(self) -> Node:
        """Parse a primary atom: literal, identifier, grouped expression, or list/dict literal.

        Dispatches on the current token type. Raises _ParseError for unexpected tokens.
        String token values are already bare content (lexer strips outer quotes).
        """
        tok = self._current()

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLiteral(value=int(tok.value), line=tok.line, source_line=tok.source_line)

        if tok.type == TokenType.STRING:
            self._advance()
            # The lexer strips the outer double-quotes; tok.value is the bare content.
            return StringLiteral(value=tok.value, line=tok.line, source_line=tok.source_line)

        if tok.type == TokenType.KEYWORD and tok.value == "true":
            self._advance()
            return BoolLiteral(value=True, line=tok.line, source_line=tok.source_line)

        if tok.type == TokenType.KEYWORD and tok.value == "false":
            self._advance()
            return BoolLiteral(value=False, line=tok.line, source_line=tok.source_line)

        if tok.type == TokenType.KEYWORD and tok.value == "length":
            # 'length' is a prefix keyword. It takes the full postfix chain of the
            # following operand so the natural reading holds: 'length items[0]' is
            # "the length of items[0]" (FunctionCall over IndexAccess), not the
            # silent mis-parse len(items)[0]. Likewise 'length student.grades' is
            # len(student.grades), not len(student).grades (WR-03).
            # Maps to FunctionCall(name="length", args=[operand]) for codegen → len().
            self._advance()
            operand = self._parse_postfix(self._parse_primary())
            return FunctionCall(
                name="length",
                args=[operand],
                line=tok.line,
                source_line=tok.source_line,
            )

        # "ask" in expression position is a D-02 misuse — redirect with a friendly message.
        # Valid use is only as assignment RHS: 'name = ask "prompt"'.
        if tok.type == TokenType.KEYWORD and tok.value == "ask":
            raise _ParseError(
                tok.line,
                'ask needs to save its answer into a name — try: answer = ask "What is your name?".',
                tok.source_line,
            )

        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(name=tok.value, line=tok.line, source_line=tok.source_line)

        if tok.type == TokenType.LPAREN:
            self._advance()   # consume '('
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, 'I reached the end of the line still waiting for a ")".')
            return expr

        if tok.type == TokenType.LBRACKET:
            return self._parse_list_literal()

        if tok.type == TokenType.LBRACE:
            return self._parse_dict_literal()

        raise _ParseError(tok.line, f'I didn\'t expect "{tok.value}" here.', tok.source_line)

    def _parse_list_literal(self) -> ListLiteral:
        """Parse a list literal: [elem, elem, …]."""
        tok = self._expect(TokenType.LBRACKET, 'Expected "[" to start a list.')
        elements: list[Node] = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._parse_expression())
            while self._match(TokenType.COMMA):
                elements.append(self._parse_expression())
        self._expect(TokenType.RBRACKET, 'I reached the end of the line still waiting for a "]".')
        return ListLiteral(elements=elements, line=tok.line, source_line=tok.source_line)

    def _parse_dict_literal(self) -> DictLiteral:
        """Parse a dict literal: {key = value, …}.

        Atena's dict literal uses = (ASSIGN) as the key-value separator.
        Keys are bare identifiers; values are arbitrary expressions.
        """
        tok = self._expect(TokenType.LBRACE, 'Expected "{" to start a dictionary.')
        pairs: list[tuple[str, Node]] = []
        if not self._check(TokenType.RBRACE):
            key_tok = self._expect(TokenType.IDENTIFIER, 'Expected a key name in the dictionary.')
            self._expect(TokenType.ASSIGN, 'Expected "=" after the key name in the dictionary.')
            val = self._parse_expression()
            pairs.append((key_tok.value, val))
            while self._match(TokenType.COMMA):
                key_tok = self._expect(TokenType.IDENTIFIER, 'Expected a key name in the dictionary.')
                self._expect(TokenType.ASSIGN, 'Expected "=" after the key name.')
                val = self._parse_expression()
                pairs.append((key_tok.value, val))
        self._expect(TokenType.RBRACE, 'I reached the end of the line still waiting for a "}".')
        return DictLiteral(pairs=pairs, line=tok.line, source_line=tok.source_line)

    # -----------------------------------------------------------------------
    # Statement-level helpers
    # -----------------------------------------------------------------------

    def _end_statement(self) -> None:
        """Require a statement terminator: a NEWLINE, or a block/stream boundary.

        Consumes a trailing NEWLINE if present. A DEDENT or EOF is also a valid
        terminator: block-final and file-final statements may have their NEWLINE
        already consumed by the block parser, or absent at end of input.

        Any *other* leftover token means the line did not actually end — e.g.
        'x = a b' parses 'a' as a complete value but leaves 'b' dangling. Rather
        than silently accept the half-parsed statement (which would leak a wrong
        AST node into program.statements and then emit a confusing secondary
        error on the leftover token), raise a _ParseError here so synchronize
        fires and no partial node is returned (WR-01).
        """
        if self._check(TokenType.NEWLINE):
            self._advance()
            return
        if self._check(TokenType.DEDENT, TokenType.EOF):
            return  # block-final / file-final: terminator already consumed/absent
        tok = self._current()
        raise _ParseError(
            tok.line,
            f'I didn\'t expect "{tok.value}" after the end of this line.',
            tok.source_line,
        )

    # -----------------------------------------------------------------------
    # Statement parser methods (Plan 03)
    # -----------------------------------------------------------------------

    def _parse_show(self) -> Show:
        """Parse: show <expression>"""
        kw = self._advance()   # consume "show"
        value = self._parse_expression()
        # 'ask' in expression position is redirected by _parse_primary (see :357).
        self._end_statement()
        return Show(value=value, line=kw.line, source_line=kw.source_line)

    def _parse_ask(self, target: str, line: int, source_line: str) -> Ask:
        """Parse the ask portion of 'name = ask "prompt"'.

        Called from _parse_assignment when 'ask' is seen as the RHS.
        """
        kw = self._advance()   # consume "ask"
        if not self._check(TokenType.STRING):
            raise _ParseError(
                kw.line,
                'ask needs to save its answer into a name — try: answer = ask "What is your name?".',
                kw.source_line,
            )
        prompt_tok = self._advance()   # consume STRING token
        self._end_statement()
        return Ask(prompt=prompt_tok.value, target=target, line=line, source_line=source_line)

    def _parse_assignment(self) -> Assign | Ask:
        """Parse: name = <expression>  OR  name = ask "prompt"

        Called when current is IDENTIFIER and peek is ASSIGN.
        """
        name_tok = self._advance()   # consume IDENTIFIER
        self._advance()              # consume ASSIGN '='
        # Check if RHS is "ask" — this is the dedicated Ask statement form (D-01/D-02).
        if self._check(TokenType.KEYWORD) and self._current().value == "ask":
            return self._parse_ask(
                target=name_tok.value,
                line=name_tok.line,
                source_line=name_tok.source_line,
            )
        value = self._parse_expression()
        self._end_statement()
        return Assign(
            name=name_tok.value,
            value=value,
            line=name_tok.line,
            source_line=name_tok.source_line,
        )

    def _parse_if(self) -> If:
        """Parse: if <condition> NEWLINE INDENT <body> DEDENT [else NEWLINE INDENT <body> DEDENT]"""
        kw = self._advance()   # consume "if"
        condition = self._parse_expression()
        self._end_statement()
        then_body = self._parse_block()
        else_body: list[Node] = []
        # Optional else clause: only if current token is the "else" keyword.
        if self._check(TokenType.KEYWORD) and self._current().value == "else":
            self._advance()   # consume "else"
            self._end_statement()
            else_body = self._parse_block()
        return If(
            condition=condition,
            then_body=then_body,
            else_body=else_body,
            line=kw.line,
            source_line=kw.source_line,
        )

    def _parse_while(self) -> While:
        """Parse: while <condition> NEWLINE INDENT <body> DEDENT"""
        kw = self._advance()   # consume "while"
        condition = self._parse_expression()
        self._end_statement()
        body = self._parse_block()
        return While(condition=condition, body=body, line=kw.line, source_line=kw.source_line)

    def _parse_repeat(self) -> Repeat:
        """Parse: repeat <count> times NEWLINE INDENT <body> DEDENT"""
        kw = self._advance()   # consume "repeat"
        count = self._parse_expression()
        # Expect the keyword "times" immediately after the count expression.
        if not (self._check(TokenType.KEYWORD) and self._current().value == "times"):
            tok = self._current()
            raise _ParseError(
                tok.line,
                '"repeat" needs the word "times" — try: repeat 5 times.',
                tok.source_line,
            )
        self._advance()   # consume "times"
        self._end_statement()
        body = self._parse_block()
        return Repeat(count=count, body=body, line=kw.line, source_line=kw.source_line)

    def _parse_function_def(self) -> FunctionDef:
        """Parse: function name(params) NEWLINE INDENT <body> DEDENT"""
        kw = self._advance()   # consume "function"
        name_tok = self._expect(TokenType.IDENTIFIER, 'Expected a function name after "function".')
        self._expect(TokenType.LPAREN, f'Expected "(" after the function name "{name_tok.value}".')
        params: list[str] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENTIFIER, 'Expected a parameter name.').value)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENTIFIER, 'Expected a parameter name after ",".').value)
        self._expect(TokenType.RPAREN, 'I reached the end of the line still waiting for a ")".')
        self._end_statement()
        # Track function nesting depth for top-level return check (D-04 item 3).
        # fn_depth is decremented in finally so it stays consistent even if body
        # parsing raises _ParseError (T-02-09).
        self._fn_depth += 1
        try:
            body = self._parse_block()
        finally:
            self._fn_depth -= 1
        return FunctionDef(
            name=name_tok.value,
            params=params,
            body=body,
            line=kw.line,
            source_line=kw.source_line,
        )

    def _parse_return(self) -> Return:
        """Parse: return <expression>"""
        kw = self._advance()   # consume "return"
        if self._fn_depth == 0:
            raise _ParseError(kw.line, '"return" only works inside a function.', kw.source_line)
        value = self._parse_expression()
        self._end_statement()
        return Return(value=value, line=kw.line, source_line=kw.source_line)

    def _parse_list_add(self) -> ListAdd:
        """Parse: add <value> to <target>"""
        kw = self._advance()   # consume "add"
        value = self._parse_expression()
        # Expect keyword "to"
        tok = self._current()
        if not (tok.type == TokenType.KEYWORD and tok.value == "to"):
            raise _ParseError(
                tok.line,
                'Expected "to" after the value in "add … to …".',
                tok.source_line,
            )
        self._advance()   # consume "to"
        target_tok = self._expect(TokenType.IDENTIFIER, 'Expected a list name after "to".')
        self._end_statement()
        return ListAdd(target=target_tok.value, value=value, line=kw.line, source_line=kw.source_line)

    def _parse_list_remove(self) -> ListRemove:
        """Parse: remove <value> from <target>"""
        kw = self._advance()   # consume "remove"
        value = self._parse_expression()
        # Expect keyword "from"
        tok = self._current()
        if not (tok.type == TokenType.KEYWORD and tok.value == "from"):
            raise _ParseError(
                tok.line,
                'Expected "from" after the value in "remove … from …".',
                tok.source_line,
            )
        self._advance()   # consume "from"
        target_tok = self._expect(TokenType.IDENTIFIER, 'Expected a list name after "from".')
        self._end_statement()
        return ListRemove(target=target_tok.value, value=value, line=kw.line, source_line=kw.source_line)

    def _parse_expression_statement(self) -> Node:
        """Parse a bare expression at statement position.

        Only function calls are valid bare expression statements. A bare
        comparison (e.g. 'x == 5' intending assignment) is the = vs ==
        Python-ism — caught here and redirected (D-04 item 2).
        """
        expr = self._parse_expression()
        # Check for the == used as assignment slip (D-04 item 2).
        if isinstance(expr, BinOp) and expr.op == "==":
            raise _ParseError(
                expr.line,
                'Did you mean "x = 5"? Use one "=" to save a value, and "==" only to compare two things.',
                expr.source_line,
            )
        # Only FunctionCall is a valid bare expression statement.
        if not isinstance(expr, FunctionCall):
            raise _ParseError(
                expr.line,
                f'I didn\'t expect "{self._tokens[self._pos - 1].value if self._pos > 0 else "?"}" here.',
                expr.source_line,
            )
        self._end_statement()
        return expr

    # -----------------------------------------------------------------------
    # Statement dispatcher (full — Plan 03)
    # -----------------------------------------------------------------------

    def _dispatch_statement(self) -> Node | None:
        """Full statement dispatcher.

        Dispatches on the current token to the appropriate parser method.
        Handles:
        - NEWLINE: skip blank lines.
        - EOF: terminate cleanly.
        - KEYWORD "show": _parse_show()
        - KEYWORD "if": _parse_if()
        - KEYWORD "while": _parse_while()
        - KEYWORD "repeat": _parse_repeat()
        - KEYWORD "function": _parse_function_def()
        - KEYWORD "return": _parse_return()
        - KEYWORD "add": _parse_list_add()
        - KEYWORD "remove": _parse_list_remove()
        - KEYWORD "ask" (bare): D-02 redirect error.
        - KEYWORD "else": unexpected else (not inside if context) → generic error.
        - IDENTIFIER + ASSIGN: _parse_assignment()
        - IDENTIFIER + other: _parse_expression_statement()
        - Python-ism identifiers (def, elif, for, class, import): redirect errors (D-04).
        - Anything else: generic _ParseError.
        """
        # Skip blank lines (NEWLINE without content)
        if self._check(TokenType.NEWLINE):
            self._advance()
            return None
        # At EOF — terminate cleanly
        if self._at_end():
            return None
        # An orphaned INDENT at statement position means the previous header
        # errored and synchronize left us on its now-headerless block. Skip the
        # whole block silently rather than emitting a meaningless `""` diagnostic
        # on the INDENT token — one bad header should yield one error (WR-02).
        if self._check(TokenType.INDENT):
            self._skip_orphaned_block()
            return None

        tok = self._current()

        # ---- KEYWORD-led statements ----
        if tok.type == TokenType.KEYWORD:
            kw_value = tok.value
            if kw_value == "show":
                return self._parse_show()
            if kw_value == "if":
                return self._parse_if()
            if kw_value == "while":
                return self._parse_while()
            if kw_value == "repeat":
                return self._parse_repeat()
            if kw_value == "function":
                return self._parse_function_def()
            if kw_value == "return":
                return self._parse_return()
            if kw_value == "add":
                return self._parse_list_add()
            if kw_value == "remove":
                return self._parse_list_remove()
            # Bare "ask" at statement level — D-02 misuse redirect.
            if kw_value == "ask":
                raise _ParseError(
                    tok.line,
                    'ask needs to save its answer into a name — try: answer = ask "What is your name?".',
                    tok.source_line,
                )
            # Python-ism redirect: "from" at statement position → "from os import sys"
            # style. "from" lexes as a KEYWORD (used in "remove … from …"), so it
            # reaches here when written at statement position without "remove" before it.
            if kw_value == "from":
                raise _ParseError(
                    tok.line,
                    'An Atena program is a single file — there\'s nothing to import.',
                    tok.source_line,
                )
            # Generic fallback for other keywords at statement position.
            raise _ParseError(
                tok.line,
                f'I didn\'t expect "{tok.value}" here.',
                tok.source_line,
            )

        # ---- IDENTIFIER-led statements ----
        if tok.type == TokenType.IDENTIFIER:
            # Python-ism redirect: "def" → suggest "function" (D-04 item 1)
            if tok.value == "def":
                raise _ParseError(
                    tok.line,
                    'Atena uses "function", not "def" — try: function greet(name).',
                    tok.source_line,
                )
            # Python-ism redirect: "elif" → nested if/else (D-04 item 1)
            if tok.value == "elif":
                raise _ParseError(
                    tok.line,
                    'Atena doesn\'t have elif — use a nested if/else inside the else.',
                    tok.source_line,
                )
            # Python-ism redirect: "for" → repeat/while (D-04 item 1)
            if tok.value == "for":
                raise _ParseError(
                    tok.line,
                    'Atena loops with "repeat N times" or "while" — there\'s no "for" loop.',
                    tok.source_line,
                )
            # Python-ism redirect: "class" → Atena has no classes (D-04 item 1)
            if tok.value == "class":
                raise _ParseError(
                    tok.line,
                    'Atena doesn\'t have classes — it\'s for step-by-step logic, not objects.',
                    tok.source_line,
                )
            # Python-ism redirect: "import" → single-file program (D-04 item 1)
            if tok.value == "import":
                raise _ParseError(
                    tok.line,
                    'An Atena program is a single file — there\'s nothing to import.',
                    tok.source_line,
                )
            # Assignment: IDENTIFIER followed by ASSIGN → assignment statement.
            if self._peek().type == TokenType.ASSIGN:
                return self._parse_assignment()
            # Otherwise: bare expression statement (e.g. a bare function call).
            return self._parse_expression_statement()

        # ---- Anything else is unexpected at statement position ----
        raise _ParseError(
            tok.line,
            f'I didn\'t expect "{tok.value}" here.',
            tok.source_line,
        )

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
