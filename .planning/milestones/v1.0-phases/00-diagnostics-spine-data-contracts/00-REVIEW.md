---
phase: 00-diagnostics-spine-data-contracts
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/atena/errors.py
  - src/atena/tokens.py
  - src/atena/ast_nodes.py
  - src/atena/cli.py
  - src/atena/pipeline.py
  - src/atena/__main__.py
  - src/atena/__init__.py
  - tests/test_errors.py
  - tests/test_tokens.py
  - tests/test_ast_nodes.py
  - tests/test_cli.py
  - tests/test_imports.py
  - tests/conftest.py
  - pyproject.toml
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: resolved
resolution:
  resolved_at: 2026-06-13
  fixed: "CR-01, WR-01, WR-02, WR-03, WR-04, WR-05, WR-06 (1 Critical + 6 Warning)"
  fix_commits: "0b4dd3c, 7bd054b, fcec22e, 5e04098, b4cf3d5, a738609"
  tests_after: 58
  deferred: "IN-01..IN-05 (Info-only; not blocking)"
  note: "Traceback-escape findings verified fixed — binary file and directory-as-file now print plain-English messages, 0 tracebacks leak."
---

# Phase 0: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 0 delivers a diagnostics spine (`ErrorCollector`, `suggest`), pure-data
contracts (`tokens.py`, `ast_nodes.py`), and stub CLI/pipeline. All 52 tests
pass. The data contracts and `ErrorCollector` are clean and well-structured.
The dedup → sort → cap → format pipeline in `report()` is correct and the
`suggest()` case-priority logic works as specified.

The most serious finding is a **traceback escape in the CLI `run` path**
(`exec(compile(...))`) — this directly violates the project's hard constraint
that "no Python traceback may reach the learner." Although `transpile()` is a
stub today, the `run`-exec block is already-written, reachable production code
gated only on `result is not None`; the moment Phase 5 returns a string, a
learner's program with a runtime error will dump a raw Python traceback to the
terminal. Because this is the project's single most-emphasized invariant, I am
classifying it BLOCKER rather than deferring it as "future phase."

The remaining findings are robustness gaps in the CLI file-write path,
correctness edges in `suggest()`, a documentation/count inconsistency baked into
multiple comments, and test-hygiene issues (unrestored global mutation, unused
imports).

## Critical Issues

### CR-01: `run` path executes generated code with no traceback guard — violates the core no-traceback invariant

**File:** `src/atena/cli.py:117-138`
**Issue:**
The `try/except` block only wraps the call to `transpile()` (lines 118-127).
The subsequent code that acts on a successful result — including
`exec(compile(result, args.file, "exec"), {})` on line 138 — sits **outside**
any exception handler.

```python
try:
    result = transpile(source, args.file)
except NotImplementedError:
    ...
except BaseException as exc:
    print(_internal_error_message(exc), file=sys.stderr)
    sys.exit(1)

# result-handling block is OUTSIDE the try -> unguarded
if result is not None:
    if args.command == "build":
        ...
    else:
        exec(compile(result, args.file, "exec"), {})  # noqa: S102
```

CLAUDE.md states the absolute constraint: *"No Python stack traces ever reach
the learner"* and *"any unexpected internal exception is converted to a generic
friendly message."* The module docstring repeats this promise. But any runtime
exception raised **by the learner's own program** during `exec` (a division by
zero, an undefined name that slips past the analyzer, etc.) will propagate
uncaught, and Python will print a full traceback referencing the generated/temp
code — exactly the failure mode the language is designed to prevent. The
`compile()` call can likewise raise `SyntaxError` (with a traceback) if codegen
ever emits malformed Python.

This is reachable production code today (it is gated only on `result is not
None`, not on a phase flag) and becomes live the instant Phase 5's `transpile`
returns a string. The blast radius is the project's central value proposition,
so it must not ship as-is even within "stub scope."

**Fix:** Wrap the result-handling block (build-write and run-exec) so no raw
traceback escapes. Runtime errors from the learner's program need their own
plain-English surface; compile/IO errors need the internal-error fallback.

```python
if result is not None:
    if args.command == "build":
        out_path = os.path.splitext(args.file)[0] + ".py"
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(result)
        except OSError as exc:
            print(_file_error_message(out_path, exc), file=sys.stderr)
            sys.exit(1)
        print(f'Built "{os.path.basename(out_path)}".')
    else:
        try:
            code = compile(result, args.file, "exec")
            exec(code, {})  # noqa: S102
        except SystemExit:
            raise
        except BaseException as exc:  # learner program runtime error
            # surface as a plain-English runtime error (Phase 5 will define
            # the exact message); never let a Python traceback escape.
            print(_internal_error_message(exc), file=sys.stderr)
            sys.exit(1)
```

(Phase 5 should refine the `run` failure path into a learner-facing runtime
error rather than the internal-error message, but even the interim form must
not leak a traceback.)

## Warnings

### WR-01: `build` file-write has no error handling — traceback on unwritable target

**File:** `src/atena/cli.py:131-135`
**Issue:**
The `build` branch opens the output path for writing with no `try/except`:

```python
out_path = os.path.splitext(args.file)[0] + ".py"
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write(result)
```

If the output directory is read-only, the disk is full, or the path collides
with an existing directory, `open()`/`write()` raises `OSError` and a raw
traceback reaches the learner. The CLI carefully guards the *read* path
(`_read_file`, `_file_error_message`) but leaves the symmetric *write* path
unguarded. This is the same invariant as CR-01 but on the `build` verb; called
out separately because the fix differs (file-error message, not runtime-error
surface).

**Fix:** Wrap the write in `try/except OSError` and route through
`_file_error_message(out_path, exc)` with `sys.exit(1)` (see CR-01 fix snippet).

### WR-02: `suggest()` reports a case-only match even when a strictly better same-case fuzzy match exists

**File:** `src/atena/errors.py:123-132`
**Issue:**
The case-only check runs to completion **before** the fuzzy check and returns on
the first case-insensitive hit. If the candidate list contains both a same-case
near-match and a different-case exact-ish match, the user can be told "match
capitalization" when the real problem was a typo. Example:

```python
suggest("scor", ["score", "SCOR"])
# -> 'Did you mean "SCOR"? Names must match capitalization exactly.'
# but the learner almost certainly meant the same-case "score" (typo'd one char)
```

Here `"SCOR"` matches `"scor"` case-insensitively and is returned, even though
`"score"` is the more plausible same-case suggestion. The case-only branch also
returns the *first* candidate in iteration order on ties, which is arbitrary.
For a teaching tool, a misleading "fix your capitalization" hint when the issue
is a typo is a real UX defect.

**Fix:** Prefer an exact same-case-ignoring match only when no closer same-case
fuzzy match exists, or restrict the case-only path to candidates that differ
*only* by case from `name` (i.e. `name.lower() == candidate.lower()` is already
that, but choose the best fuzzy match among same-case candidates first). A
pragmatic ordering: run `get_close_matches` first; if the best fuzzy match
differs from `name` only by case, emit the capitalization note; otherwise emit
the plain "Did you mean" form.

### WR-03: `suggest()` exact-match guard is case-sensitive and misses the duplicate-key reality of candidate sets

**File:** `src/atena/errors.py:120-121`
**Issue:**
`if name in candidates: return None` treats the candidate list as a membership
set, but callers are documented to build it as
`list(ATENA_KEYWORDS) + known_variable_names`, which can contain duplicates and
is order-sensitive. More importantly, the exact-match short-circuit uses `in`
(case-sensitive) while the very next block does case-insensitive matching — so
`suggest("show", ["show"])` returns `None` (correct) but the function silently
assumes candidates are unique and pre-validated. If a future caller passes a
candidate list where `name` appears with different casing only, behavior is
defined but the interaction between the three checks is fragile and untested for
the duplicate/order case.

**Fix:** Document the precondition explicitly (candidates may contain
duplicates; first exact same-case match wins) and add a test covering
`suggest("x", ["x", "X", "xx"])` to pin the contract. Low risk but worth a test
to prevent regressions as callers evolve.

### WR-04: `_read_file` collapses all non-FileNotFound `OSError` into `PermissionError`, producing a misleading message

**File:** `src/atena/cli.py:63-65` and `cli.py:76`
**Issue:**
Any `OSError` that is not `FileNotFoundError`/`PermissionError` (e.g.
`IsADirectoryError`, `UnicodeDecodeError` is not an OSError but a decode of a
binary file would surface differently) is re-raised as `PermissionError`, and
the user is told *"make sure the file isn't locked."* For
`IsADirectoryError` (`atena run somedir/`) the learner is told the file is
locked, which is wrong and confusing. The mapping conflates distinct failure
causes under one inaccurate message.

**Fix:** Either widen `_file_error_message` to detect `IsADirectoryError`
(`"... is a folder, not a file"`) or keep the generic catch but phrase the
fallback message cause-neutrally (e.g. *"I couldn't open '{filename}'."*)
rather than asserting a lock.

### WR-05: Non-UTF-8 source files raise `UnicodeDecodeError` from `_read_file`, escaping as a traceback

**File:** `src/atena/cli.py:56-65`
**Issue:**
`open(path, encoding="utf-8").read()` raises `UnicodeDecodeError` on a non-UTF-8
file. `UnicodeDecodeError` is a `ValueError`, **not** an `OSError`, so it is not
caught by the `except OSError` arm in `_read_file`, nor by the
`except (FileNotFoundError, PermissionError)` arm in `main()`. It propagates as
a raw traceback — another breach of the no-traceback invariant, triggerable by
simply pointing `atena` at a file with non-UTF-8 bytes.

**Fix:** Catch `UnicodeDecodeError` (or `ValueError`) in `_read_file` or
`main()` and surface a plain-English message such as *"I couldn't read
'{filename}' — it doesn't look like a text file."*

### WR-06: Tests C-7 and C-8 mutate global `sys.argv` without restoring it

**File:** `tests/test_cli.py:172` and `test_cli.py:215`
**Issue:**
Both tests assign `sys.argv = ["atena", "run", existing_atena_file]` directly
inside the test body. Unlike `sys.stderr` (patched via `with patch(...)`),
`sys.argv` is mutated globally and never restored. This leaks state into any
later test in the same process that reads `sys.argv` (and makes test order
significant). The suite passes today only because no subsequent in-process test
depends on `sys.argv`, but this is a latent flaky-test hazard.

**Fix:** Use `monkeypatch.setattr(sys, "argv", [...])` (the fixture is already
injected) so pytest restores it automatically, or wrap in
`with patch.object(sys, "argv", [...])`.

## Info

### IN-01: Keyword-count comments are internally contradictory ("18" vs 19)

**File:** `src/atena/tokens.py:94` and `src/atena/errors.py` (docstring lists)
**Issue:**
`tokens.py:94` states *"Full set from REQUIREMENTS.md LEX-06 (18 keywords)"*
immediately above a dict that actually contains 19 entries, and the test
`test_T5` / `test_s10` both carry comments explaining the "18 was an off-by-one"
correction. The stale "18" comment will mislead the next reader who trusts the
comment over counting the dict.

**Fix:** Update the `tokens.py:94` comment to "19 keywords" to match the data
and the corrected tests.

### IN-02: `ATENA_KEYWORDS` (errors.py) and `KEYWORDS` (tokens.py) duplicate the keyword list as two sources of truth

**File:** `src/atena/errors.py:88-92` and `src/atena/tokens.py:97-117`
**Issue:**
The 19 keywords are hand-maintained in two places with two different shapes
(a `list[str]` in errors.py, a `dict[str, TokenType]` in tokens.py). The
errors.py docstring deliberately forbids importing tokens.py to avoid circular
imports, which is a reasonable design choice — but it means a future keyword
addition must be made in both files or the two drift apart silently. There is no
test asserting the two lists agree.

**Fix:** Acceptable as-is given the stated no-import constraint, but add a single
cross-check test (in a test module that may import both) asserting
`set(ATENA_KEYWORDS) == set(KEYWORDS)` so drift is caught immediately.

### IN-03: Unused `import sys` / `import pytest` in data-contract tests

**File:** `tests/test_tokens.py:8,10` and `tests/test_ast_nodes.py:8,10`
**Issue:**
`test_tokens.py` imports `sys` and `pytest` but uses neither. `test_ast_nodes.py`
imports `pytest` but uses only `sys` (in `test_A6`). Dead imports add noise and
will trip a linter (ruff F401) when one is added per CLAUDE.md's tooling notes.

**Fix:** Remove the unused imports.

### IN-04: `__init__.py` is completely empty — no package version or docstring

**File:** `src/atena/__init__.py:1`
**Issue:**
The package `__init__.py` is zero bytes. The project version is declared in
`pyproject.toml` (`0.1.0`) but there is no `__version__` attribute on the
package, which is the conventional discoverability point and is commonly asserted
by smoke tests / `--version` flags later. Not a defect for Phase 0 scope, but
worth a docstring at minimum.

**Fix (optional):** Add a module docstring and optionally
`__version__ = "0.1.0"` (or derive it via `importlib.metadata.version`).

### IN-05: `exec(..., {})` uses an empty globals dict — builtins are auto-injected but intent is implicit

**File:** `src/atena/cli.py:138`
**Issue:**
`exec(compile(result, ...), {})` relies on Python silently inserting
`__builtins__` into the empty globals dict. This is correct behavior but the
intent (full builtins available to generated code vs. a sandboxed subset) is
undocumented. For a transpiler that runs learner code, whether builtins are
restricted is a security-relevant decision that should be explicit, even if the
answer for v1 is "full builtins." Note: generated code is trusted output of the
transpiler, so this is informational, not a sandbox vulnerability today.

**Fix (optional):** Add a comment stating the globals/builtins policy for
generated code, to be revisited in Phase 5.

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
