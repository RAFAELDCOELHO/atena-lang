# Phase 5: CLI Runtime & Pipeline Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 5-CLI Runtime & Pipeline Integration
**Areas discussed:** Run execution model, Runtime-error translation

---

## Area selection

| Candidate area | Description | Selected |
|----------------|-------------|----------|
| Run execution model | exec() in-process vs subprocess | ✓ |
| Runtime-error translation | CLI-04: Python runtime error → plain-English Atena message + line | ✓ |
| `build` output behavior | write `.py` vs stdout, `--show`, overwrite (CLI-02/CLI-06) | |
| CLI feel & ergonomics | bare `atena file.atena`, `--version`, learner-facing help | |

**User's choice:** Run execution model, Runtime-error translation.

---

## Run execution model

### Q1 — How should `atena run` execute the generated Python?

| Option | Description | Selected |
|--------|-------------|----------|
| exec() in-process (Rec.) | Run inside the same process; simplest; the crash hands us the live exception object (type + traceback) for cleaner error translation. cli.py already uses this. | ✓ |
| subprocess isolation | Temp file + separate process; cleaner stdin/stdout isolation but runtime crashes come back as a traceback string to parse/wrap. | |
| You decide | Let Claude weigh trade-offs in planning. | |

**User's choice:** exec() in-process.
**Notes:** Confirms the exec-vs-subprocess decision that 04-CONTEXT explicitly deferred to Phase 5. In-process gives the live exception object, which makes CLI-04 (curated messages + line recovery) cleaner.

### Q2 — Should `atena run` ever write the generated Python to disk?

| Option | Description | Selected |
|--------|-------------|----------|
| Purely in-memory (Rec.) | exec the string directly, never touch disk; `build` is the only file-producing verb. | ✓ |
| Write + run + keep .py | Leave a file.py behind for inspection; blurs the line with `build`, clutters the folder. | |
| You decide | Keep `run` ephemeral unless a reason emerges. | |

**User's choice:** Purely in-memory.
**Notes:** Keeps the learner's folder clean; `run` feels like "just run my program."

---

## Runtime-error translation (CLI-04)

### Q1 — How rich should runtime-error messages be, and how framed?

| Option | Description | Selected |
|--------|-------------|----------|
| Curated set + gentle (Rec.) | Specific friendly messages for common crashes (out-of-range index, ÷0, missing dict key, remove-not-found) + gentle generic fallback; framed about *their* program, naming the Atena line. Splits learner errors from the "not your fault" internal error; updates C-14. | ✓ |
| Generic line-numbered only | One template for any runtime error; simpler, less teaching value. | |
| You decide | Build a sensible curated set in planning. | |

**User's choice:** Curated set + gentle.
**Notes:** Surfaced during discussion: cli.py currently routes *every* exec crash through the internal "not your fault" message, and the C-14 test asserts that wording for a learner divide-by-zero — both conflict with CLI-04 and must change (planner does RED first).

### Q2 — How precise must the Atena line number be?

| Option | Description | Selected |
|--------|-------------|----------|
| Always pin exact line (Rec.) | Invest in a Python→Atena line mapping; even helper-raised errors (i<1 IndexError) get the precise line. | |
| Best-effort line | Pin when cheap; otherwise omit the line. | |
| You decide | Aim for exact, fall back to best-effort only where impractical. | ✓ |

**User's choice:** You decide.
**Notes:** Aim for exact lines; best-effort fallback only where exact mapping proves genuinely impractical. Never point at the wrong line.

### Q3 — Should runtime errors use the same format as compile errors, incl. the source line?

| Option | Description | Selected |
|--------|-------------|----------|
| Same format + source line (Rec.) | `Error on line {N}: {msg} → {source}` identical to compile errors; needs Atena source lines available at runtime. | ✓ |
| Line-numbered, no source line | Skip the `→ source` line; less plumbing, slightly inconsistent. | |
| You decide | Match canonical format if practical. | |

**User's choice:** Same format + source line.
**Notes:** One consistent error language — no perceived "compile vs runtime" divide.

---

## Claude's Discretion

- **Line-number precision mechanism** (Q2 above) — aim for exact Atena lines via the cleanest mapping (AST linenos, a lineno table, or injected markers); best-effort fallback only where impractical.
- **Cross-phase error gating** — pre-decided by research (ARCHITECTURE.md): collect-all within a phase, stop between phases on errors, never run codegen unless `is_empty()`. Confirmed, not re-litigated.
- **`build` output behavior** and **CLI ergonomics** — the two un-selected candidate areas; standard, beginner-friendly defaults left to research/planning.
- **exec mechanics** — compile() target filename, exec namespace, interactive `ask`/`input()` stdin, execution-test harness (canned stdin).

## Deferred Ideas

- `build` output behavior (write vs stdout, `--show`, overwrite) and CLI ergonomics (default verb, `--version`, help wording) — in Phase 5 scope but not deep-dived; sensible defaults in planning.
- Packaging (PKG-01), examples ladder beyond `school.atena` (DOCS-01), getting-started README (DOCS-02) — Phase 6.
- Number-parsing for `ask`, float support — v2.

No scope creep to redirect — discussion stayed within phase scope.
