# Phase 5: CLI Runtime & Pipeline Integration - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 4 (pipeline.py, cli.py, test_cli.py, examples/school.atena)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/atena/pipeline.py` | service/driver | transform (batch, 4-phase sequential) | `src/atena/codegen.py` (CodeGenerator.generate) | role-match |
| `src/atena/cli.py` | controller | request-response | `src/atena/cli.py` itself (existing scaffold) | exact (extend in place) |
| `tests/test_cli.py` | test | request-response + monkeypatch | `tests/test_cli.py` itself (C-1…C-14 to extend) | exact (extend in place) |
| `examples/school.atena` | fixture | batch | `examples/school.atena` itself (already present) | exact |

---

## Pattern Assignments

### `src/atena/pipeline.py` (service/driver, transform)

**Analog:** `src/atena/codegen.py` — the only existing file that calls all four phase
modules in a coordinated sequence. `pipeline.py` is a coordination layer, not a
class; its shape is a plain function that instantiates phases and threads a shared
`ErrorCollector` through them.

**Imports pattern** — mirrors the four data-contract imports named in CONTEXT.md:

```python
from __future__ import annotations

from atena.errors import ErrorCollector
from atena.lexer import Lexer
from atena.parser import Parser
from atena.analyzer import SemanticAnalyzer
from atena.codegen import CodeGenerator
```

**Phase-constructor pattern** — every existing phase uses the same two-arg signature
`(input, errors)` → method call. From `src/atena/lexer.py` lines 19-31 (Lexer) and
`src/atena/analyzer.py` lines 76-80 (SemanticAnalyzer):

```python
# Lexer(source, errors).tokenize()
# Parser(tokens, errors).parse()
# SemanticAnalyzer(program, errors).analyze()
# CodeGenerator(program).generate()   ← no errors arg; only called when errors.is_empty()
```

**Between-phases gating pattern** — gate between phases, never inside them.
`ErrorCollector.is_empty()` is the canonical gate from `src/atena/errors.py` lines 39-41:

```python
def is_empty(self) -> bool:
    """Return True if no errors have been recorded yet."""
    return len(self._records) == 0
```

The driver shape implied by CONTEXT.md + ARCHITECTURE.md:

```python
def transpile(source: str, filename: str) -> str | None:
    errors = ErrorCollector()

    tokens = Lexer(source, errors).tokenize()
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return None

    program = Parser(tokens, errors).parse()
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return None

    program = SemanticAnalyzer(program, errors).analyze()
    if not errors.is_empty():
        print(errors.report(), file=sys.stderr)
        return None

    # GEN-03: codegen runs ONLY when errors.is_empty()
    return CodeGenerator(program).generate()
```

**Error report pattern** — `ErrorCollector.report()` returns the full formatted block
(dedup, sort, cap at 10, canonical template). From `src/atena/errors.py` lines 43-84:

```python
result = "\n\n".join(blocks)  # blank-line-separated error blocks
if overflow_count > 0:
    result += f"\n…and {overflow_count} more. Fix some and run again to see the rest."
return result
```

Individual block format (line 76):
```python
f"Error on line {r.line}: {r.message}\n  → {r.source_line}"
```

**Runtime-error message format** (D-05) — runtime errors must match the same canonical
template. The planner should produce messages like:
```
Error on line 12: that list has 3 items, so there's no position 5.
  → show grades[5]
```

**Helper body strings** — from `src/atena/codegen.py` lines 81-91 (the exact bodies
that will be exec'd at runtime, so the runtime error catcher must know what they raise):

```python
_ATENA_INDEX_SRC: str = """\
def _atena_index(i):
    if i < 1:
        raise IndexError("List positions in Atena start at 1.")
    return i - 1
"""

_ATENA_CONCAT_SRC: str = """\
def _atena_concat(a, b):
    return str(a) + str(b)
"""
```

Note: `_atena_index` currently raises `IndexError` with **no line number** — D-06
requires the runtime catch layer (or a modified helper) to attach the Atena line.

---

### `src/atena/cli.py` (controller, request-response) — extend existing scaffold

**Analog:** `src/atena/cli.py` itself. Phase 5 fills in the exec-error branch and
wires the real `transpile()`. All other structure is already correct — preserve it.

**Imports pattern** — existing, lines 14-20:

```python
from __future__ import annotations

import argparse
import os
import sys

from atena.pipeline import transpile
```

**Argparse subcommand pattern** — existing, lines 26-38:

```python
_parser = argparse.ArgumentParser(
    prog="atena",
    description="Atena language transpiler",
)
_subparsers = _parser.add_subparsers(dest="command")

_run_parser = _subparsers.add_parser("run", help="Transpile and run an Atena program")
_run_parser.add_argument("file", metavar="FILE", help=".atena source file")

_build_parser = _subparsers.add_parser(
    "build", help="Transpile an Atena program to Python"
)
_build_parser.add_argument("file", metavar="FILE", help=".atena source file")
```

**File error helper** — existing, lines 74-89 (keep verbatim — CLI-05 already done):

```python
def _file_error_message(path: str, exc: Exception) -> str:
    filename = os.path.basename(path)
    if isinstance(exc, FileNotFoundError):
        return f'I couldn\'t find a file called "{filename}".'
    if isinstance(exc, IsADirectoryError):
        return f'"{filename}" is a folder, not a file.'
    if isinstance(exc, UnicodeDecodeError):
        return (
            f'I couldn\'t read "{filename}"'
            " — it doesn't look like a text file."
        )
    return f'I couldn\'t read "{filename}".'
```

**Internal error helper** — existing, lines 92-108 (keep verbatim — D-04: internal
bugs only, not learner runtime errors):

```python
def _internal_error_message(exc: BaseException) -> str:
    line = getattr(exc, "atena_line", None)
    if isinstance(line, int):
        return (
            f"Something went wrong inside Atena near line {line}"
            " — this isn't your fault."
            " Please share your program so we can fix it."
        )
    return (
        "Something went wrong inside Atena"
        " — this isn't your fault."
        " Please share your program so we can fix it."
    )
```

**exec() run path** — existing scaffold, lines 155-164. Phase 5 replaces the
`_internal_error_message` call in the exec except-block with CLI-04 runtime translation:

```python
# EXISTING (to be refined):
try:
    code = compile(result, args.file, "exec")
    exec(code, {})  # noqa: S102
except SystemExit:
    raise
except BaseException as exc:  # learner program runtime error
    # Surface as a plain-English message (Phase 5 will refine this)
    print(_internal_error_message(exc), file=sys.stderr)
    sys.exit(1)
```

The planner should introduce a `_runtime_error_message(exc, source_lines)` function
(or inline dispatch) that:
1. Checks `type(exc)` against the curated catalog (D-03): `IndexError`, `ZeroDivisionError`,
   `KeyError`, `ValueError`.
2. Extracts the Atena line number via traceback inspection (D-07) and looks up the
   source line from the `source` string kept in scope.
3. Formats using the canonical `Error on line {N}: {message}\n  → {source_line}` template
   (D-05) — same format as compile-time errors.
4. Falls back to a gentle generic message (still no traceback, still line-numbered
   where possible) for uncurated exceptions.
5. Never routes learner errors through `_internal_error_message`.

**Build write path** — existing, lines 143-153 (keep verbatim — behavior already correct):

```python
if args.command == "build":
    out_path = os.path.splitext(args.file)[0] + ".py"
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(result)
    except OSError as exc:
        print(_file_error_message(out_path, exc), file=sys.stderr)
        sys.exit(1)
    print(f'Built "{os.path.basename(out_path)}".')
```

**Errors → stderr, output → stdout** — established by existing cli.py; all `print(...,
file=sys.stderr)` for errors, bare `print(...)` for normal program output.

**Transpile-errors path** — when `transpile()` returns `None` (errors collected), the
`result is not None` guard at line 143 already skips execution. Phase 5 must ensure
the error report was printed before `transpile()` returns `None` (pipeline.py owns that
print) and the CLI exits non-zero. The planner must close the gap: if `result is None`,
`sys.exit(1)`.

---

### `tests/test_cli.py` (test, request-response + monkeypatch) — extend existing suite

**Analog:** `tests/test_cli.py` itself — C-1…C-14 establish both test styles used for
all new tests. Never break existing tests; C-14 must be rewritten (D-04).

**Subprocess helper** — existing, lines 28-34. Use for all black-box CLI tests
(C-15 run-prints-output, C-16 build-emits-file, C-17 transpile-errors, school.atena
smoke test):

```python
def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "atena", *args],
        capture_output=True,
        text=True,
    )
```

**Subprocess test pattern** — existing, e.g. lines 81-91 (C-3). Assert returncode,
then assert substring in `result.stdout + result.stderr`:

```python
result = run_cli("run", "missing.atena")
assert result.returncode == 1
combined = result.stdout + result.stderr
assert 'I couldn\'t find a file called "missing.atena".' in combined
```

**Monkeypatch + sys.argv + captured stderr pattern** — existing C-7 (lines 151-191)
and C-14 (lines 382-413). Use for white-box tests that need to control `transpile()`
return values without subprocess overhead:

```python
import atena.cli as _cli
import io
from unittest.mock import patch

def _transpile_boom(source: str, filename: str) -> str | None:
    return "x = 1 / 0\n"

monkeypatch.setattr(_cli, "transpile", _transpile_boom)
monkeypatch.setattr(sys, "argv", ["atena", "run", existing_atena_file])

captured_stderr = io.StringIO()
with pytest.raises(SystemExit) as exc_info:
    with patch("sys.stderr", captured_stderr):
        _cli.main()

assert exc_info.value.code == 1
err_output = captured_stderr.getvalue()
assert "Traceback" not in err_output
assert "ZeroDivisionError" not in err_output
```

**Fixture for temporary .atena file** — existing, lines 37-43:

```python
@pytest.fixture()
def existing_atena_file(tmp_path: Path) -> str:
    f = tmp_path / "prog.atena"
    f.write_text("show 1\n")
    return str(f)
```

**C-14 rewrite target** — current assertion at line 405 must change:

```python
# CURRENT (must go RED first, then rewrite):
assert "Something went wrong inside Atena" in err_output

# NEW assertion (D-04): learner divide-by-zero → friendly runtime message
# Must NOT contain "Something went wrong inside Atena" (that's internal only)
# Must contain a plain-English runtime error message
# Must NOT contain "Traceback" or "ZeroDivisionError"
```

**Stdin passthrough for `ask`** — subprocess `input=` parameter passes canned stdin
for tests that exercise `ask`/`input()`. Pattern for school.atena smoke test:

```python
result = subprocess.run(
    [sys.executable, "-m", "atena", "run", "examples/school.atena"],
    capture_output=True,
    text=True,
    input="Ana\n",  # canned stdin for ask "Enter student name: "
)
assert result.returncode == 0
assert "Welcome, Ana" in result.stdout
```

**Platform-skip pattern** — existing C-10/C-13 (lines 253-257, 327-333). Mirror for
any Unix-only permission tests:

```python
@pytest.mark.skipif(sys.platform == "win32", reason="Unix file permissions not applicable on Windows")
@pytest.mark.skipif(os.getuid() == 0, reason="Root user can read any file; permission test is meaningless as root")
```

---

### `examples/school.atena` (fixture, batch)

**Analog:** itself — already present and complete (lines 1-55). No modification needed.
This file is the canonical end-to-end smoke fixture. It exercises: `ask`, variable
assignment, lists, dicts, function definitions, `show`, arithmetic (`/` → `ZeroDivisionError`
risk if denominator were 0), comparison, `if`/`else`, `while`, `repeat`, `add`/`remove`,
`length`, `_atena_index` (list[1], list[i]), `_atena_concat` (implicit through `+` with
mixed types), and dot-access.

The test harness must supply `input="Ana\n"` (or any name) via subprocess `input=` to
feed the `ask` prompt.

---

## Shared Patterns

### Error format (canonical — apply to ALL error output)
**Source:** `src/atena/errors.py` lines 75-76
**Apply to:** `pipeline.py` (compile-time errors) and `cli.py` (runtime errors in D-05)

```python
f"Error on line {r.line}: {r.message}\n  → {r.source_line}"
```

Runtime errors must produce the identical format, e.g.:
```
Error on line 12: that list has 3 items, so there's no position 5.
  → show grades[5]
```

### No-traceback rule (cross-cutting — apply to ALL exception catches)
**Source:** `src/atena/cli.py` lines 155-164 + test assertions throughout test_cli.py
**Apply to:** `cli.py` exec error branch, `pipeline.py` error reporting

Every `except` clause that could surface to the learner must:
1. Never call `raise` without catching and reformatting.
2. Never print a string containing `"Traceback"`, raw exception class names (`"ZeroDivisionError"`, `"IndexError"`, etc.), or `"NoneType"`.
3. Always exit non-zero when an error occurred.

### ErrorCollector injection (apply to pipeline.py + all phases)
**Source:** `src/atena/lexer.py` lines 19-21, `src/atena/analyzer.py` lines 76-78
**Apply to:** `pipeline.py` — one shared `ErrorCollector` instance threaded through all phases

```python
# Pattern: ErrorCollector injected, never global, never instantiated inside a phase
def __init__(self, ..., errors: ErrorCollector) -> None:
    self._errors = errors  # injected — never instantiate internally
```

### Errors → stderr, output → stdout (apply to cli.py + pipeline.py)
**Source:** `src/atena/cli.py` lines 127-128, 138-139, 162-163
**Apply to:** All user-visible output routing

```python
print(error_message, file=sys.stderr)   # errors
sys.exit(1)                              # non-zero on any error
print(program_output)                   # learner's program output → stdout
```

### Internal vs learner error distinction (apply to cli.py exec branch)
**Source:** `src/atena/cli.py` lines 92-108 (`_internal_error_message`)
**Apply to:** `cli.py` runtime error dispatch (D-04)

- `_internal_error_message` → genuine internal bugs only (transpiler crashes, `NotImplementedError`, unexpected exceptions from pipeline machinery).
- New `_runtime_error_message` (or inline dispatch) → learner's program's runtime errors (`IndexError`, `ZeroDivisionError`, `KeyError`, `ValueError`).
- The two paths must never overlap.

### Curated runtime error catalog (D-03, apply to cli.py runtime catch)
**Source:** CONTEXT.md §D-03 + `_ATENA_INDEX_SRC` in codegen.py lines 81-86
**Apply to:** `cli.py` exec except-block

| Python exception | Atena-friendly message pattern |
|---|---|
| `IndexError` (out of range, i >= 1) | `"that list has N items, so there's no position P."` |
| `IndexError` (from _atena_index, i < 1) | `"List positions start at 1, so there's no position 0 (or negative)."` |
| `ZeroDivisionError` | `"you tried to divide by zero — the denominator must not be 0."` |
| `KeyError` | `"that dictionary doesn't have a key called {key!r}."` |
| `ValueError` (from list.remove) | `"that item wasn't in the list, so it couldn't be removed."` |
| anything else | generic: `"while running your program, an error occurred on line N."` |

All messages: no raw class names, include `Error on line N:` prefix and `→ source_line` suffix.

---

## No Analog Found

All four files have close analogs in the codebase. No file requires fallback to
RESEARCH.md patterns only.

| File | Status |
|---|---|
| `src/atena/pipeline.py` | Analog: codegen.py's sequential phase orchestration + errors.py gating |
| `src/atena/cli.py` | Exact: itself (extend in place) |
| `tests/test_cli.py` | Exact: itself (extend in place, rewrite C-14) |
| `examples/school.atena` | Exact: itself (no modification needed) |

---

## Metadata

**Analog search scope:** `src/atena/`, `tests/`, `examples/`
**Files scanned:** cli.py, pipeline.py, errors.py, codegen.py, lexer.py, parser.py, analyzer.py, ast_nodes.py (header), test_cli.py, conftest.py, school.atena
**Pattern extraction date:** 2026-06-14
