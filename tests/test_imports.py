"""
Smoke tests that verify all Phase 0 stub modules are importable.

These tests contain NO logic assertions — they exist purely to confirm
the project skeleton is correctly installed and all seven src/atena/
modules can be imported without error, satisfying the plan's requirement
that `pytest --collect-only` exits 0.
"""


def test_atena_package_importable() -> None:
    """The atena package imports without error after pip install -e ."""
    import atena  # noqa: F401


def test_errors_module_importable() -> None:
    """errors.py stub is importable; ErrorCollector and suggest are present."""
    from atena.errors import ErrorCollector, suggest  # noqa: F401


def test_tokens_module_importable() -> None:
    """tokens.py stub is importable; TokenType and Token are present."""
    from atena.tokens import Token, TokenType  # noqa: F401


def test_ast_nodes_module_importable() -> None:
    """ast_nodes.py stub is importable; Node and Program are present."""
    from atena.ast_nodes import Node, Program  # noqa: F401


def test_cli_module_importable() -> None:
    """cli.py stub is importable; main is present."""
    from atena.cli import main  # noqa: F401


def test_pipeline_module_importable() -> None:
    """pipeline.py stub is importable; transpile is present."""
    from atena.pipeline import transpile  # noqa: F401
