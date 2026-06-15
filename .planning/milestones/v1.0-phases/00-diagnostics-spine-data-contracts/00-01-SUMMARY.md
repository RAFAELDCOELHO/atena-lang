---
phase: "00"
plan: "01"
subsystem: "scaffold"
tags: [scaffold, packaging, imports, pytest, stubs]
dependency_graph:
  requires: []
  provides:
    - "pip-installable atena-lang package via hatchling + src layout"
    - "importable src/atena/ package with seven stub modules"
    - "pytest-discoverable tests/ tree with conftest.py"
    - "atena CLI entry point (stub) registered at atena.cli:main"
  affects:
    - "all subsequent plans — assumes pip install -e . and pytest work"
tech_stack:
  added:
    - "hatchling (build backend, pyproject.toml)"
    - "pytest 9.0.3 (test runner)"
  patterns:
    - "src-layout: src/atena/ package discovered via tool.hatch.build.targets.wheel"
    - "PEP 621 [project.scripts] entry point"
    - "stub modules with ... bodies and # TODO: implemented in Plan 0X comments"
key_files:
  created:
    - pyproject.toml
    - src/atena/__init__.py
    - src/atena/__main__.py
    - src/atena/errors.py
    - src/atena/tokens.py
    - src/atena/ast_nodes.py
    - src/atena/cli.py
    - src/atena/pipeline.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_imports.py
    - .gitignore
  modified: []
decisions:
  - "Used pytest smoke tests (tests/test_imports.py) to satisfy `pytest --collect-only` exit-0 requirement — an empty tests/ dir gives exit 5 (no tests collected)"
  - "Added .gitignore as Rule 2 (missing critical) — without it __pycache__ and .venv would pollute git status from the first commit"
  - "version set to 0.1.0 (pre-release) rather than 1.0.0 — STACK.md template shows 1.0.0 but the project is in scaffolding; 0.1.0 is more honest for a stub skeleton"
metrics:
  duration: "~3 min"
  completed: "2026-06-13"
  tasks: 2
  files_created: 12
  files_modified: 0
---

# Phase 00 Plan 01: Project Scaffold & Stub Modules Summary

**One-liner:** hatchling src-layout scaffold with seven stub modules and pytest discovery — the foundation every subsequent plan builds on.

## What Was Built

This plan bootstraps the project skeleton from a bare git repo:

- **`pyproject.toml`** with hatchling build backend, `requires-python = ">=3.11"`, zero runtime dependencies, `atena = "atena.cli:main"` entry point, and `testpaths = ["tests"]`.
- **`src/atena/` package** with `__init__.py` (empty marker) and `__main__.py` (delegates to `cli.main`).
- **Five stub modules** — `errors.py`, `tokens.py`, `ast_nodes.py`, `cli.py`, `pipeline.py` — each importable with no errors, each declaring the names later plans implement.
- **`tests/` tree** with `__init__.py`, `conftest.py` (empty fixture scaffold), and `test_imports.py` (six smoke tests confirming all stubs are importable).
- **`.gitignore`** covering `__pycache__/`, `.venv/`, `dist/`, `.pytest_cache/`, and OS artifacts.

## Verification Evidence

```
pip install -e .                          → Succeeds (hatchling installs atena-lang 0.1.0)
python -c "import atena"                  → OK
python -c "from atena.errors import ErrorCollector; from atena.tokens import Token; from atena.ast_nodes import Program; print('OK')"  → OK
python -m atena --help                    → exits 0 (stub main() returns None)
pytest tests/ --collect-only -q           → 6 tests collected, exit 0
grep sibling imports in tokens.py/ast_nodes.py → 0 (pure stdlib only)
```

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create pyproject.toml and src layout | 4ae2b4a | pyproject.toml, src/atena/__init__.py, __main__.py, tests/__init__.py, tests/conftest.py |
| 2 | Create stub modules for all phase-0 components | 24201fe | src/atena/errors.py, tokens.py, ast_nodes.py, cli.py, pipeline.py, tests/test_imports.py, .gitignore |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added smoke tests to satisfy `pytest --collect-only` exit-0 requirement**
- **Found during:** Task 2 verification
- **Issue:** An empty `tests/` directory causes `pytest --collect-only` to exit with code 5 ("no tests collected"), not 0. The plan's acceptance criterion requires exit 0.
- **Fix:** Added `tests/test_imports.py` with six smoke tests (one per stub module) — no logic assertions, just import confirmation.
- **Files modified:** `tests/test_imports.py` (created)
- **Commit:** 24201fe

**2. [Rule 2 - Missing Critical] Added `.gitignore`**
- **Found during:** Task 2 — after creating stub modules, `git status` showed `__pycache__/` directories untracked.
- **Issue:** Without a `.gitignore`, every `pytest` run and every `pip install` would pollute git status with generated artifacts, making subsequent task commits noisy and error-prone.
- **Fix:** Created `.gitignore` covering Python bytecode, virtual environments, build artifacts, pytest cache, and OS artifacts.
- **Files modified:** `.gitignore` (created)
- **Commit:** 24201fe

## Known Stubs

All stubs in this plan are intentional by design — Plan 01 creates scaffolding only. Each stub has a `# TODO: implemented in Plan 0X` annotation pointing to the plan that fills it in:

| Module | Stub | Filled in |
|--------|------|-----------|
| `src/atena/errors.py` | `ErrorCollector.add/is_empty/report`, `suggest()` | Plan 02 |
| `src/atena/tokens.py` | `TokenType` class, `Token` dataclass | Plan 03 |
| `src/atena/ast_nodes.py` | `Node`, `Program` and full node-set | Plan 03 |
| `src/atena/cli.py` | `main()` | Plan 05 |
| `src/atena/pipeline.py` | `transpile()` | Plan 05 |

These stubs are intentional and do not prevent the plan's goal (project scaffolding and importability) from being achieved.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The only trust boundary is `pip install -e .` (developer-controlled; flagged in plan's STRIDE register as accepted/accepted).

## Self-Check: PASSED

- [x] `pyproject.toml` exists and contains `requires-python = ">=3.11"`, `dependencies = []`, `atena = "atena.cli:main"`, `testpaths = ["tests"]`
- [x] All 7 `src/atena/` modules exist and are importable
- [x] `tokens.py` and `ast_nodes.py` have zero non-stdlib imports
- [x] `pytest tests/ --collect-only` exits 0 (6 tests collected)
- [x] Commit `4ae2b4a` exists in git log (Task 1)
- [x] Commit `24201fe` exists in git log (Task 2)
