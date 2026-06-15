---
phase: 04-code-generator
reviewed: 2026-06-14T21:03:16Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/atena/codegen.py
  - src/atena/parser.py
  - src/atena/analyzer.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: warnings_only
resolved:
  - id: CR-01
    resolved_at: 2026-06-14
    fix_commit: 37b41b7
    test_commit: d86aed9
    note: >
      _emit_FunctionCall now calls _mangle(func_name) on the general return
      path. Call sites for keyword-named user functions emit the mangled name
      matching the definition site. test_CR01_keyword_function_call_mangled
      confirms no SyntaxError and correct execution.
  - id: CR-02
    resolved_at: 2026-06-14
    fix_commit: 37b41b7
    test_commit: d86aed9
    note: >
      visit_Assign detects the dot-write form (node._dot_target set) and
      visits _dot_target via visit_DotAccess before visiting node.value.
      This fires the same undefined-name check the dot-READ path already
      performs. test_CR02_dot_write_undefined_object_errors confirms the
      plain-English error; test_CR02_dot_write_defined_object_no_error
      confirms defined-object dot-writes remain error-free.
  - id: WR-01
    resolved_at: 2026-06-14
    fix_commit: 6cf6c40
    test_commit: 6048f87
    quick_task: 260614-pmc
    note: >
      Removed "str" from _BUILTIN_HELPERS so source-level str() errors with
      plain-English "I don't know a function called str yet." Also moved the
      _coerced idempotency guard before child-visits in visit_BinOp so that
      analyzer-injected FunctionCall("str",...) nodes are never re-validated
      against the function table on re-analysis. Full suite 253 tests GREEN;
      school.expected.py golden fixture byte-identical.
open_issues:
  - WR-02 (arithmetic safety-net regression)
  - WR-03 (GEN-05 fallback / no top-level wrap)
  - WR-04 (parser messages for nested dot-write / == typo)
---

# Phase 4: Code Review Report

**Reviewed:** 2026-06-14T21:03:16Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the three Phase 4 source files: the new `codegen.py` (the `CodeGenerator`
that maps the analyzed AST to Python via `ast.unparse` + post-patches), the parser
change adding dot-write assignment, and the analyzer change making `-`/`*`/`/`
return `"number"`.

The canonical golden path (`examples/school.atena`) generates cleanly and exercises
the full construct set — nested-`repeat` loop-var uniqueness, on-demand
`_atena_index`/`_atena_concat` helpers, dot-write, str-coercion, and list ops all
work. The full suite (248 tests) is green. **But green tests do not validate
correctness here:** none of the existing fixtures exercise the failing paths below,
and two of them violate the project's headline invariant — "no Python traceback ever
reaches the learner."

**Update 2026-06-14:** CR-01 and CR-02 are RESOLVED (fix commit `37b41b7`,
test commit `d86aed9`). Full suite is 251 tests, 0 failures. 4 Warnings remain open.

**Update 2026-06-14 (quick 260614-pmc):** WR-01 is RESOLVED (fix commit `6cf6c40`,
test commit `6048f87`). Full suite is 253 tests, 0 failures. 3 Warnings remain open.

Two BLOCKERs were proven by end-to-end execution:
1. Keyword-named functions are mangled at the **definition** site but NOT at the
   **call** site, so any program calling a function whose name is a Python keyword
   (e.g. `lambda`, `pass`, `global`, `del`, `try`, `with`, `yield`, …) makes
   `generate()` raise an uncaught `SyntaxError` from the GEN-05 self-check.
2. The new dot-write parser path lets `obj.field = value` pass analysis even when
   `obj` was never defined, emitting `obj["field"] = value` → runtime `NameError`.
   The dot-**read** path correctly errors on the same input; the dot-write path
   introduced the asymmetry.

No structural findings block was provided.

## Critical Issues (RESOLVED)

### CR-01 [RESOLVED — commit 37b41b7]: Function-call site does not mangle Python-keyword names (definition mangles, call does not)

**File:** `src/atena/codegen.py:407` (vs definition mangle at `:334`)
**Issue:** `_emit_FunctionDef` mangles the function name (`name=_mangle(node.name)`,
line 334), but `_emit_FunctionCall` emits the **raw** name
(`func=ast.Name(id=func_name, ...)`, line 407) with no `_mangle()`. A large set of
Python keywords are NOT Atena keywords and are NOT redirected as python-isms, so they
pass lexer/parser/analyzer as legal Atena identifiers and can be used as function
names: `False, None, True, as, assert, async, await, break, continue, del, except,
finally, global, in, is, lambda, nonlocal, pass, raise, try, with, yield`.

Proven end-to-end:
```
function pass(n)
    return pass(n)
```
emits
```python
def pass_(n):
    return pass(n)   # call NOT mangled
```
which the GEN-05 `ast.parse()` self-check (codegen.py:175) rejects with an **uncaught
`SyntaxError`**. Because `generate()` does not catch it (correctly — GEN-05 failure is
defined as an internal bug), this propagates as a raw Python traceback to whatever
calls the generator. That directly violates the project invariant "no Python
traceback ever reaches the learner," and it is reachable from ordinary user input.

Note: the `length` → `len` mapping (line 396) and `_atena_*` helpers are safe — a user
can never define `length` (it is an Atena keyword, rejected at the function-name
position by the parser), and the helper names are not Python keywords. Identifier,
parameter, assign-target, ask-target, and list-target sites are all already mangled
consistently; only the function-call name is missed.

**Fix:** Mangle the call name on the general path, after the `length` and helper
special-cases:
```python
# in _emit_FunctionCall, replace the final return:
return ast.Call(
    func=ast.Name(id=_mangle(func_name), ctx=ast.Load()),
    args=[self._emit(a) for a in node.args],
    keywords=[],
)
```
`_mangle("_atena_concat")` / `_mangle("_atena_index")` are no-ops (not keywords), so
the line-403 helper-tracking branch is unaffected. Add a targeted fixture that defines
and calls a keyword-named function (e.g. `pass`) and asserts the generated Python both
`ast.parse`s and executes.

### CR-02 [RESOLVED — commit 37b41b7]: Dot-write to an undefined object passes analysis, emits code that crashes at runtime

**File:** `src/atena/parser.py:670-714` (`_parse_dot_assignment`) +
`src/atena/analyzer.py:128-174` (`visit_Assign`)
**Issue:** The new dot-write feature builds an `Assign` node with `name=""` and a
dynamically attached `_dot_target` (a `DotAccess`). `visit_Assign` only does
`self._visit(node.value)` (the RHS) — it never visits `node._dot_target`, so the
target identifier (`obj` in `obj.field = value`) is never checked for being defined.

Proven end-to-end:
```
nope.grade = 10
```
passes analysis (`is_empty() == True`) and emits
```python
nope["grade"] = 10
```
which crashes at runtime with `NameError: name 'nope' is not defined` — a leaked
Python traceback for the learner.

This is an asymmetry the feature introduced: the dot-**read** path
(`show nope.grade`) correctly produces the plain-English error
`I don't know what "nope" is yet. Did you forget to create it first?` because
`visit_DotAccess` visits its target. The dot-write path bypasses that check entirely.

**Fix:** Have `visit_Assign` detect the dot-write form and validate the target. Either
visit the attached `_dot_target` so the existing `visit_DotAccess` undefined-name check
fires:
```python
def visit_Assign(self, node: Assign) -> str:
    if getattr(node, "_dot_target", None) is not None:
        self._visit(node._dot_target)   # validates the target object exists
        self._visit(node.value)
        return "unknown"
    if node.name.startswith("_atena_"):
        ...
```
(Visiting the read-context `DotAccess` is semantically fine for an existence check.)
Add a fixture asserting `nope.grade = 10` produces a plain-English "I don't know what
nope is" error rather than runnable code.

## Warnings

### WR-01 [RESOLVED — commit 6cf6c40, quick 260614-pmc]: User-defined `function str(x)` silently breaks analyzer-injected `str()` coercion

**File:** `src/atena/codegen.py:384-410` (`_emit_FunctionCall`) +
`src/atena/analyzer.py:295` (`_BUILTIN_HELPERS` pass-through)
**Issue:** `str` is not an Atena keyword, so a user may write `function str(x)`. The
analyzer permits the redefinition (visit_FunctionCall step 2 only passes `str` through
when it is not in `self._functions`), and the generator emits `def str(x): ...` plus
calls to `str(...)` verbatim. But the analyzer's `+`-coercion injects bare
`FunctionCall(name="str", ...)` nodes, which the generator emits as plain `str(...)`.
Both resolve to the **user's** `str`, not Python's builtin.

Proven end-to-end:
```
function str(x)
    return 999
msg = "score: " + 10
show msg
```
emits valid Python (passes GEN-05) but crashes at runtime:
`TypeError: can only concatenate str (not "int") to str`, because the injected
`str(10)` calls the user function (returning `999`) instead of stringifying.

Not introduced by this diff, but it is a generator-level emission concern surfaced by
reviewing `codegen.py`: the injected coercion and a user function share the same emitted
name. **Fix:** Inject coercion under a reserved, mangle-proof name the user cannot
collide with (e.g. analyzer injects `FunctionCall(name="_atena_str", ...)` and the
generator maps `_atena_str` → builtin `str`, or emits `__builtins__`-qualified `str`).
Alternatively, reject user redefinition of `str` in the analyzer (treat `str` like the
reserved `_atena_` names). Minimum: add a fixture documenting the current behavior so
the gap is tracked.

### WR-02: Analyzer arithmetic change turns a non-crashing program into a runtime traceback

**File:** `src/atena/analyzer.py:353-357` (added `if node.op in ("-", "*", "/")`)
**Issue:** The diff makes `-`/`*`/`/` return `"number"` unconditionally. This correctly
fixes the common case (`2 + (3 * 4)` now type-checks as `number + number` instead of
wrongly stringifying to `"212"`). But it also changes behavior for *mistyped* programs:
previously an arithmetic sub-expression returned `"unknown"`, so an enclosing `+` routed
through `_atena_concat` (which never crashes — it stringifies both sides). Now it emits
raw Python `+`.

Proven regression:
```
a = 2
b = "x"
show a + b * 3
```
Pre-diff: `b * 3` → "unknown" → `a + (b*3)` routes to `_atena_concat` → runs, prints
`"2xxx"` (wrong but no traceback). Post-diff: `b * 3` → "number" → `a + b * 3` emits raw
`+` → runtime `TypeError: unsupported operand type(s) for +: 'int' and 'str'` — a leaked
Python traceback, the exact thing the project forbids.

The root gap (no type-checking of `*`/`-`/`/` operands — D-04) is pre-existing v1.0
scope, so this is a Warning, not a Blocker. But the diff removed the `_atena_concat`
safety net that was incidentally preventing the traceback for these compound forms.
**Fix:** Either (preferred) type-check `*`/`-`/`/` operands and emit a plain-English
"can't do arithmetic on text" error when an operand is `str`/`bool`, mirroring the `+`
coercion table; or only return `"number"` when both operands are known-numeric and fall
back to the previous behavior otherwise. Add an execution test for `a + b * 3` with `b`
a string and assert a plain-English error (not a `TypeError`).

### WR-03: GEN-05 self-check failure escapes as an uncaught exception (no friendly fallback)

**File:** `src/atena/codegen.py:175` (`ast.parse(python_source)`)
**Issue:** The GEN-05 self-check raises `SyntaxError` on any internal codegen bug
(triggered today by CR-01). The class docstring says this "is never caught or turned
into an ErrorCollector entry" — which is the right intent (it is an internal bug, not a
user error) — but combined with CR-01 it means *user input* can drive the generator to
raise a raw Python `SyntaxError`. There is no last-resort wrapper converting an
unexpected internal failure into the generic friendly message the project mandates
("Wrap the top level so any unexpected internal exception is converted to a generic
friendly message" — CLAUDE.md).

That top-level wrap is nominally Phase 5's job (`pipeline.py`/CLI), so this is a Warning
rather than a Blocker for this phase. **Fix:** Primary fix is CR-01 (so the self-check
stops firing on reachable input). Defense-in-depth: ensure the Phase-5 driver wraps
`generate()` so any escaping `SyntaxError`/`TypeError` becomes the generic friendly
message, and add a regression test that the keyword-name programs from CR-01 never reach
`ast.parse`.

### WR-04: Misleading error message for nested dot-write and bare dot expressions

**File:** `src/atena/parser.py:691-694` (`_parse_dot_assignment` `_expect(ASSIGN, …)`)
**Issue:** Dispatch routes any `IDENTIFIER . …` to `_parse_dot_assignment`, which hard-
commits to `IDENTIFIER . IDENTIFIER =`. For inputs that are not flat dot-writes the
error misdescribes the situation:
- `student.grade.inner = 10` (nested write, explicitly out of v1.0 scope) →
  `Expected "=" after the field name in a dot assignment.` — points at the second `.`,
  not "nested field writes aren't supported."
- `student.grade == 10` (a comparison typed where assignment was meant) → same
  `Expected "="` message rather than the existing `=` vs `==` teaching redirect.

For a teaching language whose value prop is plain-English errors, these mislead.
**Fix:** After consuming `IDENTIFIER . IDENTIFIER`, branch on the next token: if it is
another `.`, emit "Atena can only set one field at a time (student.grade = …), not
nested fields." If it is `==`, reuse the existing `=` vs `==` redirect. Keep the current
message only for the genuine "missing `=`" case.

## Info

### IN-01: Post-unparse regex patches operate on raw source text, not the AST

**File:** `src/atena/codegen.py:182-198` (`_patch_double_quotes`, `_patch_blank_lines`)
**Issue:** Both patches are regexes over the unparsed string. They are safe today
because Atena v1.0 has only double-quoted single-line strings and integers, and
`ast.unparse` switches to double quotes whenever a string contains a single quote
(so `r"'([^'\\]*)'"` never matches an apostrophe-bearing literal), and `r"\n(def )"`
only matches a top-level `def`. But this couples correctness to incidental `unparse`
behavior; multi-line strings or escape-bearing content (a v2 concern) could surprise it.
The GEN-05 self-check guards against producing unparseable output, not against producing
*wrong-but-parseable* output. **Fix:** No change required for v1.0; add a comment noting
the dependency on `unparse`'s quote/line behavior, and revisit if string features expand.

### IN-02: Dead/defensive branches that current grammar cannot reach

**File:** `src/atena/codegen.py:158-161` (`isinstance(result, list)` in `generate`),
`src/atena/codegen.py:344` (`... or [ast.Pass()]`)
**Issue:** `_emit_as_stmt` never returns a `list` (only `_emit_Program`, reached via
`_emit`, does), so the `isinstance(result, list)` branch in the top-level loop is
unreachable for a well-formed Program. Likewise a parsed `FunctionDef` always has a
non-empty body (the parser errors on an empty block), so `or [ast.Pass()]` cannot fire.
Both are harmless defensive code. **Fix:** Optional — drop or annotate as intentional
defensive guards so future readers don't assume they are exercised.

### IN-03: Existing fixtures cover only happy paths for the new features

**File:** `tests/fixtures/dict_dot_write.atena` (and the absence of negative fixtures)
**Issue:** The dot-write fixture only tests an object that is defined first, and there is
no fixture for keyword-named functions or arithmetic-on-text. The 248-test green suite
therefore gives false confidence on exactly the paths that fail in CR-01, CR-02, and
WR-02. **Fix:** Add negative/edge fixtures: (a) `nope.grade = 10` → plain-English
undefined error; (b) `function pass(n) … pass(n)` → executes; (c) `a + b * 3` with `b` a
string → plain-English error. These will fail until CR-01/CR-02/WR-02 are fixed and lock
the regressions out.

---

_Reviewed: 2026-06-14T21:03:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
