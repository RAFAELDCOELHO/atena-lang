# Phase 0: Diagnostics Spine & Data Contracts - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 0 builds the **cross-cutting diagnostics spine** and the **inter-phase data contracts** that every later phase plugs into — before the lexer exists. Concretely it delivers:

- A shared `ErrorCollector` (`add(line, message, source_line)`, `is_empty()`, `report()`), injected into phases, never global.
- The single source of truth for the error format: `Error on line {N}: {plain English}` followed by `→ {offending source line}`, line-sorted, deduplicated, capped.
- A "Did you mean?" suggestion utility usable by any phase.
- The internal-error safety net that converts any uncaught Python exception into a plain-English message (no traceback ever reaches the learner).
- Position-bearing data contracts: the `Token` type and the AST node dataclasses, each carrying a line number and the offending source-line text.
- A stub CLI (`atena run` / `atena build`) that parses args, handles file errors in plain English, and shows a friendly "not built yet" placeholder.

Covers requirements **DIAG-01 … DIAG-06** (and the file-error half of **CLI-05**, see D-12).

**In scope:** the error system, the data contracts, the suggestion engine, the internal-error fallback, and the stub CLI.
**Not in scope:** any actual lexing/parsing/analysis/codegen (Phases 1–4) and the real `transpile()` pipeline wiring (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Error voice & tone
- **D-01 — Register: "Plain & kind".** First-person, calm, one gentle guiding question. Reads like a patient tutor — warm but not performative. No emoji, no exclamation-heavy "buddy" tone. Canonical example:
  ```
  Error on line 4: I don't know what "score" is yet.
  Did you forget to create it first?
    → show score
  ```
- **D-02 — Internal-error fallback: blame-free + line if known.** When Atena itself crashes internally (not the learner's mistake), reassure it's not their fault, include the Atena line number when the failure can be tied to one, and gracefully omit the line when it can't. Invite the learner to share their program so it can be fixed. Example: `Something went wrong inside Atena near line 7 — this isn't your fault. Please share your program so we can fix it.` This is the safety net behind success criterion #5 / Pitfall 6 — no Python traceback ever reaches the user.
- **D-03 — Message structure (house style for ALL four phases): "problem + guidance when clear".** Two-part: state the problem, then a gentle next-step toward the likely fix — **but only when there is a genuine likely cause.** When the cause is ambiguous, describe only; never invent a guess. (Has guidance: `I don't know what "score" is yet. Did you forget to create it first?` — Describe-only: `This line's indentation doesn't match any block above it.`)

### "Did you mean?" rules
- **D-04 — Eagerness: balanced.** Suggest only when the typed name is reasonably close to a known one (similarity scales with length — e.g. ~70%+ / length-aware edit distance). Catch real typos (`scr`→`score`, `shwo`→`show`); stay silent on wild misses (`banana` → no suggestion). A far/absurd suggestion erodes a beginner's trust, so silence beats a bad guess.
- **D-05 — Candidate pool: variables + keywords.** The suggestion engine takes a **candidate set** as input; the convention is to search both the learner's own names (variables, functions) and Atena's keywords. Each phase passes whatever names it knows — keywords are always available (lex time), user-defined names accumulate as analysis proceeds. Engine design must accept an arbitrary candidate set so phases differ only in what they pass.
- **D-06 — Case-only mismatch: called out explicitly.** When the only difference is capitalization (`Score` vs defined `score`), always suggest the right name AND teach the rule: `Did you mean "score"? Names must match capitalization exactly.` This is a constant beginner mistake and a strong teaching moment.
- **D-07 — Count: one best guess.** Show only the single closest name. Ties broken deterministically (e.g. first-defined, then alphabetical) so output is stable/testable.

### Error volume & capping
- **D-08 — Show ~10 errors, then collapse.** Errors are always collected across the run and line-sorted underneath; the cap only governs how many are *shown*. After ~10, print a trailing `…and N more` line that itself carries gentle guidance (e.g. `…and 23 more. Fix some and run again to see the rest.`), consistent with the D-03 voice. ~10 chosen over research's ~50 because a wall of errors overwhelms a complete non-programmer. (DIAG-06)
- **D-09 — Dedup before cap.** Collapse duplicate errors sharing the same line **and** message to one, THEN apply the ~10 cap. Sort is stable so same-line errors keep insertion order. (DIAG-06)

### Phase 0 CLI stub scope
- **D-10 — Stub = argparse + friendly placeholder.** Both `run` and `build` subcommands exist with `--help`. They parse args, validate the input file, and print a friendly "this part isn't built yet — coming soon" notice where the pipeline will go. They do NOT fake a pipeline.
- **D-11 — Phase 0 ↔ Phase 5 boundary.** The real `transpile(source, filename)` function and the four-phase wiring belong to **Phase 5**, not Phase 0. Phase 0 ships only the CLI surface + error path.
- **D-12 — File-not-found / unreadable handling lands in Phase 0 (CLI-05 partial).** The stub uses the *real* plain-English file-error message (e.g. `I couldn't find a file called "missing.atena".`), not a placeholder — so CLI-05's friendly file handling is genuinely implemented here, exercising the diagnostics spine end-to-end before any phase exists.

### Claude's Discretion
The following are left to research/planning (the user did not constrain them; honor the locked items below):
- Exact string-distance algorithm for D-04 (Levenshtein vs `difflib.get_close_matches` vs custom length-aware ratio) and the precise threshold curve.
- Whether the source-line text is carried on every `Token`/AST node vs the `ErrorCollector` holding the source array and looking up by line. (ARCHITECTURE.md recommends per-token/per-node carriage — follow unless a better contract emerges.)
- Whether `col`/`col_offset` is included in the `Token`/AST contract now or added later (ARCHITECTURE.md includes `col` on `Token`).
- Internal module placement of the suggestion engine and message templates (ARCHITECTURE.md puts the format in `errors.py` as the single source of truth — keep it there).
- `exec` vs subprocess for the eventual `atena run` (deferred to Phase 5; out of scope here).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 0 scope & success criteria
- `.planning/ROADMAP.md` §"Phase 0: Diagnostics Spine & Data Contracts" — the 5 success criteria (what must be TRUE) and dependency/requirement mapping.
- `.planning/REQUIREMENTS.md` §"Diagnostics & Errors" — DIAG-01 … DIAG-06 verbatim; also CLI-05 (file handling) which partially lands here per D-12.

### Architecture & contracts (authoritative for HOW)
- `.planning/research/ARCHITECTURE.md` — the shared `ErrorCollector` design, the `errors.py`/`tokens.py`/`ast_nodes.py` module split (data modules are pure, dependency-free contracts), the full AST node-set, source-position threading, and the recommended `src/atena/` project structure. The single most relevant doc for this phase.
- `.planning/research/PITFALLS.md` — esp. Pitfall 6 (never let a Python exception reach the user → D-02), Pitfall 12 (cascading/duplicate errors → D-09), Pitfall 14 (errors not line-ordered / unbounded output → D-08/D-09), and the cross-cutting three-test-layer principle.
- `.planning/research/STACK.md` — Python 3.11+ floor, stdlib-only, `@dataclass` AST nodes, `argparse` CLI, `pyproject.toml` + `src/` layout, pytest with fixture files. Note: `keyword.kwlist` (stdlib) is the source of truth for any keyword list (relevant to D-05's keyword candidate pool).
- `.planning/PROJECT.md` §Constraints / §Key Decisions — collect-all-errors over fail-fast, no-traceback promise, TDD + per-phase feature branch (`feat/diagnostics` or similar), one phase 100% green before advancing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **None yet — greenfield.** No `src/`, `tests/`, or `pyproject.toml` exists. Phase 0 establishes the project skeleton.

### Established Patterns
- Project structure to follow (from ARCHITECTURE.md): `src/atena/{errors,tokens,ast_nodes,cli,pipeline}.py` with a mirrored `tests/` tree and a `fixtures/` dir. Phase 0 creates `errors.py`, `tokens.py`, `ast_nodes.py`, and a stub `cli.py` (and likely a placeholder `pipeline.py` boundary for Phase 5 to fill).
- `errors.py` is the ONE place the `Error on line {N}: … → {source}` format lives; every later phase imports the same `ErrorCollector`.
- `tokens.py` / `ast_nodes.py` must depend on nothing so any phase and any test can import them freely.
- TDD per PROJECT.md: failing test first, commit after each task, feature branch (not `main`).

### Integration Points
- `ErrorCollector` is the cross-cutting, many-to-one dependency injected into every future phase constructor.
- The stub `cli.py` is where Phase 5 will later wire `transpile()`; Phase 0 leaves a clean, friendly placeholder seam there.

</code_context>

<specifics>
## Specific Ideas

Concrete wordings the user selected during discussion — treat these as the canonical voice exemplars to match (not just describe):

- Undefined variable: `I don't know what "score" is yet. Did you forget to create it first?`
- Internal error: `Something went wrong inside Atena near line 7 — this isn't your fault. Please share your program so we can fix it.`
- Case mismatch: `I don't know what "Score" is yet. Did you mean "score"? Names must match capitalization exactly.`
- Suggestion (typo): `Did you mean "score"?` / keyword typo `shwo` → `Did you mean "show"?`
- Overflow line: `…and 23 more. Fix some and run again to see the rest.`
- File not found: `I couldn't find a file called "missing.atena".`
- CLI placeholder: `Atena can read your program, but running it isn't built yet — coming soon!`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (The full `transpile()` pipeline wiring and `atena run` execution strategy are not "deferred ideas" but explicit Phase 5 scope, per D-11.)

</deferred>

---

*Phase: 0-Diagnostics Spine & Data Contracts*
*Context gathered: 2026-06-13*
