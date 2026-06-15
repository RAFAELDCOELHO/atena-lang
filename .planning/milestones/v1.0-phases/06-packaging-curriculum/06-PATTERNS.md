# Phase 6: Packaging & Curriculum - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 7 new/modified files + 8-9 example rungs
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pyproject.toml` | config | — | `pyproject.toml` (current) | exact (extend in place) |
| `README.md` | docs | — | `tests/test_cli.py` (CLI surface) + `src/atena/cli.py` (verbs) | role-match |
| `examples/01-show.atena` … `examples/08-dicts.atena` | curriculum | — | `examples/school.atena` | exact (same voice/syntax) |
| `examples/school.atena` | curriculum | — | already exists; read-only capstone | — |
| `tests/test_examples.py` | test | request-response | `tests/test_cli.py` (C-18 + subprocess+input) + `tests/test_codegen.py` (G2_school_execution_with_canned_stdin) | exact |

## Pattern Assignments

---

### `pyproject.toml` (config, extend in place)

**Analog:** `pyproject.toml` (the current file)

**Current state** (full file, lines 1-20):
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "atena-lang"
version = "0.1.0"
description = "Atena: a teaching language that transpiles to Python 3"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
atena = "atena.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/atena"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

**What to ADD (D-10, D-11):**

```toml
[project]
name = "atena-lang"
version = "1.0.0"                          # bump 0.1.0 → 1.0.0 (D-10)
description = "Atena: a teaching language that transpiles to Python 3"
readme = "README.md"                       # NEW — hatchling auto-populates PyPI long-desc
license = { file = "LICENSE" }            # NEW — MIT file already exists
authors = [{ name = "RAFAELDCOELHO" }]    # NEW — matches LICENSE copyright line
keywords = ["teaching", "education", "programming", "transpiler", "language"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Education",
    "Topic :: Education",
    "Topic :: Software Development :: Interpreters",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "License :: OSI Approved :: MIT License",
]
requires-python = ">=3.11"
dependencies = []                          # KEEP — zero runtime deps constraint
```

**Do NOT add** `[project.urls]` unless a real GitHub URL is confirmed — avoids fabricated metadata.

**Keep unchanged:**
```toml
[project.scripts]
atena = "atena.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/atena"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

---

### `README.md` (docs, full rewrite)

**Analog — CLI surface to document:** `src/atena/cli.py`

**Exact verbs and flags confirmed from `cli.py` (lines 32-50, 179-248):**
```python
# Two subcommands and their exact help strings:
_run_parser   = _subparsers.add_parser("run",   help="Transpile and run an Atena program")
_build_parser = _subparsers.add_parser("build", help="Transpile an Atena program to Python")
_build_parser.add_argument("--show", action="store_true",
                           help="Print generated Python 3 source to stdout")

# No --version flag was added in Phase 5. bare `atena` prints help and exits 0.
# If args.command is None: _parser.print_help(); sys.exit(0)
```

**Key behavioral facts for README accuracy:**
- `atena run file.atena` — transpiles and executes in memory; Atena line numbers preserved in runtime errors
- `atena build file.atena` — writes `file.py` alongside the source, prints `Built "file.py".`
- `atena build --show file.atena` — also prints generated Python 3 to stdout (the "see what Atena wrote" feature)
- `atena` (no args) — prints help, exits 0
- `atena --help` / `atena run --help` — standard argparse help, exit 0
- NO `--version` flag in Phase 5 — do not document it unless confirmed added in Phase 6

**Error message voice (DIAG-04) — mirror this voice in README:**
```python
# from cli.py lines 82-91
f'I couldn\'t find a file called "{filename}".'
f'"{filename}" is a folder, not a file.'
f"Something went wrong inside Atena — this isn't your fault."
```

**Keyword list for cheatsheet — from `tokens.py` KEYWORDS dict (lines 97-117):**
```python
# The canonical 19 keywords (LEX-06):
"show", "ask", "if", "else", "while", "repeat", "times",
"and", "or", "not", "function", "return",
"add", "to", "remove", "from", "length",
"true", "false"
```

**README section outline (D-05 through D-09):**
1. Hook — 2-3 sentences: what Atena is, who it is for, that `build --show` reveals Python (D-08)
2. Install — `pip install .` (users), `pip install -e .` (contributors) (D-11)
3. First program — write `hello.atena`, run it, see the output (D-05 "install-to-first-program")
4. The two verbs — `atena run`, `atena build`, `atena build --show` (D-05)
5. When you make a mistake — tiny buggy program + exact Atena error output (D-07). Good candidates:
   - undefined variable: `I don't know what "xyz" is.`
   - zero-index: `Lists in Atena start at 1, not 0.`
6. Language basics cheatsheet — `show`, `ask`, `if`/`else`, `while`, `repeat N times`, `function`/`return`, lists (1-indexed!), dicts (dot access), automatic string coercion (D-05)
7. Examples — pointer to `examples/` ladder (D-05)
8. For teachers — one-paragraph framing of the 9 rungs as a classroom curriculum, one concept ≈ one ~50-minute class (D-09)

**Voice rule (D-06):** Write "you" not "the user". Plain English. No jargon. Match the encouraging, first-person error voice of `cli.py` and `errors.py`.

---

### `examples/01-show.atena` … `examples/08-dicts.atena` (curriculum, standalone rungs)

**Analog (style, voice, syntax):** `examples/school.atena` (the capstone)

**Capstone patterns to adopt (all 55 lines of `school.atena`):**

Style rules extracted from `school.atena`:
- One statement per line, no semicolons, no colons, no braces in control flow
- Comments use `#` prefix — teaching comments name what the line does
- Variables are short, meaningful English words (`name`, `grades`, `total`, `avg`, `verdict`)
- String concatenation: `"label: " + variable` (triggers automatic coercion)
- 1-indexed list access: `grades[1]`, `grades[i]` (never `grades[0]`)
- Dict literal: `{name = "waiting", passed = false}` (not JSON-style braces)
- Dict read/write via dot: `student.name`, `student.passed = true`
- Function definition: `function name(param)` then indented body
- `ask` for input: `name = ask "Enter student name: "`
- `show` for output: `show "text " + variable`
- `while` loop: `while condition` then indented body
- `repeat N times` loop: `repeat 2 times` then indented body
- `add value to list` / `remove value from list`
- `length(list)` for count

**Rung list (D-13, D-02 — one new idea per file, ~8-9 rungs, honor roadmap concept order):**

| File | Concept Introduced | New Ideas | ask/input? |
|------|-------------------|-----------|------------|
| `01-show.atena` | Output (`show`) | `show` with strings and numbers | No |
| `02-ask.atena` | Input (`ask`) | `ask` + variable + showing back | Yes — 1 input |
| `03-variables.atena` | Variables & arithmetic | assign, `+`, `-`, `*`, `/`, `show` result | No |
| `04-conditionals.atena` | `if` / `else` | branch on a comparison | No |
| `05-while.atena` | `while` loop | counted loop with `while` | No |
| `06-repeat.atena` | `repeat N times` | counted loop with `repeat` | No |
| `07-functions.atena` | Functions & `return` | `function`, `return`, call | No |
| `08-lists.atena` | Lists | `[]`, `add`, `remove`, `length`, 1-indexing | No |
| `09-dicts.atena` | Dicts | `{}`, dot read, dot write | No |
| `examples/school.atena` | Capstone | All of the above combined | Yes — 1 input |

**File header comment pattern (D-03) — copy this structure:**
```atena
# Concept: show (output)
# This file shows how to print text and numbers to the screen.
# Run it with: atena run 01-show.atena

show "Hello, world!"
show 42
# You can show text and numbers together — Atena handles the conversion
show "The answer is: " + 42
```

**Key teaching notes by rung:**

`02-ask.atena` (interactive — requires canned stdin in tests):
```atena
# Concept: ask (input)
# ask pauses the program and waits for the learner to type something.
name = ask "What is your name? "
show "Hello, " + name
```

`08-lists.atena` (must demonstrate 1-indexing explicitly):
```atena
# Lists in Atena are numbered starting at 1, not 0.
# grades[1] is the first item, grades[2] is the second.
show "First grade: " + grades[1]
```

`09-dicts.atena` (must show dot access for both read and write):
```atena
person = {name = "Ana", age = 20}
# Read a value using dot notation:
show person.name
# Update a value using dot notation:
person.age = 21
show "Updated age: " + person.age
```

---

### `tests/test_examples.py` (test, request-response, NEW FILE)

**Primary analog:** `tests/test_cli.py` — specifically **C-18** (lines 475-491, the school.atena subprocess+canned-stdin pattern):

```python
def test_c18_school_atena_smoke() -> None:
    """C-18: atena run examples/school.atena with canned stdin 'Ana' exits 0 and prints 'Welcome, Ana'."""
    result = subprocess.run(
        [sys.executable, "-m", "atena", "run", "examples/school.atena"],
        capture_output=True,
        text=True,
        input="Ana\n",
    )
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}. stderr: {result.stderr!r}"
    )
    assert "Welcome, Ana" in result.stdout, (
        f"Expected 'Welcome, Ana' in stdout. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr, (
        f"Python traceback must not appear. Got: {result.stdout + result.stderr!r}"
    )
```

**Secondary analog:** `tests/test_codegen.py` — **G2_school_execution_with_canned_stdin** (lines 171-197), which shows the `subprocess.run(..., input="Ana\n", ...)` / `timeout=10` / `capture_output=True, text=True` idiom:

```python
result = subprocess.run(
    [sys.executable, "-c", python_src],
    input="Ana\n",
    capture_output=True,
    text=True,
    timeout=10,
)
assert result.returncode == 0, f"Generated Python crashed:\n{result.stderr}"
assert "Ana" in result.stdout, (...)
```

**Also see:** `tests/test_cli_runtime_lines.py` lines 32-49 — `_run_capture` helper that uses `patch.object(sys, "argv", ...)` + in-process `main()`. Use the **subprocess style** (not monkeypatch) for example tests because:
- Examples run via the installed `atena` entry point (`python -m atena run ...`)
- Subprocess style proves the actual installed pipeline, matching ROADMAP criterion #1

**Imports pattern** (copy from `test_cli.py` lines 8-21):
```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
```

**`run_cli` helper pattern** (copy from `test_cli.py` lines 28-34):
```python
def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI as a subprocess with the given arguments."""
    return subprocess.run(
        [sys.executable, "-m", "atena", *args],
        capture_output=True,
        text=True,
    )
```

**Pattern for non-interactive rungs** (no `ask` — e.g. `01-show.atena`, `03-variables.atena`, etc.):
```python
def test_example_01_show_runs_to_completion() -> None:
    """01-show.atena exits 0 and produces output (no interactive input needed)."""
    result = run_cli("run", "examples/01-show.atena")
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert result.stdout.strip() != "", (
        f"Expected some output. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr
```

**Pattern for interactive rungs** (with `ask` — e.g. `02-ask.atena`, `school.atena`):
```python
def test_example_02_ask_runs_to_completion() -> None:
    """02-ask.atena exits 0 when given canned stdin 'Alice'."""
    result = subprocess.run(
        [sys.executable, "-m", "atena", "run", "examples/02-ask.atena"],
        capture_output=True,
        text=True,
        input="Alice\n",
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Alice" in result.stdout, (
        f"Expected the input name echoed back. Got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stdout + result.stderr
```

**Pattern for school.atena capstone** (mirrors C-18 exactly, tests multiple outputs):
```python
def test_example_school_atena_capstone() -> None:
    """school.atena (capstone) exits 0 with canned stdin and prints expected greeting."""
    result = subprocess.run(
        [sys.executable, "-m", "atena", "run", "examples/school.atena"],
        capture_output=True,
        text=True,
        input="Ana\n",
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Expected exit 0. stderr: {result.stderr!r}"
    )
    assert "Welcome, Ana" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
```

**Three-assert rule** (from every C-* test in `test_cli.py`): each test asserts:
1. `returncode == 0`
2. expected content in `result.stdout`
3. `"Traceback" not in result.stdout + result.stderr`

---

## Shared Patterns

### No-traceback assertion
**Source:** `tests/test_cli.py` — every test, e.g. lines 62-64
**Apply to:** every test in `tests/test_examples.py`
```python
assert "Traceback" not in result.stdout + result.stderr, (
    f"Python traceback must not appear. Got: {result.stdout + result.stderr!r}"
)
```

### subprocess.run with canned stdin
**Source:** `tests/test_cli.py` lines 475-491 (C-18) and `tests/test_codegen.py` lines 183-189
**Apply to:** any example rung that contains an `ask` statement
```python
result = subprocess.run(
    [sys.executable, "-m", "atena", "run", "examples/XX-name.atena"],
    capture_output=True,
    text=True,
    input="canned_value\n",
    timeout=10,
)
```

### subprocess.run without stdin (non-interactive)
**Source:** `tests/test_cli.py` lines 28-34 (`run_cli` helper)
**Apply to:** all non-`ask` example rungs
```python
result = subprocess.run(
    [sys.executable, "-m", "atena", *args],
    capture_output=True,
    text=True,
)
```

### Error voice — "I couldn't …" / "isn't your fault"
**Source:** `src/atena/cli.py` lines 82-110
**Apply to:** README error-showcase section (D-07)
The README must show this voice so learners recognize it. Quote the actual error strings from `cli.py`, e.g.:
- `I couldn't find a file called "hello.atena".`
- `Error on line 2: I don't know what "xyz" is. Did you forget to create it?`

### Teaching comment header
**Source:** established in D-03 decisions; `school.atena` already uses inline `#` comments
**Apply to:** all rung `.atena` files (01-09)
Every rung opens with:
```atena
# Concept: <name>
# <One sentence on what this teaches>
# Run it with: atena run NN-name.atena
```

### Zero runtime dependencies invariant
**Source:** `pyproject.toml` line 10: `dependencies = []`
**Apply to:** `pyproject.toml` (keep as-is when adding metadata)
Never add items to `dependencies`. `hatchling` is a build-time dep only (automatically pulled by `pip install`, never a runtime dep).

---

## No Analog Found

All Phase 6 files have analogs in the existing codebase. No entries in this table.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All files have analogs |

---

## Key Behavioral Facts for Implementation (do not re-derive)

**CLI verbs that actually exist in `cli.py`:**
- `atena run FILE` — exec in memory, runtime errors → plain English
- `atena build FILE` — writes `FILE.py`, prints `Built "FILE.py".`
- `atena build --show FILE` — writes `FILE.py` AND prints Python to stdout
- `atena` (no args) — prints help, exits 0
- NO `--version` flag as of Phase 5 end. Version bump in `pyproject.toml` is not auto-exposed via CLI unless Phase 6 adds it explicitly.

**19 keywords (from `tokens.py` KEYWORDS dict):**
`show ask if else while repeat times and or not function return add to remove from length true false`

**school.atena is 55 lines**, uses `ask` (interactive), all major constructs. The canned stdin for tests is `"Ana\n"` and the expected output contains `"Welcome, Ana"` (confirmed by C-18 in `test_cli.py`).

**Execution test file location:** `tests/test_examples.py` (new file). It does NOT go in `tests/conftest.py` — conftest is for fixtures only (confirmed: conftest is currently just a stub with a docstring and no fixture functions).

**Example files live in `examples/`** (already contains `school.atena`). New numbered rungs: `01-show.atena` through `09-dicts.atena`.

---

## Metadata

**Analog search scope:** `tests/`, `examples/`, `src/atena/`, `pyproject.toml`
**Files scanned:** 12 source files + 2 planning docs
**Pattern extraction date:** 2026-06-15
