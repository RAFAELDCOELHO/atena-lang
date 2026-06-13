# Stack Research

**Domain:** Programming-language transpiler (Atena → Python 3), teaching-oriented, single-pass 4-phase pipeline
**Researched:** 2026-06-13
**Confidence:** HIGH

## Executive Recommendation

**Standard library only for the transpiler core. Add exactly two dev-time dependencies: `pytest` and `hatchling` (build backend).** No parser generator, no codegen library. Everything the pipeline needs — tokenizing, the AST, semantic analysis, emitting Python source, and the CLI — is covered by the Python 3 standard library at a level of polish that exceeds the available third-party options for this specific shape of project.

The two decisive facts behind this:

1. **`ast.unparse()` is in the standard library** (since Python 3.9). It turns a Python AST back into valid, runnable source code with correct formatting and parenthesization. This obsoletes `astor` (the historical answer), whose last release was December 2019. You do not need a codegen library.
2. **INDENT/DEDENT cannot be delegated to a parser generator cleanly.** Significant-whitespace tokenization is inherently a context-sensitive, stateful pre-pass. Even Lark — the best modern Python parser generator — handles it with a hand-managed `Indenter` postlex stage that has documented edge-case bugs with comments inside indentation-sensitive regions (exactly the case Atena hits, since it skips comment-only lines). A hand-rolled lexer is simpler, fully under your control, and trivially carries line/column through every token.

---

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

---

## Installation

```bash
# Runtime: the transpiler ships with ZERO runtime dependencies.
# Everything it needs (dataclasses, ast, argparse) is stdlib.

# Dev dependencies (install into a venv)
pip install pytest          # 9.1.0 — test runner
pip install build           # frontend for building the package
# hatchling is pulled automatically as the build backend at build time;
# you do not pip-install it directly.

# Optional, only if/when justified:
# pip install syrupy        # snapshot testing
# pip install tox           # multi-version test matrix
# pip install ruff          # lint + format
```

`pyproject.toml` declares the build backend; you never install hatchling by hand:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "atena-lang"
version = "1.0.0"
description = "Atena: a teaching language that transpiles to Python 3"
requires-python = ">=3.11"
dependencies = []                       # zero runtime deps

[project.scripts]
atena = "atena.cli:main"                # creates the `atena` console command

[tool.hatch.build.targets.wheel]
packages = ["src/atena"]                # src-layout

[tool.pytest.ini_options]
testpaths = ["tests"]
```

The `[project.scripts]` table (PEP 621, the standard that replaced `entry_points={'console_scripts': ...}`) is what makes `atena run file.atena` and `atena build file.atena` work after `pip install`. `atena = "atena.cli:main"` means "the `atena` command calls `main()` in `atena/cli.py`"; argparse inside `main()` dispatches `run` vs `build`.

---

## Deep Dives (project-specific decisions)

### Hand-roll vs parser generator — RECOMMEND HAND-ROLL (HIGH confidence)

**Hand-roll the lexer AND the parser. Do not use lark, ply, sly, or ANTLR.**

Why, tied to Atena's constraints:

1. **INDENT/DEDENT is a stateful pre-pass no matter what.** The offside rule (emit INDENT when a line is more indented than the previous, DEDENT(s) when less) requires a lexer that tracks an indentation stack across lines. This is the *standard, well-documented* technique and is independent of any parser tool — Python's own `tokenize` module does exactly this. A parser generator does not save you this work; Lark, the best option, makes you supply a hand-written `Indenter` postlex class anyway, and it has known bugs when comments interleave with indentation. Atena explicitly skips blank and comment-only lines, so you'd be walking straight into that edge case.

2. **Error recovery / collect-all-errors fights generated parsers.** Atena must gather *every* error in a run, not stop at the first. Hand-written recursive-descent parsers make this natural: on a parse error you record it, synchronize to a recovery point (e.g., the next line start / DEDENT), and keep going. Parser generators are built around fail-fast or opaque automaton-level recovery that is hard to shape into friendly, line-numbered messages.

3. **Plain-English errors with line + source line demand full control.** The requirement is `Error on line {N}: ... → {source}` with no tracebacks. When you own every token (each carrying `line`, `col`) and every parse decision, producing that message is a one-liner. With a generated parser you fight the tool's error vocabulary.

4. **The grammar is tiny and LL(1)-friendly.** No colons/braces, integer-only, double-quoted strings only, flat scope, no `elif`, no slicing, no closures. A recursive-descent parser with a Pratt (precedence-climbing) expression sub-parser is a few hundred lines and maps 1:1 to the spec's grammar. A parser-generator's build step, grammar DSL, and dependency are pure overhead at this size.

5. **Teaching artifact value.** The repo *is* the lesson. A readable hand-written lexer/parser is itself pedagogical; a `.lark` grammar file plus a black-box runtime is not.

**Lexer pattern (standard):** read line by line, compute leading-whitespace level, compare to a stack → push + emit `INDENT`, or pop + emit one `DEDENT` per level unwound. Enforce the "tabs OR spaces, not mixed" rule here. Skip blank/comment-only lines *before* computing indentation. Every token gets `(type, value, line, col)`.

**Parser pattern:** recursive descent for statements (`show`, `ask`, `repeat`, `function`, if/else), Pratt parsing for expressions to honor operator precedence cleanly. Consume `INDENT`…`DEDENT` to bracket blocks instead of `{`…`}`.

### AST representation — RECOMMEND `@dataclass` nodes (HIGH confidence)

Use plain `@dataclass` classes, one per node type, each carrying position fields:

```python
from dataclasses import dataclass, field

@dataclass
class Node:
    line: int
    col: int = 0

@dataclass
class BinOp(Node):
    op: str
    left: "Node"
    right: "Node"
```

Tradeoffs vs the alternatives, judged for a *teaching transpiler that needs line-numbered errors*:

| Choice | Verdict | Reasoning |
|--------|---------|-----------|
| **`@dataclass`** | **RECOMMENDED** | Mutable (the analyzer rewrites in place: 1→0 index, `str()` injection), typed fields, free `__repr__` for debugging, `lineno`/`col` are just fields. Mirrors CPython's own `ast` node convention (`lineno`, `col_offset`). Readable as a teaching artifact. |
| `typing.NamedTuple` | Avoid | **Immutable** — every analyzer rewrite forces a `._replace()` and rebuild of parent nodes. That friction directly harms the 1→0 and `str()`-injection passes, which are central to Atena. |
| Plain classes | Acceptable but worse | You'd hand-write `__init__` and `__repr__` for every node. Dataclasses give both for free with less code to read. |
| `ast.AST` subclasses | Avoid | Coupling your *source* AST to CPython's internal AST is confusing for a teaching codebase and brittle across Python versions. Keep the Atena AST your own; only touch `ast` at the final codegen step. |

**Carrying position through the pipeline:** put `line`/`col` on the token, copy it onto the AST node at parse time, and keep it on the node through analysis. At codegen, the only place you build CPython `ast` nodes, call `ast.fix_missing_locations()` before `ast.unparse()` so you don't have to set positions on the *generated* Python tree. Atena-level errors reference the Atena node's `line`; Python-level positions are irrelevant to the learner.

### Code generation — RECOMMEND `ast.unparse()` (HIGH confidence)

Two valid strategies; pick based on appetite:

- **(A) Build a Python `ast` and `ast.unparse()` it (recommended).** Map each analyzed Atena node to the corresponding `ast` node (`ast.Assign`, `ast.For`, `ast.Call`, `ast.Subscript`, etc.), call `ast.fix_missing_locations(module)`, then `ast.unparse(module)`. You get correct indentation, correct operator precedence/parenthesization, and runnable output for free. Verified working on the stdlib: building a small tree and unparsing `x = items[0]` round-trips correctly.
- **(B) Emit Python source as strings directly.** Simpler conceptually, but you re-implement indentation and parenthesization by hand and risk precedence bugs. Acceptable given Atena's tiny grammar, and arguably more transparent as a teaching artifact, but more error-prone.

Recommend **(A)** for correctness, with **(B)** as a legitimate fallback if you want the emitter to read like obvious, line-by-line Python for students. Either way: **do not add `astor`** — it is abandoned (last release 2019-12-10) and `ast.unparse()` supersedes it.

### Testing — RECOMMEND pytest with fixture files + parametrization (HIGH confidence)

Structure the suite as three layers:

1. **Unit tests per phase.** `@pytest.mark.parametrize` over `(source, expected_tokens)`, `(tokens, expected_ast)`, etc. Parametrization is ideal because each phase has many small input→output cases.
2. **Golden/snapshot tests for codegen.** Keep paired fixture files: `tests/fixtures/<name>.atena` and `tests/fixtures/<name>.expected.py`. A parametrized test discovers each pair, transpiles the `.atena`, and asserts string-equality with the `.expected.py`. Start with **plain file fixtures + `assert`** (zero deps); adopt `syrupy` only if updating goldens by hand becomes a chore. The spec's complete `school.atena`-style program and its expected Python is your canonical end-to-end golden fixture.
3. **Error-collection integration tests.** Feed deliberately-broken programs (e.g., `items[0]`, undefined variable, wrong arity) and assert that the run returns the *full list* of plain-English errors in `Error on line {N}: ... → {source}` form — proving error recovery, not fail-fast. This is the test that locks in the "collect all errors" requirement.

Use `pytest.ini_options` in `pyproject.toml` (no separate `pytest.ini` needed). `unittest` would work but is more boilerplate (classes, `self.assertEqual`) for no benefit; pytest's plain-`assert` style is also easier for learners reading the repo.

### Packaging — RECOMMEND pyproject.toml + hatchling + `[project.scripts]` (HIGH confidence)

- **Single `pyproject.toml`**, src-layout (`src/atena/`), `hatchling` build backend.
- **`[project.scripts]` table** (PEP 621) — `atena = "atena.cli:main"` — is the modern, declarative replacement for the old `setup.py` `entry_points={'console_scripts': [...]}`. After `pip install .` (or `pip install atena-lang`), the `atena` command is on PATH.
- `main()` builds an `argparse` parser with two subcommands: `run` (transpile to a temp/in-memory module and `exec`/run it) and `build` (transpile and write `file.py`). Crucially, `main()` must catch the transpiler's collected errors and print them as plain English — **no Python traceback may escape to the user**. Wrap the top level so any unexpected internal exception is converted to a generic friendly message, while *expected* Atena errors print the `Error on line N` list and exit non-zero.

---

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

---

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

---

## Stack Patterns by Variant

**If you want the simplest possible emitter (max teaching transparency):**
- Use string-based code generation (strategy B) instead of `ast.unparse()`.
- Because the generated Python then reads like obvious, line-by-line output a student can trace — at the cost of hand-managing indentation/precedence. Atena's tiny grammar makes this tractable.

**If you want maximum correctness with least emitter code:**
- Use `ast.unparse()` (strategy A).
- Because precedence, parenthesization, and indentation come for free and are impossible to get subtly wrong.

**If golden-file maintenance becomes painful:**
- Add `syrupy` for snapshot management (`--snapshot-update`).
- Because it removes the manual edit step for expected outputs. Only justified once you have many/large goldens.

**If you must support Python 3.10 (e.g., an older institutional environment):**
- Set `requires-python = ">=3.10"`. `ast.unparse()`, dataclasses, and pytest 9 all still work.
- Note 3.10 reaches EOL Oct 2026; prefer 3.11 as the floor if you can.

---

## Minimum Python Version

**Recommend `requires-python = ">=3.11"`.** Confidence: HIGH.

Rationale tied to the project:
- **3.9 floor would be the absolute minimum** (that's when `ast.unparse()` landed). But 3.9 reaches EOL Oct 2025 — already past. Do not target it.
- **3.10 (EOL Oct 2026)** adds structural pattern matching (`match`/`case`), which is genuinely useful for dispatching on token types and AST node types in lexer/parser/analyzer/codegen. Acceptable floor if an environment forces it.
- **3.11 (EOL Oct 2027)** is the recommended floor: `match` is mature, exception groups and `Self`/typing improvements help, and it has a comfortable support runway. pytest 9.1.0 requires ≥3.10, so no conflict.
- **Test against 3.11, 3.12, 3.13, and 3.14** (3.14.6 is the current stable, released Oct 2025). The transpiler emits plain, conservative Python 3, so the *generated* code runs on an even wider range than the transpiler itself.

| Floor | Status | Use when |
|-------|--------|----------|
| 3.11 | **Recommended** | Default greenfield choice; best support runway + mature `match` |
| 3.10 | Acceptable | An institutional/classroom environment pins 3.10 |
| 3.9  | Avoid | Already EOL (Oct 2025); only if absolutely forced |

---

## Version Compatibility

| Package | Version | Requires Python | Notes |
|---------|---------|-----------------|-------|
| pytest | 9.1.0 | ≥3.10 | Matches recommended ≥3.11 floor with room to spare |
| hatchling | 1.30.1 | ≥3.10 | Build backend; pulled automatically at build time |
| setuptools (alt) | 82.0.1 | ≥3.9 | Only if you prefer setuptools over hatchling |
| `ast.unparse()` | stdlib | ≥3.9 | The hard floor for the chosen codegen strategy |
| `match`/`case` | stdlib | ≥3.10 | Convenient for token/node dispatch (not required) |
| Python (target) | 3.14.6 latest | — | 3.10 oldest non-EOL until Oct 2026; 3.11 recommended floor |

No known incompatibilities. The transpiler core has **zero runtime dependencies**, which eliminates the entire class of version-conflict problems for end users — `pip install atena-lang` cannot drag in a conflicting dependency.

---

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

---
*Stack research for: Atena teaching transpiler (Python 3, indentation-based source → Python 3 source)*
*Researched: 2026-06-13*
