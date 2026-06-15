---
phase: 01
slug: lexer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (Python 3.12.13) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`, `addopts = "-v"`) |
| **Quick run command** | `python3 -m pytest tests/test_lexer.py -q` |
| **Full suite command** | `python3 -m pytest -q` |
| **Estimated runtime** | ~1 second (58 Phase 0 tests collect in 0.01s; lexer suite is pure in-memory) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_lexer.py -q`
- **After every plan wave:** Run `python3 -m pytest -q` (full suite — guards the Phase 0 contract from regression)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

> Populated during/after planning once plan + task IDs exist. Each lexer task maps to one or
> more golden-token or error-path assertions in `tests/test_lexer.py`. Requirement coverage spans
> LEX-01 … LEX-08; the off-side-rule edge cases (balanced INDENT/DEDENT, EOF drain, blank/comment
> skip, staircase dedent, mixed tabs/spaces) and the four off-ramps (decimal, single-quote, colon,
> semicolon) each get dedicated message/count/order assertions.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | LEX-01…08 | — | N/A | unit (RED stubs) | `python3 -m pytest tests/test_lexer.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_lexer.py` — RED test stubs covering LEX-01 … LEX-08 (golden token snapshots + error-path assertions). Must exist before `src/atena/lexer.py` per TDD (CLAUDE.md).
- [x] `tests/conftest.py` — shared fixtures (already exists from Phase 0)
- [x] pytest framework — already installed (9.0.3), no install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification — the lexer is pure (source string → token list / collected errors), fully exercisable in-memory by pytest. No manual steps required.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_lexer.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
