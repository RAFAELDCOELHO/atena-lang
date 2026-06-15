---
phase: 04-code-generator
plan: "01"
subsystem: codegen
tags: [tdd, red-phase, codegen, parser, dot-write]
dependency_graph:
  requires:
    - 03-04-SUMMARY.md
  provides:
    - CodeGenerator skeleton (src/atena/codegen.py)
    - test_codegen.py RED stubs (tests/test_codegen.py)
    - parser dot-write support (src/atena/parser.py)
  affects:
    - 04-02-PLAN.md (GREEN phase — implements against these failing tests)
tech_stack:
  added: []
  patterns:
    - "Dynamic attribute _dot_target on Assign dataclass for dot-write without modifying ast_nodes.py"
    - "CodeGenerator dispatch via getattr(self, _emit_{NodeType}, _emit_default)(node)"
    - "On-demand helper emission tracked via _used_helpers set[str]"
    - "_mangle() uses keyword.iskeyword() — no hardcoded list"
key_files:
  created:
    - src/atena/codegen.py
    - tests/test_codegen.py
    - tests/fixtures/.gitkeep
  modified:
    - src/atena/parser.py
    - tests/test_parser.py
decisions:
  - "Dot-write implemented via Assign(name='') + dynamically-set _dot_target=DotAccess(...) — avoids modifying ast_nodes.py (locked contract)"
  - "keyword mangling test uses 'pass' (valid Atena variable name, Python keyword) not 'class' (caught by parser Python-ism redirect before codegen)"
  - "test_G3_zero_error_gate passes by design — it verifies the gate contract without calling generate()"
metrics:
  duration: "~30 min"
  completed: "2026-06-14T20:02:11Z"
  tasks_completed: 2
  files_modified: 5
---

# Phase 4 Plan 1: TDD RED Phase — Parser Dot-Write + CodeGenerator Skeleton

Parser dot-write assignment and CodeGenerator class skeleton with 16 failing test stubs across G1/G2/G3/Gx layers.

## What Was Built

### Task 1: Parser Dot-Write Fix (`student.grade = 10`)

Added `_parse_dot_assignment()` to `src/atena/parser.py`:

- New dispatch branch in `_dispatch_statement()` detects `IDENTIFIER + DOT` before the existing `IDENTIFIER + ASSIGN` branch.
- `_parse_dot_assignment()` consumes `IDENTIFIER DOT FIELD ASSIGN` and parses the RHS expression.
- Produces `Assign(name="", value=rhs)` with `node._dot_target = DotAccess(...)` set dynamically.
- Codegen will detect via `hasattr(node, "_dot_target")` — no changes to `ast_nodes.py` required.
- Added `test_dot_write_assignment` to `tests/test_parser.py` — written RED (fails before impl), then GREEN. Full 72-test parser suite still passes.

### Task 2: CodeGenerator Skeleton + test_codegen.py Stubs

**`src/atena/codegen.py`:**
- Module docstring documenting the Phase 4 contract (analyzed Program → Python 3 via ast.unparse, D-01 strategy A).
- Imports: stdlib `ast`, `keyword`, `re` + all 22 node types from `atena.ast_nodes`. Never imports `lexer`, `parser`, `analyzer`, or `errors`.
- `_mangle(name)` — trailing-underscore mangling using `keyword.iskeyword()`.
- `_ATENA_INDEX_SRC` and `_ATENA_CONCAT_SRC` — locked helper bodies.
- `CodeGenerator.__init__`: sets `_program`, `_used_helpers: set[str]`, `_loop_counter: int`. No `ErrorCollector` field.
- `generate()` — raises `NotImplementedError` (skeleton).
- `_emit()` — dispatch via `getattr(self, f"_emit_{type(node).__name__}", self._emit_default)`.
- `_emit_default()` — raises `TypeError` with "internal Atena bug" message.
- Stub `_emit_*` methods for all 22 node types — each raises `NotImplementedError`.

**`tests/test_codegen.py`:**
- 16 test stubs across four layers: G1 (6 golden snapshot), G2 (3 execution), G3 (4 self-check/edge), Gx (3 cross-req).
- `_generate(source)` pipeline helper chains Lexer→Parser→SemanticAnalyzer→CodeGenerator.
- RED gate confirmed: 15 failed, 1 passed (`test_G3_zero_error_gate` passes by design — it verifies the gate contract without ever calling `generate()`).

**`tests/fixtures/`:** Created with `.gitkeep` placeholder.

## Deviations from Plan

**1. [Rule 1 - Bug] Keyword mangling test uses 'pass' not 'class'**
- Found during: Task 2
- Issue: The plan specified `test_G3_keyword_mangling_class` testing `class = 5`, but `class` is caught by the parser's Python-ism redirect (`"Atena doesn't have classes..."`) before it ever reaches codegen. The test would fail for the wrong reason — the error comes from the parser, not from a codegen assertion.
- Fix: Changed to `test_G3_keyword_mangling_pass` using `pass = 5`. `pass` is a Python keyword (`keyword.iskeyword("pass") == True`) but is NOT in Atena's 19-keyword set, so it passes through the parser as a valid Atena variable name and reaches codegen where mangling must occur.
- Files modified: `tests/test_codegen.py`

## Verification Results

```
pytest tests/test_parser.py -k "dot_write" -v       → PASSED (1 test)
pytest tests/test_parser.py                          → 72 passed
pytest tests/test_codegen.py --tb=no -q              → 15 failed, 1 passed (RED confirmed)
pytest tests/ --ignore=tests/test_codegen.py -q      → 201 passed
from atena.codegen import CodeGenerator; print('ok') → import OK
forbidden imports check (Lexer/Parser/SemanticAnalyzer/ErrorCollector in CodeGenerator source) → NONE FOUND
dot-write manual verification                        → dot-write OK
```

## Commits

| Hash | Message |
|------|---------|
| `72fa7b3` | `feat(04-01): add dot-write assignment support to parser` |
| `a68c292` | `test(04-01): RED phase — CodeGenerator skeleton + test_codegen.py stubs` |

## Self-Check: PASSED

Files verified to exist:
- `src/atena/codegen.py` — present, imports succeed
- `tests/test_codegen.py` — present, 16 stubs, 15 failing
- `tests/fixtures/.gitkeep` — present
- `src/atena/parser.py` — modified with dot-write support
- `tests/test_parser.py` — modified with `test_dot_write_assignment`

Commits verified in git log: `72fa7b3` and `a68c292` both present.
