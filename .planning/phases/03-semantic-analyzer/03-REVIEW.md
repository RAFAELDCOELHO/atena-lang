---
phase: 03-semantic-analyzer
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/atena/analyzer.py
  - tests/test_analyzer.py
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

The SemanticAnalyzer is well-organized and its happy paths are covered by 27 passing
tests. However, adversarial probing surfaced two correctness BLOCKERs and several
robustness gaps that the test suite does not exercise:

1. **Coercion injection is not idempotent.** The analyzer advertises idempotency
   (`index_converted` guard) and the suite tests it for index rewrites, but the
   `str()`-coercion rewrite in `visit_BinOp` has no such guard. Running the analyzer
   twice over the same tree silently changes the emitted code (`"a" + str(1)` becomes
   `_atena_concat("a", str(1))`). The pipeline contract says nodes are mutated in
   place — any second pass, re-analysis, or shared sub-tree breaks this.

2. **`add`/`remove` statement targets are never validated.** `add 1 to mylist` and
   `remove 1 from mylist` against an undefined list produce zero errors, contradicting
   the project's defined-before-use semantics enforced everywhere else (this is the
   same class of error as the undefined-variable check that `visit_Identifier`
   implements). The learner gets a raw Python `NameError` at runtime — a stack trace,
   which the project's core value statement explicitly forbids.

Beyond these, internal helper names (`_atena_concat`, `_atena_index`, `length`,
`str`) are reachable as ordinary user identifiers/functions and silently shadow or
collide with the analyzer's injected nodes, and duplicate function definitions are
silently accepted. The test suite tests only the constructs it implements; the
untested surface (list mutation statements, re-analysis, name collisions, duplicate
defs) is where the defects live.

All findings were reproduced empirically against the current code.

## Critical Issues

### CR-01: `str()` coercion injection is not idempotent — second analyze pass corrupts the AST

**File:** `src/atena/analyzer.py:287-305`
**Issue:**
`visit_IndexAccess` carefully guards against double-rewrite with the `index_converted`
flag (lines 337-339), and `test_Ax_index_converted_idempotent` proves it. But the
parallel coercion rewrite in `visit_BinOp` has **no idempotency guard**. After the
first pass, `"a" + 1` becomes `BinOp("+", StringLiteral("a"), FunctionCall("str",[1]))`.
On a second pass the right operand (`str(...)`) now infers type `"unknown"`, so the
short-circuit at lines 265-273 fires and rewrites the **entire BinOp in place into**
`FunctionCall("_atena_concat", [...])`. The tree shape silently changes.

Reproduced:
```
After 1st analyze: BinOp(op='+'), right=FunctionCall('str')
After 2nd analyze: FunctionCall(name='_atena_concat')   # tree shape CHANGED
```

This matters because: (a) the module docstring and CLAUDE.md describe an in-place
mutating analyzer whose passes must be stable; (b) the suite already establishes
idempotency as a contract for the index path, so coercion violating it is an
inconsistency that will bite any re-run (e.g. the driver retrying, or a future
multi-pass design). It is the same defect class the index guard was written to prevent.

**Fix:** Add an idempotency guard equivalent to `index_converted`. Either skip
coercion when the operand is already a `FunctionCall("str", ...)`, or short-circuit
when the BinOp's operands are already analyzer-injected. Simplest robust fix — guard
the str-wrap and the `_atena_concat` conversion on whether the node has already been
processed:
```python
# In visit_BinOp, before the unknown short-circuit and table lookup:
if getattr(node, "_coerced", False):
    return "str"  # or the previously-inferred type
...
# after a successful coerce_right / coerce_left:
node._coerced = True   # mark so re-analysis is a no-op
```
Alternatively, recognize an already-injected `str()` operand as type `"str"` instead
of `"unknown"` so the second pass takes the no-op `("str","str")` branch. Add a test
mirroring `test_Ax_index_converted_idempotent` for the coercion path.

### CR-02: `add`/`remove` statement targets bypass the defined-before-use check — leaks a Python traceback

**File:** `src/atena/analyzer.py:391-397`
**Issue:**
`visit_ListAdd` and `visit_ListRemove` visit only `node.value` and never check that
`node.target` (the list name) is defined or is actually a list. Every other name use
in the analyzer is validated (`visit_Identifier`, `visit_FunctionCall`), but the
`target` field of `add … to X` / `remove … from X` is a bare `str` that is never
looked up in any scope.

Reproduced:
```
add 1 to mylist        -> errors empty? True   (mylist never defined)
remove 1 from mylist   -> errors empty? True
```

Because the analyzer reports no error, the driver gates codegen open, emits Python
`mylist.append(1)`, and the learner sees a raw `NameError: name 'mylist' is not
defined` traceback at runtime. This directly violates the project's stated core value
("never sees a Python stack trace — only plain-English errors that name the line")
and the defined-before-use rule enforced for ordinary variables.

**Fix:** Look up the target in the active scope and report a plain-English error when
it is missing (mirroring `visit_Identifier` Case 4, including the `suggest()` hint).
For example:
```python
def visit_ListAdd(self, node: ListAdd) -> str:
    self._visit(node.value)
    self._check_list_target(node)   # new helper
    return "unknown"

def _check_list_target(self, node) -> None:
    scope = self._locals if self._locals is not None else self._globals
    if node.target in scope or (self._locals is not None and node.target in self._functions):
        return
    candidates = list(scope.keys()) + list(ATENA_KEYWORDS)
    hint = suggest(node.target, candidates)
    msg = f'I don\'t know a list called "{node.target}" yet. Did you forget to create it first?'
    if hint:
        msg = f'{msg} {hint}'
    self._errors.add(node.line, msg, node.source_line)
    scope[node.target] = "unknown"   # poison to suppress cascade
```
Apply the identical check in `visit_ListRemove`. Add error-path tests for both.

## Warnings

### WR-01: Built-in helper names (`length`, `str`, `_atena_concat`, `_atena_index`) are unguarded — user definitions silently shadow them and skip all checks

**File:** `src/atena/analyzer.py:206`
**Issue:**
`visit_FunctionCall` treats any call to `{"length", "str", "_atena_concat",
"_atena_index"}` as an always-reachable, never-arity-checked built-in (`return
"unknown"` at line 207). A user who defines `function str(x)` and calls `str(5)`, or
defines `function length(a,b)` and calls it with the wrong arity, has their call
silently pass-through with **no arity check and no defined-before-called check**.

Reproduced:
```
function str(x)\n  return x\nshow str(5)         -> errors empty? True (arity never checked)
function _atena_concat(a)\n...\n_atena_concat(1,2,3) -> errors empty? True
```

The internal helper names `_atena_concat`/`_atena_index` are also reachable as plain
identifiers (`_atena_index = 5` is accepted, line was confirmed), so a user variable
can collide with the analyzer's injected helper at codegen time, producing wrong
output or a runtime crash.

**Fix:** Two parts. (1) For the user-facing built-ins (`length`, `str`), if the name
is also present in `self._functions` (user redefined it), prefer the user definition
and run the normal arity/defined checks — or reject the redefinition with a
plain-English "that name is built in" error. (2) The internal helpers
(`_atena_concat`, `_atena_index`) should never be writable by users; reserve the
`_atena_` prefix in `visit_Assign`/`visit_Identifier`/`visit_FunctionDef` and reject
it with a clear message, so injected nodes can never collide with user names.

### WR-02: Duplicate function definitions are silently accepted; arity table overwritten

**File:** `src/atena/analyzer.py:173-174`
**Issue:**
`visit_FunctionDef` does `self._functions[node.name] = len(node.params)` and
`self._globals[node.name] = "function"` with no check for an existing definition. A
second `function f(...)` silently overwrites the first's arity, so calls written
against the first definition's arity now error against the second's (or vice versa),
producing a confusing "expects N values" message that points the learner at the call
site, not the real mistake (two functions with the same name).

Reproduced:
```
function f(a)\n  return a\nfunction f(a,b)\n  return a\nf(1)
-> Error: "f" expects 2 values, but you gave 1.   (no redefinition error)
```

**Fix:** Detect redefinition and emit a plain-English error at the second `function`
header, e.g. `'A function called "f" is already defined above. Pick a different name.'`,
naming `node.line`/`node.source_line`. Keep the first registration so downstream
arity checks stay stable.

### WR-03: Stale `op`/`left`/`right` fields persist after `BinOp.__class__ = FunctionCall` mutation

**File:** `src/atena/analyzer.py:270-272`
**Issue:**
The in-place class swap sets `node.name`/`node.args` but never deletes the original
`op`, `left`, `right` attributes. The object now answers `hasattr(node, "op") == True`
with value `"+"` while reporting `type(node).__name__ == "FunctionCall"`. Confirmed:
```
node class: FunctionCall ; has op attr (stale)? True '+' ; has left attr? True
```
The Phase-4 generator reportedly reads only `name`/`args`, so this is latent rather
than active — but it is a correctness landmine: any future visitor, debug `repr`, or
generator pass that does `isinstance(x, FunctionCall)` then trusts the dataclass's
declared fields will see ghost attributes that do not belong to `FunctionCall`. The
parallel `str()`-coercion path (lines 289-294, 299-304) correctly builds a fresh
`FunctionCall` instead of mutating `__class__`; only the `_atena_concat` path uses the
fragile swap.

**Fix:** Prefer constructing a fresh `FunctionCall` and reassigning through the parent
(consistent with the str()-coercion path), or, if in-place swap must stay, delete the
stale fields after the swap:
```python
node.__class__ = FunctionCall
node.name = "_atena_concat"
node.args = [orig_left, orig_right]
for stale in ("op", "left", "right"):
    if hasattr(node, stale):
        delattr(node, stale)
```

### WR-04: Poisoned undefined name keeps type `"unknown"` even after a later valid assignment, suppressing correct coercion

**File:** `src/atena/analyzer.py:439`
**Issue:**
When an undefined name is used, `visit_Identifier` poisons it as `"unknown"` in scope
to suppress cascades (correct intent). But because the analyzer is single-pass and
top-down, a name used before assignment that is later assigned a known type keeps the
poisoned `"unknown"`. Subsequent `+` uses then route through `_atena_concat` instead
of the precise `str()` coercion the type would dictate.

Reproduced:
```
show ghost          # poisons ghost = unknown (correctly errors)
ghost = 5           # would be number
y = "a" + ghost     # routes via _atena_concat (unknown), not str() coercion
```
This is mostly masked because the first use already produced an error (so the run is
aborted before codegen). It becomes a real defect only if poison policy or error
gating changes. Flagging as WARNING because it couples two concerns (cascade
suppression vs. type tracking) in one mutable cell.

**Fix:** Let a real assignment (`visit_Assign`) overwrite a poisoned `"unknown"` with
the freshly inferred type (it already writes `scope[node.name] = inferred`, so this is
mostly fine for assignment). The residual risk is for names used-then-assigned; if
that ordering should still coerce correctly, separate "poisoned/undefined" tracking
from the type cell so a later assignment cleanly re-types. At minimum, add a comment
documenting the single-pass limitation.

### WR-05: `DotAccess` and `DictLiteral` keys are never validated; dynamic field/key typos slip to runtime

**File:** `src/atena/analyzer.py:318-321, 387-389`
**Issue:**
`visit_DotAccess` visits only the target and never checks `node.name`; `visit_DictLiteral`
visits values but never the keys. Atena is a teaching language where the value
proposition is plain-English compile-time errors. A field-name typo on a dict
(`student.naem`) cannot be caught statically without a type system, so this is
partially inherent — but it means `student.naem` produces a runtime `KeyError`/
`AttributeError` traceback, which the project forbids. Whether this is in scope for
v1.0 depends on the spec; flagging so it is a conscious decision, not an oversight.

**Fix:** If dict field validation is out of scope for v1.0, document it explicitly
(comment + a note in the phase summary) so it is not mistaken for a covered case. If
in scope, the generator should emit a guarded access helper (like `_atena_index`) that
raises a plain-English error on a missing key rather than a Python traceback.

### WR-06: `_visit_default` swallows unknown node types as `"unknown"` with no diagnostic

**File:** `src/atena/analyzer.py:99-104`
**Issue:**
`_visit` falls back to `_visit_default` (returns `"unknown"`) for any node type that
lacks a `visit_<Type>` method. Every one of the 22 node types currently has a visitor,
so this is dormant — but it means a future AST node added without a corresponding
visitor will be silently skipped (no traversal of its children, no error), which can
hide entire subtrees from analysis (e.g. an un-visited child containing an undefined
name or an un-coerced `+`). For a collect-all-errors analyzer, silent skipping is a
correctness hazard.

**Fix:** Make the fallback explicit. Either raise an internal (non-user-facing)
assertion in development builds, or log/track that an unhandled node type was
encountered so the gap surfaces in tests rather than in production. At minimum, ensure
`_visit_default` still recurses into common child fields, or add a test that asserts
every node type has a dedicated visitor.

## Info

### IN-01: `visit_Program` and several leaf visitors are dead/unreachable as written

**File:** `src/atena/analyzer.py:110-111`
**Issue:** `visit_Program` returns `"unknown"` and is never dispatched — `analyze()`
iterates `self._program.statements` directly rather than calling `self._visit(program)`.
It is harmless dead code but invites confusion (a maintainer may "fix" Program handling
there expecting it to run).
**Fix:** Either remove `visit_Program`, or route `analyze()` through
`self._visit(self._program)` and move the statement loop into `visit_Program` for
consistency with the visitor pattern used everywhere else.

### IN-02: Magic string set for built-ins duplicated as a literal inside the hot path

**File:** `src/atena/analyzer.py:206`
**Issue:** The built-in name set `{"length", "str", "_atena_concat", "_atena_index"}`
is an inline literal inside `visit_FunctionCall`. The same names appear in `visit_BinOp`
and `visit_IndexAccess` as injected `FunctionCall(name=...)` constructions. The
"reserved/injected name" concept is spread across three sites with no single source of
truth, which is how WR-01's collision gap arose.
**Fix:** Hoist a module-level constant, e.g.
`_BUILTIN_HELPERS = frozenset({"length", "str"})` and
`_INTERNAL_HELPERS = frozenset({"_atena_concat", "_atena_index"})`, and reference both
everywhere (including the future name-collision guard from WR-01).

### IN-03: Test suite has no negative/idempotency coverage for the coercion path or list-mutation statements

**File:** `tests/test_analyzer.py` (whole file)
**Issue:** The two BLOCKERs (CR-01, CR-02) and three WARNINGs (WR-01, WR-02) all live
in code paths the suite never exercises: there is no test that re-analyzes a coercion
result (only `test_Ax_index_converted_idempotent` covers the index path), no test for
`add`/`remove` against an undefined list, no test for built-in shadowing, and no test
for duplicate function definitions. The green suite gave false confidence that these
paths were sound.
**Fix:** Add error-path and idempotency tests for each gap as the fixes land:
re-analyze a `str + number` program and assert the tree is unchanged; `add 1 to
undefinedlist` asserts a plain-English error; `function str(x)` / duplicate
`function f` assert the expected diagnostics.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
