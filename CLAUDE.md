<!-- GSD:project-start source:PROJECT.md -->
## Project

**Atena Language**

Atena v1.0 is a teaching programming language that transpiles to runnable Python 3. It strips away syntactic noise — no colons, no braces — and uses indentation-delimited blocks with plain English keywords (`show`, `ask`, `repeat`, `function`). It is built for complete non-programmers learning algorithmic logic, while still exposing real engineering concepts: functions, control flow, lists, and dictionaries. The transpiler is a single-pass pipeline of four sequential phases — Lexer → Parser → Semantic Analyzer → Code Generator — written in Python 3.

**Core Value:** A complete non-programmer can write real algorithmic logic (functions, control flow, lists, dicts) without ever fighting syntax, and never sees a Python stack trace — only plain-English errors that name the line and show the offending code.

### Constraints

- **Tech stack**: Python 3 — the transpiler is written in Python 3 and emits Python 3. Standard library only unless a dependency proves necessary.
- **Architecture**: Four sequential phases (Lexer → Parser → Analyzer → Generator). Build one phase at a time; do not advance until the current phase is 100% green.
- **Process**: TDD — write the failing test first, then implement. Commit after every completed task. Feature branch per phase (`feat/lexer`, `feat/parser`, …); never work directly on `main`.
- **Indentation**: Blocks are indentation-delimited. A single file must use consistent tabs OR spaces (not mixed).
- **Errors**: All user-facing errors are plain English with line number and offending source line. No Python stack traces ever reach the learner. Errors are collected across a run, not fail-fast.
- **Strings/Numbers (v1.0)**: Double-quoted strings only; integers only.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Executive Recommendation
## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | **3.11+** (target), tested on 3.11–3.14 | Implementation language and target language | 3.11 is the floor: best balance of modern syntax (`match` statements for token/node dispatch, exception groups, `Self` typing) against installed base. 3.10 is fine if you need it but reaches EOL Oct 2026. See "Minimum Python Version" below. |
| **`dataclasses`** (stdlib) | bundled | AST node representation | The standard, idiomatic way to define typed tree nodes with zero boilerplate. Mutable (the analyzer rewrites nodes in place: 1→0 indexing, `str()` injection), supports `lineno`/`col_offset` fields directly, mirrors how CPython's own `ast` nodes expose position. See "AST Representation" below. |
| **`ast` + `ast.unparse()`** (stdlib) | bundled (3.9+) | Code generation — emit Python 3 source | Build a real Python AST from the analyzed Atena AST, then `ast.unparse()` it. Produces correct, runnable, properly-parenthesized Python with no manual string-building, no operator-precedence bugs, no indentation bookkeeping in the emitter. Replaces `astor` entirely. |
| **`argparse`** (stdlib) | bundled | CLI dispatch (`atena run` / `atena build`) | Subcommand support, auto-generated `--help`, zero dependencies. Proportional to a two-verb CLI; pulling in Click/Typer would be over-engineering here. |
| **`pytest`** | **9.1.0** (requires Python ≥3.10) | Test framework + runner | The de-facto standard. Plain `assert`, fixtures, and `@pytest.mark.parametrize` are exactly the primitives a transpiler test suite needs. See "Testing" below. |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **`hatchling`** | **1.30.1** | PEP 517 build backend for the wheel/sdist | Use as the `build-backend` in `pyproject.toml`. Modern default, zero-config for a pure-Python package, cleaner than setuptools for greenfield. See "Packaging" below. |
| `syrupy` | latest (3.x) | Snapshot/golden testing plugin for pytest | **Optional.** Only adopt if managing golden `.py` outputs as inline files becomes painful. For Atena's scale, plain fixture files + `assert generated == expected` is enough and has zero dependencies. Recommend starting without it. |
| `tox` or `nox` | latest | Multi-version test matrix (3.11–3.14) | **Optional, late.** Add only when you want CI to prove the floor-to-ceiling Python range. Not needed for day-one development. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Test runner | Configure under `[tool.pytest.ini_options]` in `pyproject.toml`. Set `testpaths = ["tests"]`. |
| **ruff** (optional) | Linter + formatter | If you want one tool for both, ruff is the current standard. Not required for correctness; nice-to-have for a public teaching repo. |
| **`python -m build`** | Build wheel/sdist locally | Frontend that invokes hatchling. Install with `pip install build`. |
## Installation
# Runtime: the transpiler ships with ZERO runtime dependencies.
# Everything it needs (dataclasses, ast, argparse) is stdlib.
# Dev dependencies (install into a venv)
# hatchling is pulled automatically as the build backend at build time;
# you do not pip-install it directly.
# Optional, only if/when justified:
# pip install syrupy        # snapshot testing
# pip install tox           # multi-version test matrix
# pip install ruff          # lint + format
## Deep Dives (project-specific decisions)
### Hand-roll vs parser generator — RECOMMEND HAND-ROLL (HIGH confidence)
### AST representation — RECOMMEND `@dataclass` nodes (HIGH confidence)
| Choice | Verdict | Reasoning |
|--------|---------|-----------|
| **`@dataclass`** | **RECOMMENDED** | Mutable (the analyzer rewrites in place: 1→0 index, `str()` injection), typed fields, free `__repr__` for debugging, `lineno`/`col` are just fields. Mirrors CPython's own `ast` node convention (`lineno`, `col_offset`). Readable as a teaching artifact. |
| `typing.NamedTuple` | Avoid | **Immutable** — every analyzer rewrite forces a `._replace()` and rebuild of parent nodes. That friction directly harms the 1→0 and `str()`-injection passes, which are central to Atena. |
| Plain classes | Acceptable but worse | You'd hand-write `__init__` and `__repr__` for every node. Dataclasses give both for free with less code to read. |
| `ast.AST` subclasses | Avoid | Coupling your *source* AST to CPython's internal AST is confusing for a teaching codebase and brittle across Python versions. Keep the Atena AST your own; only touch `ast` at the final codegen step. |
### Code generation — RECOMMEND `ast.unparse()` (HIGH confidence)
- **(A) Build a Python `ast` and `ast.unparse()` it (recommended).** Map each analyzed Atena node to the corresponding `ast` node (`ast.Assign`, `ast.For`, `ast.Call`, `ast.Subscript`, etc.), call `ast.fix_missing_locations(module)`, then `ast.unparse(module)`. You get correct indentation, correct operator precedence/parenthesization, and runnable output for free. Verified working on the stdlib: building a small tree and unparsing `x = items[0]` round-trips correctly.
- **(B) Emit Python source as strings directly.** Simpler conceptually, but you re-implement indentation and parenthesization by hand and risk precedence bugs. Acceptable given Atena's tiny grammar, and arguably more transparent as a teaching artifact, but more error-prone.
### Testing — RECOMMEND pytest with fixture files + parametrization (HIGH confidence)
### Packaging — RECOMMEND pyproject.toml + hatchling + `[project.scripts]` (HIGH confidence)
- **Single `pyproject.toml`**, src-layout (`src/atena/`), `hatchling` build backend.
- **`[project.scripts]` table** (PEP 621) — `atena = "atena.cli:main"` — is the modern, declarative replacement for the old `setup.py` `entry_points={'console_scripts': [...]}`. After `pip install .` (or `pip install atena-lang`), the `atena` command is on PATH.
- `main()` builds an `argparse` parser with two subcommands: `run` (transpile to a temp/in-memory module and `exec`/run it) and `build` (transpile and write `file.py`). Crucially, `main()` must catch the transpiler's collected errors and print them as plain English — **no Python traceback may escape to the user**. Wrap the top level so any unexpected internal exception is converted to a generic friendly message, while *expected* Atena errors print the `Error on line N` list and exit non-zero.
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Hand-rolled lexer + recursive-descent/Pratt parser | **Lark** (1.3.1) | A genuinely large/ambiguous grammar, or you want Earley parsing for an inherently ambiguous language. Not Atena — its `Indenter` postlex still needs hand-written indentation logic and has comment-interaction bugs. |
| Hand-rolled parser | **PLY** (3.11) / **SLY** (0.5) | Teaching LALR/yacc concepts specifically, or porting an existing yacc grammar. PLY is yacc-style and dated; SLY is unmaintained-ish (0.5, never 1.0). Both add a code-gen/runtime layer Atena doesn't need. |
| `ast.unparse()` | **astor** (0.8.1) | Never, for new code. Only relevant if you must run on Python <3.9. Atena targets 3.11+, so `ast.unparse()` always wins. |
| `@dataclass` nodes | `typing.NamedTuple` | A purely immutable, no-rewrite AST. Atena's analyzer mutates nodes (1→0, `str()` injection), so immutability is a liability here. |
| `argparse` | **Typer / Click** | A CLI with many commands, rich option types, shell completion, or colored help. Atena has two verbs; argparse is proportional and dependency-free. |
| pytest + plain fixtures | **syrupy** (snapshot plugin) | Many large golden outputs that change often and are tedious to update by hand. Adopt later if needed; not day-one. |
| hatchling | **setuptools** (82.0.1) | Existing setuptools project, or you need a setuptools-specific plugin. For greenfield pure-Python, hatchling is cleaner and zero-config. Both are fully valid PEP 517 backends. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **astor** | Abandoned (last release 2019-12-10); superseded by stdlib. | `ast.unparse()` (stdlib, 3.9+) |
| **Parser generator (lark/ply/sly/ANTLR) for the parser** | INDENT/DEDENT still needs hand-written stateful logic; error-recovery/collect-all-errors and friendly line-numbered messages fight the tool; grammar is tiny and LL(1). Pure overhead + a dependency. | Hand-rolled recursive-descent + Pratt expression parser |
| **`typing.NamedTuple` for AST nodes** | Immutable — every analyzer rewrite (1→0 indexing, `str()` injection) forces `_replace` and parent rebuilds. | `@dataclass` nodes (mutable, typed, carry `line`/`col`) |
| **`setup.py` + `entry_points={'console_scripts': ...}`** | Legacy imperative config; deprecated workflow. | `pyproject.toml` `[project.scripts]` (PEP 621) |
| **Click/Typer for the CLI** | Heavyweight for a two-verb CLI; adds a runtime dependency to a tool that should be stdlib-only. | `argparse` (stdlib) |
| **Subclassing CPython's `ast.AST` for the *source* AST** | Couples Atena's tree to CPython internals; brittle across versions; confusing in a teaching repo. | Your own `@dataclass` nodes; touch `ast` only at codegen |
| **Raising exceptions to halt on first error** | Violates the collect-all-errors requirement and risks tracebacks reaching learners. | Accumulate errors in a list per phase; gate codegen on zero errors |
## Stack Patterns by Variant
- Use string-based code generation (strategy B) instead of `ast.unparse()`.
- Because the generated Python then reads like obvious, line-by-line output a student can trace — at the cost of hand-managing indentation/precedence. Atena's tiny grammar makes this tractable.
- Use `ast.unparse()` (strategy A).
- Because precedence, parenthesization, and indentation come for free and are impossible to get subtly wrong.
- Add `syrupy` for snapshot management (`--snapshot-update`).
- Because it removes the manual edit step for expected outputs. Only justified once you have many/large goldens.
- Set `requires-python = ">=3.10"`. `ast.unparse()`, dataclasses, and pytest 9 all still work.
- Note 3.10 reaches EOL Oct 2026; prefer 3.11 as the floor if you can.
## Minimum Python Version
- **3.9 floor would be the absolute minimum** (that's when `ast.unparse()` landed). But 3.9 reaches EOL Oct 2025 — already past. Do not target it.
- **3.10 (EOL Oct 2026)** adds structural pattern matching (`match`/`case`), which is genuinely useful for dispatching on token types and AST node types in lexer/parser/analyzer/codegen. Acceptable floor if an environment forces it.
- **3.11 (EOL Oct 2027)** is the recommended floor: `match` is mature, exception groups and `Self`/typing improvements help, and it has a comfortable support runway. pytest 9.1.0 requires ≥3.10, so no conflict.
- **Test against 3.11, 3.12, 3.13, and 3.14** (3.14.6 is the current stable, released Oct 2025). The transpiler emits plain, conservative Python 3, so the *generated* code runs on an even wider range than the transpiler itself.
| Floor | Status | Use when |
|-------|--------|----------|
| 3.11 | **Recommended** | Default greenfield choice; best support runway + mature `match` |
| 3.10 | Acceptable | An institutional/classroom environment pins 3.10 |
| 3.9  | Avoid | Already EOL (Oct 2025); only if absolutely forced |
## Version Compatibility
| Package | Version | Requires Python | Notes |
|---------|---------|-----------------|-------|
| pytest | 9.1.0 | ≥3.10 | Matches recommended ≥3.11 floor with room to spare |
| hatchling | 1.30.1 | ≥3.10 | Build backend; pulled automatically at build time |
| setuptools (alt) | 82.0.1 | ≥3.9 | Only if you prefer setuptools over hatchling |
| `ast.unparse()` | stdlib | ≥3.9 | The hard floor for the chosen codegen strategy |
| `match`/`case` | stdlib | ≥3.10 | Convenient for token/node dispatch (not required) |
| Python (target) | 3.14.6 latest | — | 3.10 oldest non-EOL until Oct 2026; 3.11 recommended floor |
## Sources
- https://devguide.python.org/versions/ — Python version support/EOL status (HIGH)
- https://endoflife.date/api/python.json — confirmed 3.14.6 latest (2025-10-07), 3.10 EOL 2026-10-31 (HIGH)
- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) — verified current versions: pytest 9.1.0 (req ≥3.10), hatchling 1.30.1 (req ≥3.10), setuptools 82.0.1, lark 1.3.1, astor 0.8.1 (last upload 2019-12-10), sly 0.5, ply 3.11 (HIGH)
- Local stdlib verification — confirmed `ast.unparse` present and round-trips a built AST to source on Python 3.12 (HIGH)
- https://docs.python.org/3/library/ast.html — `lineno`/`col_offset` node attributes, `fix_missing_locations`, unparse (HIGH)
- https://docs.pytest.org/en/stable/ — fixtures, parametrization, plain-assert model (HIGH)
- https://github.com/berkerpeksag/astor/issues/204 — maintainers acknowledge `ast.unparse` supersedes astor (HIGH)
- https://lark-parser.readthedocs.io/en/latest/examples/indented_tree.html + lark `indenter.py` — Lark's INDENT/DEDENT requires a hand-written postlex Indenter; known comment-interaction limitation (MEDIUM-HIGH)
- https://michaeldadams.org/papers/layout_parsing/LayoutParsing.pdf and the offside-rule lexer write-ups — standard indentation-stack INDENT/DEDENT technique (HIGH, well-established)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
