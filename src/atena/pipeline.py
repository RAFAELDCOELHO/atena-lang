"""
Top-level pipeline: runs Lexer → Parser → Analyzer → Generator in sequence.

Each phase writes into a single shared ErrorCollector.  The driver gates
between phases on errors.is_empty() — if any phase produced errors, the
error report is printed to stderr and the function returns None immediately.
CodeGenerator is only instantiated when the tree is provably clean (GEN-03).

Threat model note (T-05-01-A): the errors.is_empty() gate is structural —
CodeGenerator never receives a partial or error AST because the function
returns before reaching that call when any error exists.

Threat model note (T-05-01-C): errors.report() produces only the canonical
plain-English format; no Python stack frames or internal type names reach
the learner via this path.
"""

from __future__ import annotations

import sys

from atena.errors import ErrorCollector
from atena.lexer import Lexer
from atena.parser import Parser
from atena.analyzer import SemanticAnalyzer
from atena.codegen import CodeGenerator


def transpile(source: str, filename: str) -> str | None:
    """Transpile Atena source to a Python 3 source string.

    Parameters
    ----------
    source:
        The raw Atena source text to transpile.
    filename:
        The name of the source file (reserved for future use, e.g. as the
        ``filename`` argument to ``compile()`` in the CLI run path).

    Returns
    -------
    str
        The generated Python 3 source on success.
    None
        If any phase produced errors.  The canonical error report has
        already been printed to *stderr* before returning None.
    """
    errors = ErrorCollector()

    # Phase 1 — Lexing
    tokens = Lexer(source, errors).tokenize()
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return None

    # Phase 2 — Parsing
    program = Parser(tokens, errors).parse()
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return None

    # Phase 3 — Semantic analysis
    program = SemanticAnalyzer(program, errors).analyze()
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return None

    # Phase 4 — Code generation (GEN-03: only reached when errors.is_empty())
    return CodeGenerator(program).generate()
