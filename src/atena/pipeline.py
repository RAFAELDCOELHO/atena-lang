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
from types import CodeType

from atena.ast_nodes import Program
from atena.errors import ErrorCollector
from atena.lexer import Lexer
from atena.parser import Parser
from atena.analyzer import SemanticAnalyzer
from atena.codegen import CodeGenerator


def _gate(errors: ErrorCollector) -> bool:
    """Print the canonical error report and signal a halt if any errors exist.

    Returns True (caller must stop) when *errors* is non-empty; False otherwise.
    Centralises the between-phase gate so the report-to-stderr behaviour lives
    in exactly one place (WR-04).
    """
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return True
    return False


def _analyze(source: str) -> Program | None:
    """Run Lexer → Parser → Analyzer with between-phase error gating.

    Returns the fully-analyzed ``Program`` (contract C) on success, or None if
    any phase produced errors — in which case the canonical error report has
    already been printed to *stderr*.  The Generator is never reached on the
    error path (GEN-03 / T-05-01-A: it only sees a provably-clean tree).
    """
    errors = ErrorCollector()

    # Phase 1 — Lexing
    tokens = Lexer(source, errors).tokenize()
    if _gate(errors):
        return None

    # Phase 2 — Parsing
    program = Parser(tokens, errors).parse()
    if _gate(errors):
        return None

    # Phase 3 — Semantic analysis
    program = SemanticAnalyzer(program, errors).analyze()
    if _gate(errors):
        return None

    return program


def transpile(source: str, filename: str | None = None) -> str | None:
    """Transpile Atena source to a Python 3 source string.

    Parameters
    ----------
    source:
        The raw Atena source text to transpile.
    filename:
        The name of the source file (unused by this path; accepted for a
        symmetric signature with ``compile_for_run``).

    Returns
    -------
    str
        The generated Python 3 source on success (used by ``atena build``).
    None
        If any phase produced errors.  The canonical error report has
        already been printed to *stderr* before returning None.
    """
    program = _analyze(source)
    if program is None:
        return None

    # Phase 4 — Code generation (GEN-03: only reached when errors.is_empty())
    return CodeGenerator(program).generate()


def compile_for_run(source: str, filename: str) -> CodeType | None:
    """Transpile Atena source and compile it to an executable code object.

    Unlike :func:`transpile`, this compiles the Python ``ast.Module`` *directly*
    (rather than the unparsed source string).  The module's nodes carry the
    learner's original Atena line numbers, so any runtime traceback the code
    object produces reports the Atena line — which is what ``atena run`` needs
    to print "Error on line N" and the offending source line correctly (CR-01).

    Parameters
    ----------
    source:
        The raw Atena source text.
    filename:
        The display filename embedded in the compiled code object (the CLI
        passes the basename so absolute paths never leak — WR-05).

    Returns
    -------
    CodeType
        A compiled code object ready for ``exec`` on success.
    None
        If any phase produced errors (report already printed to *stderr*).

    A ``SyntaxError`` from ``compile`` means the Generator emitted invalid
    Python — an internal Atena bug, never a learner error.  It is allowed to
    propagate so the CLI can route it to the internal-error message (CR-03).
    """
    program = _analyze(source)
    if program is None:
        return None

    # Phase 4 — build the module (GEN-03: only reached when errors.is_empty())
    module = CodeGenerator(program).build_module()
    return compile(module, filename, "exec")
