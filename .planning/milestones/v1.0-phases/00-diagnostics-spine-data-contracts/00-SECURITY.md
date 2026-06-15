---
phase: "00"
slug: diagnostics-spine-data-contracts
status: secured
threats_open: 0
threats_total: 16
threats_closed: 16
asvs_level: 1
audited: 2026-06-13
---

# SECURITY.md — Atena Language Transpiler

**Phase:** 00 — Diagnostics Spine & Data Contracts
**Audited:** 2026-06-13
**ASVS Level:** L1
**Auditor:** gsd-secure-phase (Claude Sonnet 4.6)
**Result:** SECURED — all declared threats closed

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-00-01-SC | Tampering | mitigate | CLOSED | `pyproject.toml:10` — `dependencies = []` (zero runtime deps). Build backend is `hatchling` (well-known, PyPI-verified); `pytest` and `hatchling` are build/dev-only. No `[ASSUMED]` or `[SUS]` packages present. |
| T-00-02-01 | Information Disclosure | mitigate | CLOSED | `errors.py:76` — single format template is `f"Error on line {r.line}: {r.message}\n  → {r.source_line}"`. Independent grep: `"token"`, `"AST"`, `"DEDENT"`, `"arity"`, `"NoneType"`, `"traceback"`, `"Traceback"` each appear 0 times in any string literal in `errors.py`. Covered by `test_errors.py::test_no_jargon_in_errors_py` (PASS). |
| T-00-02-02 | Denial of Service | mitigate | CLOSED | `errors.py:17` — `ERROR_CAP: int = 10`. Enforced at `report()` render time (`errors.py:71-72`): `shown = unique[:ERROR_CAP]`; unbounded `_records` list only caps at display, not at `add()`. Pathological input does not crash. Test `test_cap_at_ten_with_overflow_line` (PASS). |
| T-00-04-01 | Denial of Service | mitigate | CLOSED | `errors.py:136` — `difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)`. Candidate set is caller-supplied; `errors.py:127-128` documents: "bounded in practice by the number of names in one Atena program (a few hundred at most)". No unbounded path. Tests S-1 through S-13 all pass. |
| T-00-05-01 | Information Disclosure | mitigate | CLOSED | `cli.py:131-140` — outer `except BaseException` converts all unexpected exceptions to `_internal_error_message(exc)` (blame-free). `KeyboardInterrupt`/`SystemExit` re-raised at `cli.py:136-137`. File-read path (`cli.py:124-128`) catches `UnicodeDecodeError` (WR-05 fix, commit 7bd054b confirmed present). Exec/run path (`cli.py:155-163`) is inside its own `try/except BaseException` (CR-01 fix, commit 0b4dd3c confirmed present). Tests C-7, C-8, C-12, C-14 all pass. |
| T-00-05-04 | Information Disclosure | mitigate | CLOSED | `cli.py:79` — `filename = os.path.basename(path)` in `_file_error_message()`; all user-facing file error strings use `filename` (basename only), never `path`. Comment at `cli.py:77` explicitly cites T-00-05-04. `os.path.basename` also used in `build` output message at `cli.py:152`. |

---

## Accepted-Risk Register

The following threats carry `accept` disposition. Each rationale is evaluated as reasonable for a local, offline, teaching CLI with no network surface.

| Threat ID | Category | Component | Accepted-Risk Rationale | Evaluation |
|-----------|----------|-----------|------------------------|------------|
| T-00-01-01 | Tampering | `pyproject.toml [project.scripts]` entry point | Developer-controlled; no user attack surface. | REASONABLE — entry point is managed by pip, no learner can modify it without owning the developer environment. |
| T-00-01-02 | Information Disclosure | pip install output on failure | Build-tool output visible to developer, not learner. | REASONABLE — install-time output never reaches the learner's terminal session. |
| T-00-02-03 | Tampering | `source_line` text in error output | Offline CLI; source_line comes from learner's own file. | REASONABLE — no injection risk in a local, single-user, offline tool. |
| T-00-03-01 | Tampering | `Token.source_line` field | `Token` is `@dataclass(frozen=True)` — immutable after construction. | REASONABLE and VERIFIED: `tokens.py:63` confirms `frozen=True`. Mutation raises `FrozenInstanceError`. |
| T-00-03-02 | Information Disclosure | AST node `__repr__` | Debug-only; `@dataclass` auto-repr is never surfaced to the learner. | REASONABLE — no code path prints AST repr to user-visible output. |
| T-00-03-03 | Denial of Service | `KEYWORDS` dict lookup | Static dict, O(1) lookup, no user-controlled growth. | REASONABLE — `tokens.py:97-117` is a static 19-entry dict. |
| T-00-04-02 | Information Disclosure | suggestion string | Only names already in learner's symbol table / keyword list. | REASONABLE — `suggest()` returns only from caller-supplied candidates; no internal implementation detail leaks. |
| T-00-04-03 | Tampering | `ATENA_KEYWORDS` runtime mutation | Callers copy via `list(ATENA_KEYWORDS) + extra` per documented pattern. | REASONABLE — `errors.py:96` docstring explicitly instructs: "user_candidates = list(ATENA_KEYWORDS) + known_variable_names". |
| T-00-05-02 | Tampering | File path from CLI arg | Local offline tool; no server; path traversal risk is negligible. | REASONABLE — the transpiler is a local dev/teaching CLI, not a server or multi-user system. |
| T-00-05-03 | Denial of Service | Very large `.atena` file | Teaching programs are small; no size cap needed. | REASONABLE for v1.0 scope — large-file DoS is not a realistic threat surface for a teaching language tool. |

---

## Unregistered Flags

None. SUMMARY.md `## Threat Flags` section was not authored for this phase (no new unregistered attack surface was flagged by the executor beyond the threats tracked above).

Code review findings CR-01 (exec block outside handler) and WR-05 (UnicodeDecodeError escape) were identified during the code review phase and fixed before verification. Both fixes are confirmed present in the implementation and covered by tests C-14 and C-12 respectively. These were registered in 00-REVIEW.md and are not new unregistered flags.

---

## Audit Notes

- The jargon test (`test_no_jargon_in_errors_py`) checks `["token", "AST", "DEDENT", "arity", "NoneType"]` but does not include `"traceback"` / `"Traceback"` in its `forbidden` list despite those words appearing in the plan-level threat description (00-02-PLAN.md:128). Independent grep confirms both words appear 0 times in `errors.py` — the mitigation holds in code regardless of the test's incomplete coverage. This is an informational gap in test coverage, not a code gap.
- `tokens.py:94` carries a stale comment saying "18 keywords" above a 19-entry dict (IN-01 from code review). This does not affect any security property.
- The `exec(..., {})` globals policy (IN-05 from code review) is informational only; generated code is trusted transpiler output at this phase.

---

_Audit method: FORCE stance — each mitigation verified by grep match and/or test execution before marking CLOSED._
_Test run: `pytest tests/test_errors.py tests/test_cli.py` — 38/38 passed._
