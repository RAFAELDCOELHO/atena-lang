# Phase 0: Diagnostics Spine & Data Contracts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 0-Diagnostics Spine & Data Contracts
**Areas discussed:** Error voice & tone, 'Did you mean?' rules, Error volume cap, Phase 0 CLI stub scope

---

## Error voice & tone

### Register
| Option | Description | Selected |
|--------|-------------|----------|
| Plain & kind | First-person, calm, one gentle guiding question; patient tutor. | ✓ |
| Playful buddy | Casual, exclamations, emoji; risk of feeling patronizing/noisy. | |
| Minimal & gentle | Short, soft, no cheerleading or follow-up question. | |

**User's choice:** Plain & kind
**Notes:** Canonical example accepted: `I don't know what "score" is yet. / Did you forget to create it first?`

### Internal-error fallback
| Option | Description | Selected |
|--------|-------------|----------|
| Blame-free + invite report | Not-your-fault + ask to share program; no line. | |
| Blame-free, minimal | Reassure only, no call to action. | |
| Blame-free + line if known | Reassure + include Atena line when available + invite report. | ✓ |

**User's choice:** Blame-free + line if known
**Notes:** Include the line number when the failure can be tied to one; fall back gracefully when not.

### Message structure (house style)
| Option | Description | Selected |
|--------|-------------|----------|
| Problem + guidance when clear | Two-part; suggestion only when a genuine likely cause exists, else describe-only. | ✓ |
| Curated guidance set | Only a hand-picked set of errors carry guidance. | |
| Problem statement only | Single description, no suggestions ever. | |

**User's choice:** Problem + guidance when clear
**Notes:** Never invent a guess when the cause is ambiguous.

---

## 'Did you mean?' rules

### Eagerness
| Option | Description | Selected |
|--------|-------------|----------|
| Balanced — close matches | Suggest on reasonable closeness (length-aware), silent on wild misses. | ✓ |
| Strict — typos only | Only 1–2 char differences. | |
| Generous — always nearest | Always show closest however far. | |

**User's choice:** Balanced — close matches

### Candidate pool
| Option | Description | Selected |
|--------|-------------|----------|
| Variables + keywords | Engine takes a candidate set; search user names AND Atena keywords. | ✓ |
| User names only | Only learner-defined names; keyword typos get generic error. | |

**User's choice:** Variables + keywords

### Case-only mismatch
| Option | Description | Selected |
|--------|-------------|----------|
| Call it out explicitly | Suggest + teach "names must match capitalization exactly." | ✓ |
| Treat like any other typo | Counts toward closeness; generic wording. | |

**User's choice:** Call it out explicitly

### Number of suggestions
| Option | Description | Selected |
|--------|-------------|----------|
| One best guess | Single closest name; deterministic tie-break. | ✓ |
| Up to a few | Show ~2–3 similarly close names. | |

**User's choice:** One best guess

---

## Error volume cap

| Option | Description | Selected |
|--------|-------------|----------|
| Around 10 | Beginner-friendly; avoids a wall of errors. | ✓ |
| Around 25 | Middle ground. | |
| Around 50 | Research default; maximizes visibility. | |

**User's choice:** Around 10
**Notes:** Overflow line carries gentle guidance (`…and N more. Fix some and run again to see the rest.`). Dedup identical line+message first, then cap; errors always collected and line-sorted underneath.

---

## Phase 0 CLI stub scope

| Option | Description | Selected |
|--------|-------------|----------|
| Argparse + friendly placeholder | Subcommands + real file-error handling + "not built yet" placeholder. | ✓ |
| Wired to empty pipeline | Real transpile() over empty phase sequence reporting zero errors. | |
| Minimal arg parsing only | Just argparse + --help; no file handling. | |

**User's choice:** Argparse + friendly placeholder
**Notes:** Real plain-English file-not-found/unreadable message lands in Phase 0 (CLI-05 partial); `transpile()` pipeline wiring deferred to Phase 5.

---

## Claude's Discretion

- Exact string-distance algorithm and threshold curve for suggestions.
- Source-line carriage on Token/AST nodes vs ErrorCollector holding the source array (ARCHITECTURE.md recommends per-node carriage).
- Whether `col`/`col_offset` is included in the contract now (ARCHITECTURE.md includes `col` on Token).
- Module placement of suggestion engine / message templates (keep format in `errors.py`).
- `exec` vs subprocess for eventual `atena run` (Phase 5 concern).

## Deferred Ideas

None — discussion stayed within phase scope. (Full `transpile()` wiring and `atena run` execution strategy are explicit Phase 5 scope, not deferred ideas.)
