---
phase: "00"
plan: "03"
subsystem: "data-contracts"
tags: [tokens, ast-nodes, dataclass, enum, tdd, pure-data]
dependency_graph:
  requires:
    - "00-01 (pip-installable package, stub modules exist)"
  provides:
    - "TokenType enum (19 members) — canonical token classification for the lexer"
    - "Token frozen dataclass (5 fields: type, value, line, col, source_line)"
    - "KEYWORDS dict (19 Atena keywords → TokenType.KEYWORD)"
    - "Node base dataclass + 22 concrete AST node dataclasses, all position-bearing"
    - "tests/test_tokens.py (7 tests) and tests/test_ast_nodes.py (7 tests)"
  affects:
    - "00-04 (errors.suggest() needs the KEYWORDS dict)"
    - "Phase 1 lexer — imports TokenType, Token, KEYWORDS"
    - "Phase 2 parser — imports all 22 AST node types"
    - "Phase 3 analyzer — mutates IndexAccess.index_converted, injects str() wrappers"
    - "Phase 4 generator — reads every AST node field"
tech_stack:
  added: []
  patterns:
    - "enum.Enum for TokenType (string values, 19 members)"
    - "@dataclass(frozen=True) for Token — immutable after lexer creates it"
    - "@dataclass (mutable) for all 22 AST nodes — analyzer rewrites nodes in place"
    - "field(default_factory=list) for all list-typed node fields (prevents shared mutable defaults)"
    - "field(default_factory=lambda: Node()) for all Node-typed fields with defaults"
    - "Node base carries line: int = 0 and source_line: str = '' — every subclass inherits positional fields"
key_files:
  created:
    - tests/test_tokens.py
    - tests/test_ast_nodes.py
  modified:
    - src/atena/tokens.py
    - src/atena/ast_nodes.py
decisions:
  - "TokenType uses string enum values (e.g. STRING='STRING') rather than auto() integers — values appear in repr() and are self-documenting in error output"
  - "Token is frozen=True — tokens are immutable after the lexer creates them; downstream phases read but never mutate tokens"
  - "AST nodes are mutable @dataclasses — the analyzer rewrites IndexAccess.index_converted and injects str() wrappers in place without rebuilding the tree"
  - "IndexAccess carries index_converted: bool = False — the idempotency guard prevents the analyzer from double-shifting an already-converted index (ARCHITECTURE.md Pattern 11)"
  - "Node base has line: int = 0 and source_line: str = '' with defaults — allows simple test construction (Program(statements=[], line=0)) without supplying source_line"
  - "KEYWORDS has 19 entries (not 18 as mistakenly stated in the plan <behavior> section) — LEX-06 is the authoritative source and lists 19 keywords [Rule 1 auto-fix]"
metrics:
  duration: "~8 min"
  completed: "2026-06-13"
  tasks: 2
  files_created: 2
  files_modified: 2
---

# Phase 00 Plan 03: Token + AST Node Data Contracts Summary

**One-liner:** Frozen Token dataclass with 19-member TokenType enum and KEYWORDS map, plus 22 mutable position-bearing AST node dataclasses — the pure-data inter-phase contracts every Atena pipeline stage imports.

## What Was Built

This plan implements the two pure-data modules that all four pipeline phases depend on.

### `src/atena/tokens.py`

Replaces the Plan 01 stub with a complete implementation:

- **`TokenType(enum.Enum)`** — 19 members with string values. Covers every token category from REQUIREMENTS.md LEX-01: STRING, NUMBER, IDENTIFIER, KEYWORD, OPERATOR, COMPARISON, ASSIGN, LPAREN, RPAREN, LBRACKET, RBRACKET, LBRACE, RBRACE, COMMA, DOT, NEWLINE, INDENT, DEDENT, EOF.
- **`Token`** — `@dataclass(frozen=True)` with 5 fields: `type: TokenType`, `value: str`, `line: int`, `col: int`, `source_line: str`. Frozen means mutation raises `FrozenInstanceError`. The `source_line` field lets any downstream phase produce "Error on line N: … → {source}" without re-reading the file (DIAG-01).
- **`KEYWORDS: dict[str, TokenType]`** — maps all 19 Atena reserved words to `TokenType.KEYWORD`. The lexer uses this for O(1) keyword/identifier distinction.

### `src/atena/ast_nodes.py`

Replaces the Plan 01 stub (which only had `Node` and `Program`) with the full node set:

- **`Node`** base dataclass — `line: int = 0`, `source_line: str = ""`. All concrete nodes inherit these positional fields.
- **22 concrete dataclasses**: Program, Assign, Show, Ask, If, While, Repeat, FunctionDef, Return, FunctionCall, BinOp, UnaryOp, ListLiteral, DictLiteral, IndexAccess, DotAccess, ListAdd, ListRemove, Identifier, NumberLiteral, StringLiteral, BoolLiteral.
- **`IndexAccess.index_converted: bool = False`** — idempotency guard: the analyzer sets True after rewriting 1→0; prevents double-shift on revisit (ARCHITECTURE.md Pattern 11).
- All list-typed fields use `field(default_factory=list)` to prevent shared mutable defaults.
- Zero non-stdlib imports in both modules (only `enum`, `dataclasses`).

### Tests

- **`tests/test_tokens.py`** — 7 tests covering: TokenType member count (T1), Token construction (T2), Token equality (T3), KEYWORDS["show"] (T4), KEYWORDS length (T5), user names not in KEYWORDS (T6), Token repr (T7).
- **`tests/test_ast_nodes.py`** — 7 tests covering: all 22 types importable (A1), Program construction (A2), BinOp construction (A3), Assign equality (A4), IndexAccess.index_converted default (A5), import isolation (A6), DictLiteral construction (A7).

## Verification Evidence

```
pytest tests/test_tokens.py tests/test_ast_nodes.py -v     → 14 passed, exit 0
pytest tests/ -v                                           → 31 passed, exit 0 (no regressions)
grep sibling imports in tokens.py/ast_nodes.py             → 0 (pure stdlib only)
python -c "Token(...).value = 'x'"                         → FrozenInstanceError (frozen confirmed)
python -c "import atena.ast_nodes; 'atena.errors' not in sys.modules" → isolation PASS
```

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| RED | Add failing token and ast_node contract tests | ae92323 | tests/test_tokens.py, tests/test_ast_nodes.py |
| GREEN | Implement TokenType, Token, KEYWORDS, and all 22 AST node dataclasses | 01216cc | src/atena/tokens.py, src/atena/ast_nodes.py, tests/test_tokens.py (T5 fix) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected KEYWORDS count from 18 to 19**

- **Found during:** GREEN phase, implementing KEYWORDS dict
- **Issue:** The plan's `<behavior>` section states "Test T-5: `len(KEYWORDS) == 18` (18 Atena keywords from LEX-06)", but REQUIREMENTS.md LEX-06 explicitly lists 19 keywords: "show, ask, if, else, while, repeat, times, and, or, not, function, return, add, to, remove, from, length, true, false". The plan has an internal inconsistency; LEX-06 is the authoritative source.
- **Fix:** Updated `test_T5_keywords_has_19_entries` to assert `len(KEYWORDS) == 19`. Implemented all 19 keywords in KEYWORDS dict. The test name was also updated to reflect the correct count.
- **Files modified:** `tests/test_tokens.py` (assertion and docstring), `src/atena/tokens.py` (all 19 keywords present)
- **Commit:** 01216cc

## TDD Gate Compliance

RED gate commit: ae92323 (`test(00-03): add failing token and ast_node contract tests`)
GREEN gate commit: 01216cc (`feat(00-03): implement TokenType, Token, KEYWORDS, and all 22 AST node dataclasses`)

Both gates present. No REFACTOR commit needed (implementation was clean on first pass).

## Known Stubs

None. All previously-stub content in `tokens.py` and `ast_nodes.py` is now fully implemented and tested.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. The only trust boundary is Token.source_line (read-only after construction via frozen=True — T-00-03-01 mitigated). No new threat surface beyond what the plan's STRIDE register covers.

## Self-Check: PASSED

- [x] `pytest tests/test_tokens.py tests/test_ast_nodes.py -v` exits 0, 14 tests PASSED
- [x] `pytest tests/ -v` exits 0, 31 tests PASSED (no regressions)
- [x] `TokenType` has exactly 19 members: `len(list(TokenType)) == 19`
- [x] `KEYWORDS` has exactly 19 entries: `len(KEYWORDS) == 19`
- [x] `Token` is frozen (`FrozenInstanceError` on mutation attempt)
- [x] All 22 AST node names importable from `atena.ast_nodes` in one import statement
- [x] `IndexAccess.index_converted` defaults to `False`
- [x] Zero sibling imports in `tokens.py` and `ast_nodes.py` (grep count = 0)
- [x] `from atena.ast_nodes import Program` does not add `atena.errors` or `atena.tokens` to `sys.modules`
- [x] Commit `ae92323` exists (RED gate)
- [x] Commit `01216cc` exists (GREEN gate)
