"""
TDD tests for the Atena Lexer — Phase 1 / Wave 0 RED phase.

Layer 1: golden token snapshots — assert exact token types/values, no errors.
Layer 2: error-path tests — assert key phrase in report(), error line number, no crash.

All tests are written BEFORE the implementation (RED phase per CLAUDE.md TDD requirement).
Every test in this file must FAIL after this plan completes — that is the definition of
done for a TDD RED phase.
"""

from __future__ import annotations

import pytest

from atena.tokens import TokenType, Token, KEYWORDS
from atena.errors import ErrorCollector
from atena.lexer import Lexer


def _lex(source: str) -> tuple[list[Token], ErrorCollector]:
    """Helper: lex source and return (tokens, errors) for inspection."""
    ec = ErrorCollector()
    tokens = Lexer(source, ec).tokenize()
    return tokens, ec


# ---------------------------------------------------------------------------
# Layer 1 — Golden snapshot tests (LEX-01 through LEX-07)
# ---------------------------------------------------------------------------


def test_L1_all_token_types():
    """All 17 non-structural token types appear in a hand-crafted source snippet."""
    # Exercises: STRING, NUMBER, IDENTIFIER, KEYWORD, OPERATOR, COMPARISON,
    # ASSIGN, LPAREN, RPAREN, LBRACKET, RBRACKET, LBRACE, RBRACE, COMMA, DOT
    # NEWLINE/INDENT/DEDENT/EOF are structural and covered by other tests.
    source = (
        'show x\n'
        'y = 42\n'
        'z = "hello"\n'
        'a = x + y - z * y / a\n'
        'if x == y\n'
        '    b = (1)\n'
        '    c = [1, 2]\n'
        '    d = {"key": 1}\n'
        '    e = x.name\n'
    )
    tokens, ec = _lex(source)
    types_found = {t.type for t in tokens}
    assert TokenType.STRING in types_found
    assert TokenType.NUMBER in types_found
    assert TokenType.IDENTIFIER in types_found
    assert TokenType.KEYWORD in types_found
    assert TokenType.OPERATOR in types_found
    assert TokenType.COMPARISON in types_found
    assert TokenType.ASSIGN in types_found
    assert TokenType.LPAREN in types_found
    assert TokenType.RPAREN in types_found
    assert TokenType.LBRACKET in types_found
    assert TokenType.RBRACKET in types_found
    assert TokenType.LBRACE in types_found
    assert TokenType.RBRACE in types_found
    assert TokenType.COMMA in types_found
    assert TokenType.DOT in types_found
    assert ec.is_empty()


def test_L1_keyword_recognition():
    """'show' at the start of a line produces a KEYWORD token with value 'show'."""
    tokens, ec = _lex("show x\n")
    keywords = [t for t in tokens if t.type == TokenType.KEYWORD]
    assert len(keywords) >= 1
    assert keywords[0].value == "show"
    assert ec.is_empty()


def test_L1_identifier_vs_keyword():
    """'score' produces IDENTIFIER and '=' produces ASSIGN in 'score = 10'."""
    tokens, ec = _lex("score = 10\n")
    assert ec.is_empty()
    identifiers = [t for t in tokens if t.type == TokenType.IDENTIFIER]
    assert len(identifiers) == 1
    assert identifiers[0].value == "score"
    assigns = [t for t in tokens if t.type == TokenType.ASSIGN]
    assert len(assigns) == 1
    assert assigns[0].value == "="


def test_L2_indent_dedent_balanced():
    """A one-level block produces exactly one INDENT and one DEDENT, ending with EOF."""
    tokens, ec = _lex("if x\n    show y\n")
    assert ec.is_empty()
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    assert len(indents) == 1
    assert len(dedents) == 1
    assert tokens[-1].type == TokenType.EOF


def test_L2_eof_drain_no_trailing_newline():
    """File with no trailing newline still drains all open blocks and ends with EOF."""
    tokens, ec = _lex("if x\n    show y")
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    assert len(indents) == 1
    assert len(dedents) == 1
    assert tokens[-1].type == TokenType.EOF


def test_L2_eof_drain_mid_block():
    """Two open blocks at EOF drain to exactly two INDENT and two DEDENT tokens."""
    tokens, ec = _lex("if x\n    if y\n        show z")
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    assert len(indents) == 2
    assert len(dedents) == 2
    assert tokens[-1].type == TokenType.EOF


def test_L3_blank_line_no_tokens():
    """A blank line between two statements produces no INDENT or DEDENT tokens."""
    tokens, ec = _lex("show 1\n\nshow 2\n")
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    assert len(indents) == 0
    assert len(dedents) == 0
    assert ec.is_empty()


def test_L3_comment_only_no_tokens():
    """A comment-only line produces no INDENT, DEDENT, or spurious tokens."""
    tokens, ec = _lex("show 1\n# this is a comment\nshow 2\n")
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    assert len(indents) == 0
    assert len(dedents) == 0
    assert ec.is_empty()


def test_L3_deep_comment_no_indent_effect():
    """A deeply-indented comment inside a block does not add a second INDENT level."""
    source = "if x\n    show y\n        # deep comment\n    show z\n"
    tokens, ec = _lex(source)
    assert ec.is_empty()
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    assert len(indents) == 1
    assert len(dedents) == 1


def test_L5_assign_token():
    """'x = 10' produces exactly one ASSIGN token with value '='."""
    tokens, ec = _lex("x = 10\n")
    assert ec.is_empty()
    assigns = [t for t in tokens if t.type == TokenType.ASSIGN]
    assert len(assigns) == 1
    assert assigns[0].value == "="


def test_L5_eq_comparison_token():
    """'x == 10' produces exactly one COMPARISON token with value '=='."""
    tokens, ec = _lex("x == 10\n")
    assert ec.is_empty()
    comps = [t for t in tokens if t.type == TokenType.COMPARISON]
    assert len(comps) == 1
    assert comps[0].value == "=="


def test_L5_all_comparisons():
    """'!=', '<', '>', '<=', '>=' each appear exactly once as COMPARISON tokens."""
    source = "a != b\na < b\na > b\na <= b\na >= b\n"
    tokens, ec = _lex(source)
    assert ec.is_empty()
    comp_values = [t.value for t in tokens if t.type == TokenType.COMPARISON]
    assert comp_values.count("!=") == 1
    assert comp_values.count("<") == 1
    assert comp_values.count(">") == 1
    assert comp_values.count("<=") == 1
    assert comp_values.count(">=") == 1


def test_L5_arithmetic_operators():
    """'+', '-', '*', '/' each appear exactly once as OPERATOR tokens."""
    tokens, ec = _lex("a + b - c * d / e\n")
    assert ec.is_empty()
    op_values = [t.value for t in tokens if t.type == TokenType.OPERATOR]
    assert op_values.count("+") == 1
    assert op_values.count("-") == 1
    assert op_values.count("*") == 1
    assert op_values.count("/") == 1


def test_L6_all_19_keywords():
    """All 19 Atena keywords on one line produce exactly 19 KEYWORD tokens."""
    # All 19 keywords: show ask if else while repeat times and or not
    # function return add to remove from length true false
    source = "show ask if else while repeat times and or not function return add to remove from length true false\n"
    tokens, ec = _lex(source)
    assert ec.is_empty()
    kw_tokens = [t for t in tokens if t.type == TokenType.KEYWORD]
    assert len(kw_tokens) == 19


def test_L7_string_literal():
    """A double-quoted string literal produces a STRING token with the inner value."""
    tokens, ec = _lex('"hello"\n')
    assert ec.is_empty()
    strings = [t for t in tokens if t.type == TokenType.STRING]
    assert len(strings) == 1
    assert strings[0].value == "hello"


def test_L7_number_literal():
    """An integer literal produces a NUMBER token with the digit string as value."""
    tokens, ec = _lex("42\n")
    assert ec.is_empty()
    numbers = [t for t in tokens if t.type == TokenType.NUMBER]
    assert len(numbers) == 1
    assert numbers[0].value == "42"


def test_L7_token_position_fields():
    """Every non-EOF token in 'x = 10' has line >= 1 and a non-empty source_line."""
    tokens, ec = _lex("x = 10\n")
    assert ec.is_empty()
    non_eof = [t for t in tokens if t.type != TokenType.EOF]
    for tok in non_eof:
        assert tok.line >= 1, f"Token {tok!r} has line < 1"
        assert tok.source_line != "", f"Token {tok!r} has empty source_line"


# ---------------------------------------------------------------------------
# Layer 2 — Error-path tests (LEX-04 and LEX-08)
# ---------------------------------------------------------------------------


def test_L4_mixed_tabs_spaces_error():
    """Mixed tabs and spaces in indentation produces a 'tabs and spaces' error."""
    source = "if x\n    show y\n\tshow z\n"  # 4-space indent on line 2, tab on line 3
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "tabs and spaces" in report


def test_L4_staircase_dedent_error():
    """Dedent to a column never opened produces a 'doesn't match' error."""
    source = "if x\n    show y\n  show z\n"  # indented 4, then dedent to 2 (never opened)
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "doesn't match" in report


def test_L4_over_indent_error():
    """Jumping two indent units at once produces a 'too far' error."""
    # unit=4 (pinned on first indent); third line jumps from 4 to 12 (delta=8=2 units)
    source = "if x\n    if y\n            show z\n"
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "too far" in report


def test_L4_ragged_width_error():
    """An indent of 6 spaces when the unit is 4 produces a 'same size' error."""
    # unit=4 (pinned on first indent at line 2); line 3 indents by 6 (non-multiple of 4)
    source = "if x\n    if y\n      show z\n"
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "same size" in report


def test_L8_unterminated_string():
    """An unterminated string literal produces an error on line 1 without crashing."""
    _, ec = _lex('"hello\n')
    assert not ec.is_empty()
    report = ec.report()
    assert "Error on line 1" in report


def test_L8_decimal_offramp():
    """A decimal number produces the 'whole numbers' off-ramp error on line 1."""
    _, ec = _lex("x = 3.5\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "whole numbers" in report
    assert "Error on line 1" in report


def test_L8_single_quote_offramp():
    """A single-quoted string produces the 'double quotes' off-ramp error on line 1."""
    _, ec = _lex("x = 'hello'\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "double quotes" in report
    assert "Error on line 1" in report


def test_L8_colon_offramp():
    """A trailing colon produces the 'colons' off-ramp error on line 1."""
    _, ec = _lex("if x > 1:\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "colons" in report
    assert "Error on line 1" in report


def test_L8_semicolon_offramp():
    """A semicolon produces the 'own line' off-ramp error on line 1."""
    _, ec = _lex("a = 1; b = 2\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "own line" in report
    assert "Error on line 1" in report


def test_L8_unexpected_char():
    """An unexpected character '@' produces an error on line 1 without crashing."""
    _, ec = _lex("x = @foo\n")
    assert not ec.is_empty()
    report = ec.report()
    assert "Error on line 1" in report


# ---------------------------------------------------------------------------
# Layer 2 — Cross-requirement tests (collect-all guarantee)
# ---------------------------------------------------------------------------


def test_Lx_multiple_errors_collected():
    """An unterminated string on line 1 and a decimal on line 2 are both collected."""
    source = '"hello\nx = 3.5\n'
    _, ec = _lex(source)
    assert not ec.is_empty()
    report = ec.report()
    assert "Error on line 1" in report
    assert "Error on line 2" in report


def test_Lx_offramp_no_infinite_loop():
    """A single-quote and decimal together return without hanging and collect errors."""
    source = "x = 'abc'; y = 3.5\n"
    _, ec = _lex(source)
    # If we get here, no infinite loop occurred.
    assert not ec.is_empty()


def test_L8_non_ascii_digit_rejected():
    """A non-ASCII digit (Arabic-Indic ١, U+0661) is an unexpected character, not a NUMBER.

    Regression for CR-01: str.isdigit() accepts Unicode digits, which would slip through
    as NUMBER tokens and crash ast.parse() at codegen — a Python traceback reaching the
    learner. The lexer must reject them with a plain-English error at lex time.
    """
    tokens, ec = _lex("y = ١\n")
    # The non-ASCII digit must NOT become a NUMBER token (the only number-shaped input here).
    assert not any(t.type == TokenType.NUMBER for t in tokens)
    # It is reported as a plain-English error pinned to its line; no Python exception escapes.
    assert not ec.is_empty()
    assert "Error on line 1" in ec.report()
