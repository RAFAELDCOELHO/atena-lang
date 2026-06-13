# Feature Research

**Domain:** Teaching-oriented source-to-source transpiler (Atena → Python 3) for complete non-programmers
**Researched:** 2026-06-13
**Confidence:** HIGH (error-message and CLI patterns grounded in Elm, Rust, Python 3.10+, Hedy, Scratch, and novice-error-message research; MEDIUM on exact curriculum sequencing, which is convention not standard)

> Scope note: Atena's **language** feature set is FIXED by PROJECT.md (variables, show/ask, if/else, repeat-N, while, and/or/not, comparisons, integer arithmetic, functions+return, 1-indexed lists, dot-access dicts, silent str coercion). This research does **not** propose new language features — every item below is about the **product wrapper** that makes the locked language a good teaching tool: error quality, error recovery, CLI ergonomics, and curriculum. Anti-features tie directly to the PROJECT.md Out of Scope list.

## Feature Landscape

### Table Stakes (Users Expect These)

The teaching value collapses without these. They are the contract implied by "never sees a Python stack trace — only plain-English errors."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **No raw Python stack traces ever reach the learner** | Core promise of PROJECT.md. A leaked `Traceback (most recent call last)` instantly breaks the "no syntactic noise" illusion and re-introduces the exact jargon Atena exists to hide. | MEDIUM | The CLI runner must wrap execution and translate any Python runtime exception that escapes (e.g. `KeyError`, `ZeroDivisionError`, `IndexError`) back into Atena terms with the original Atena line. Source-map line numbers from analyzer → generated `.py` are the dependency. |
| **`Error on line N: <plain explanation> → <source line>` format, exactly** | The spec fixes this format. Showing the offending source line is the single highest-leverage readability technique — Elm and Rust both anchor the message on the literal code, and novice-error research finds "show the code" the top readability factor. | LOW–MEDIUM | Requires every token/AST node to carry its line number end-to-end. The `→ source` snippet means the lexer must retain raw line text, not just tokens. |
| **Plain-English wording, zero compiler jargon** | Novice-error research (Becker et al.; the "Readability and its Constituent Factors" CHI paper) shows terse/jargon messages cause frustration, repeated errors, and loss of confidence. Words like "token", "AST", "DEDENT", "arity", "NoneType" must never appear. | MEDIUM | A controlled vocabulary discipline: write each message as if to someone who has never programmed. "I don't know what `total` is — did you forget to set it?" not "undefined identifier `total`". |
| **Collect all errors in one run (error recovery), not fail-fast** | Explicitly a Key Decision in PROJECT.md. One-error-at-a-time forces beginners into a demoralizing whack-a-mole loop. Each phase gathers what it can; codegen runs only at zero errors. | HIGH | This is the hardest table-stake. Needs an error-collector/diagnostics bag threaded through all four phases plus parser synchronization points (see Differentiators → synchronization). |
| **Undefined-variable detection with the variable's name** | Spec requires the analyzer to detect undefined variables. Naming the actual identifier ("`scor` is not defined") is the difference between actionable and useless. | LOW | Symbol table in the analyzer already required by spec. Naming the variable is free once you have it. |
| **Function arity errors in human terms** | Spec requires arity checking. "The function `greet` needs 2 inputs but you gave it 1" beats "TypeError: greet() takes 2 positional arguments but 1 was given". | LOW | Function signature table in analyzer (already required). |
| **The 1-indexed `[0]` deliberate error** | PROJECT.md makes `items[0]` a *teaching* error: "Lists in Atena start at 1, not 0." This is table stakes because it's a named design decision — silently allowing or silently breaking `[0]` would betray the mental model. | LOW | Analyzer owns the 1→0 rewrite; `[0]` is caught before rewrite. |
| **`atena run file.atena` executes the program** | The default verb. Beginners want to see output immediately; making them run a separate Python step would surface the implementation. | LOW | Transpile in-memory → `exec`/subprocess the generated Python, capturing/translating runtime errors. |
| **`atena build file.atena` emits a `.py` file** | The "connect Atena to real code" affordance from PROJECT.md. Lets a learner see that their `show "hi"` became `print("hi")`. | LOW | Write generated source to `file.py` next to the input. |
| **Friendly file-handling errors** | clig.dev and CLI best-practice sources: a bare `No such file or directory` is "useless"; name the path and suggest a fix. A beginner who typos a filename should not get a Python traceback from `open()`. | LOW | Catch missing-file / wrong-extension / permission cases in the CLI layer before the pipeline runs. |
| **`pip install`-able entry point** | PROJECT.md ships packaging. A learning tool nobody can install delivers zero value. The `atena` command must exist on PATH after install. | LOW | `pyproject.toml` console-script entry point; stdlib-only keeps it trivial. |
| **An `examples/` folder covering the concept ladder** | A required deliverable. "By example" learning (Go by Example, Tour of Go, Dlang Tour) is the dominant beginner on-ramp; runnable examples are how non-programmers learn a new language. | LOW–MEDIUM | Content work, not engineering. Each example must actually run under `atena run`. |
| **Getting-started tutorial / README** | PROJECT.md ships docs. First-run experience determines whether a non-programmer continues. Must show install → write `show "hello"` → `atena run` in under a minute. | LOW | Doc work. |

### Differentiators (Competitive Advantage)

Not strictly required to function, but these are what make Atena *notably good* for learners versus "a working transpiler." They align with the Core Value: teach algorithmic logic without syntactic noise.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **First-person, encouraging compiler voice** | Elm's signature move ("I cannot find a `view` variable…"). It reframes the compiler as an assistant, not an adversary — the explicit Elm design goal. Reduces the "scolding" tone novice-error research flags as a frustration driver. | LOW | Pure wording choice, zero engineering cost. Decide a voice and apply consistently. High value-to-effort ratio. Caveat: keep it brief — Elm is occasionally criticized as "paternalistic"/verbose; one warm sentence, not a paragraph. |
| **"Did you mean…?" suggestions for typo'd names/keywords** | Python 3.10+, Rust, and Hedy all do edit-distance suggestions ("Did you mean `score`?"). Catches the single most common beginner mistake — a misspelled variable, function, or keyword — and turns a dead end into a one-keystroke fix. | MEDIUM | Levenshtein over the symbol table (for names) and the fixed keyword list (for `shwo`→`show`). Stdlib `difflib.get_close_matches` makes this nearly free. Strong differentiator for very low cost. |
| **Parser synchronization points so one mistake doesn't cascade** | The hard half of "collect all errors." Without sync points, a single bad line produces a cascade of spurious downstream errors that bury the real one — the documented failure mode of naive panic-mode recovery. Synchronizing on line boundaries / DEDENT lets the parser recover cleanly. | HIGH | Because Atena blocks are indentation-delimited and statements are line-oriented, the **newline/next-statement boundary is a natural, reliable synchronization token** — much simpler than brace/semicolon languages. This is an architectural advantage worth exploiting. |
| **Cascading-error dedup + sensible error cap** | Best-in-class recovery shows *real* errors, not noise. clig.dev: "group similar errors." Once a variable is reported undefined, don't re-report it on every later use. Cap the list (e.g. first ~10) with "…and N more" so a beginner isn't buried. | MEDIUM | Track already-reported symbols; suppress duplicates. Cap-and-summarize at the reporting layer. |
| **`atena build` prints/echoes the generated Python (or a `--show`/`--python` flag on `run`)** | The "aha, my `repeat 3 times` became a `for` loop" moment. PROJECT.md explicitly wants learners to "connect Atena to real code." Seeing the clean generated Python is a uniquely motivating teaching artifact most beginner tools lack. | LOW | Generated Python should be *readable* (good names, blank lines) precisely because learners will read it — treat codegen output as teaching material, not just machine fodder. |
| **Coercion is silent at runtime but inspectable** | Silent `str()` injection (spec) means `"score: " + 5` just works — no crash for a beginner. The differentiator is that `atena build` reveals the injected `str(...)`, so an instructor can explain *why* it worked. | LOW | Falls out of the analyzer's coercion pass; value is in surfacing it via `build`. |
| **Annotated examples (comments explaining each concept)** | Go by Example's whole value is annotation, not just code. For non-programmers, a bare program teaches less than one with `# this asks the user a question` comments. | LOW | Content quality choice. Atena supports comment-only lines (lexer skips them), so examples can self-document. |
| **A single canonical end-to-end "golden" example** | PROJECT.md names a `school.atena`-style script as the canonical fixture. As a *teaching* artifact it doubles as the capstone example that combines every concept — the thing a learner aspires to write. | LOW | Already required as an integration fixture; promote it into `examples/` as the showcase. |
| **Consistent exit codes (0 success, non-zero on error)** | Lets the tool be used in graded/automated settings and matches CLI norms. Cheap, and signals polish. | LOW | clig.dev convention; errors to stderr, program output to stdout. |

### Anti-Features (Commonly Requested, Often Problematic)

These tie directly to the PROJECT.md **Out of Scope** list. Documenting them prevents scope creep and protects the beginner mental model. Each is "commonly requested" precisely because it exists in Python — but adding it re-introduces the noise Atena removes.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **`elif`** | Python has it; nested if/else feels verbose to experienced eyes. | Adds a third control-flow keyword and a grammar branch for marginal gain; beginners reason fine with nested if/else. (Out of Scope.) | Teach nested `if/else`; the indentation makes the nesting visually obvious — itself a lesson. |
| **Float numbers** | "What if I want 3.5?" | Drags in precision, rounding, and formatting teaching detours that derail algorithmic-logic focus. (Out of Scope.) | Integers only in v1.0. Defer floats to a later milestone if validated. |
| **String escaping (`\n`, `\"`)** | Users will want newlines/quotes inside strings. | Escaping is a notorious beginner stumbling block and balloons lexer complexity. (Out of Scope.) | Double-quoted literals only; multiple `show` calls for multiple lines. |
| **Negative list indices / slicing** | Python power users expect `list[-1]` and `list[1:3]`. | Negative indices directly contradict the 1-indexed "first, second, third" model and would confuse it; slicing is beyond foundational logic. (Out of Scope.) | 1-indexed positive access plus `length`, `add`, `remove`. Teach iteration over slicing. |
| **Default params / nested functions / closures** | Make functions "more powerful." | Default params complicate the call model; closures are an advanced concept that flat scope deliberately avoids. (Out of Scope.) | Flat, fixed-arity functions with explicit `return`. |
| **Classes / OOP / module imports / multi-file** | "Real" programs have these. | v1.0 teaches *procedural* logic; OOP and modules are a whole second curriculum and break the single-program model. (Out of Scope.) | Single-file procedural programs. Composition via functions. |
| **REPL / interactive mode** | Many languages have a REPL for quick experiments. | PROJECT.md is file-based transpilation only; a REPL is a separate execution model (line-at-a-time, no DEDENT-delimited blocks) that doubles the surface area. (Out of Scope.) | `atena run file.atena` on a tiny scratch file is the "quick experiment" path. |
| **Configurable strictness / "expert mode" flags** | Power users want to disable the hand-holding. | Defeats the purpose: the guardrails (1-indexing error, silent coercion, no stack traces) *are* the teaching. A flag to turn them off invites confusing partial states. | One opinionated mode. No knobs. |
| **Auto-fixing the learner's code** | "If you know it's a typo, just fix it." | Auto-applying fixes (vs. *suggesting* them) removes the learning moment and can silently change intent. Rust marks suggestions with applicability/confidence rather than blindly rewriting. | *Suggest* ("Did you mean `score`?"); let the learner make the edit. |
| **Localized/translated keywords & messages** | Hedy shows native-language keywords help children learn faster. | Real benefit, but multiplies grammar and message surface area enormously (Hedy's hardest engineering problem) and isn't in v1.0 scope. | English keywords/messages for v1.0; note localization as a credible future milestone. |
| **Rich IDE/LSP integration, syntax highlighting plugins** | Modern dev expectation. | Large surface area orthogonal to the transpiler's core teaching value; not in scope. | Plain `.atena` files; clear CLI errors substitute for in-editor diagnostics in v1.0. |

## Feature Dependencies

```
[Line-number propagation: lexer keeps raw line text + line nums]
    └──requires──> [Error on line N: ... → source format]
                       └──requires──> [No stack traces reach learner]
                       └──requires──> ["Did you mean...?" suggestions]

[Symbol table in analyzer]
    └──requires──> [Undefined-variable detection (named)]
    └──requires──> [Function arity errors]
    └──enhances──> ["Did you mean...?" for variable/function names]

[Error-collector / diagnostics bag threaded through all 4 phases]
    └──requires──> [Collect all errors (error recovery)]
                       └──requires──> [Parser synchronization points]
                       └──enhances──> [Cascading-error dedup + cap]

[Code generator emits readable Python]
    └──enhances──> [atena build shows generated Python]
    └──enhances──> [Inspectable silent coercion]

[atena run / atena build CLI]
    └──requires──> [Friendly file-handling errors]
    └──requires──> [pip-installable entry point]

[examples/ folder] ──enhances──> [getting-started tutorial]
[golden school.atena fixture] ──doubles-as──> [capstone example]

[REPL] ──conflicts──> [file-based DEDENT-delimited block model]  (← anti-feature)
[elif / floats / slicing] ──conflicts──> [minimal beginner mental model]  (← anti-features)
```

### Dependency Notes

- **Everything error-related requires line-number propagation:** the `→ source` snippet means the lexer must retain each line's raw text keyed by line number, and every token/AST node must carry its line. Build this into the token model in Phase 1 (Lexer) or pay for it later in every phase.
- **"Collect all errors" requires parser synchronization, which depends on indentation structure:** Atena's line-oriented, indentation-delimited grammar gives a clean, natural sync token (statement/line boundary, DEDENT). This is an architectural gift — exploit it rather than inventing ad-hoc recovery.
- **"Did you mean…?" enhances the analyzer's existing symbol table and the fixed keyword list:** near-zero marginal cost (`difflib`) once those structures exist; do it in the same phase that builds them.
- **`atena build` value depends on codegen readability:** because learners *read* the emitted Python, codegen quality is a teaching feature, not just correctness. Don't emit dense or oddly-named Python.
- **REPL and the locked block model conflict:** a REPL evaluates line-by-line, which fights DEDENT-delimited blocks — a structural reason (beyond scope) to keep it out of v1.0.

## MVP Definition

### Launch With (v1) — the locked v1.0

- [ ] **`Error on line N: ... → source` format, plain English, no jargon** — the contract; without it the product is "a transpiler," not "a teaching tool."
- [ ] **No Python stack trace ever escapes** (compile-time *and* runtime errors translated) — the headline promise.
- [ ] **Collect-all-errors recovery with parser synchronization** — explicit Key Decision; the defining UX difference for beginners.
- [ ] **Named undefined-variable + human arity errors + 1-indexed `[0]` teaching error** — spec-required analyzer behaviors.
- [ ] **`atena run` and `atena build`** with friendly file-not-found handling — spec-required CLI.
- [ ] **pip-installable `atena` entry point** — required to deliver value at all.
- [ ] **`examples/` covering the full ladder + getting-started README** — required teaching deliverable.

### Add After Validation (v1.x) — low-cost differentiators, fold in early if cheap

- [ ] **First-person encouraging compiler voice** — trigger: any learner reports an error felt "harsh." (Near-zero cost; arguably belongs in v1.)
- [ ] **"Did you mean…?" suggestions** — trigger: typos dominate observed beginner errors. (`difflib`, cheap.)
- [ ] **Cascading-error dedup + error cap** — trigger: real programs produce noisy error walls.
- [ ] **`--show`/`--python` flag on `run`** to echo generated Python — trigger: learners ask "what did this become?"
- [ ] **Annotated examples** — trigger: bare examples leave learners with unanswered "why" questions.

### Future Consideration (v2+) — defer past PMF

- [ ] **Localized keywords/messages (Hedy-style)** — defer: large grammar/message surface; validate the English product first.
- [ ] **Floats, then maybe `elif`/slicing** — defer: each is an Out-of-Scope decision with a stated rationale; only revisit if learner demand is proven.
- [ ] **Editor/LSP integration, syntax highlighting** — defer: orthogonal surface area; CLI errors carry v1.0.
- [ ] **REPL** — defer: conflicts with the v1.0 block model; would need its own execution design.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Plain-English `Error on line N: ... → source` | HIGH | MEDIUM | P1 |
| No stack traces escape (compile + runtime) | HIGH | MEDIUM | P1 |
| Collect-all-errors recovery + sync points | HIGH | HIGH | P1 |
| Named undefined-var / arity / `[0]` errors | HIGH | LOW | P1 |
| `atena run` / `atena build` | HIGH | LOW | P1 |
| Friendly file-not-found handling | HIGH | LOW | P1 |
| pip-installable entry point | HIGH | LOW | P1 |
| `examples/` ladder + getting-started README | HIGH | LOW–MED | P1 |
| First-person encouraging voice | MEDIUM | LOW | P2 (P1-cheap) |
| "Did you mean…?" suggestions | HIGH | MEDIUM | P2 |
| Cascading dedup + error cap | MEDIUM | MEDIUM | P2 |
| Echo generated Python on `run` | MEDIUM | LOW | P2 |
| Annotated examples | MEDIUM | LOW | P2 |
| Consistent exit codes / stdout-stderr split | MEDIUM | LOW | P2 |
| Localized keywords/messages | HIGH (future) | HIGH | P3 |
| REPL / IDE integration | MEDIUM (future) | HIGH | P3 |

**Priority key:** P1 = must have for launch · P2 = should have, add when possible · P3 = future consideration

## Competitor Feature Analysis

| Feature | Hedy | Elm | Rust | Python 3.10+ | Scratch | Atena's Approach |
|---------|------|-----|------|--------------|---------|------------------|
| Beginner error tone | Plain, refers to symbols by name in quotes; still found "hard to understand" by kids — message quality is an ongoing struggle | First-person, warm, didactic ("I cannot find…"); occasionally called paternalistic | Structured: primary + secondary labels, `help:` vs `note:`, `--explain` | "Did you mean…?", "Perhaps you forgot a comma?" | Avoids errors entirely via block shapes | Plain English, optional first-person voice, **one warm sentence** — copy Elm's tone, avoid its verbosity |
| Show offending source | Quotes the character/token | Shows code snippet with `43|>` pointer | Underlines span in source | Carets under the spot | N/A (visual) | **`→ source` line** is mandated; the highest-leverage technique |
| Typo suggestions | Some | Yes (hints) | Yes | Yes (`difflib`-style) | N/A | **"Did you mean…?"** via `difflib` (P2 differentiator) |
| Multiple errors at once | Level-gated; limited | Reports several | Reports many with recovery | Improving | N/A | **Collect-all with synchronization** (P1) — a deliberate edge |
| Prevent vs. report errors | Gradual levels reduce surface | Strong type system prevents | Strong types prevent | Reports | **Prevents** syntactically | Atena can't prevent (it's textual) → **invests in recovery + clarity** instead |
| Seeing the "real" target language | End state is valid Python subset | N/A | N/A | N/A | N/A | **`atena build` reveals generated Python** — a teaching artifact few peers offer |
| Localization | Native-language keywords (signature feature) | English | English | English | Localized UI | **English in v1.0**, localization a credible v2 milestone |

## Sources

- Hedy — design philosophy, gradual levels, error-message struggles, localization: [Design, implementation and evaluation of the Hedy programming language (PDF)](https://hedy.org/research/Design_Implementation_and_evaluation_of_the_Hedy_programming_language_2022.pdf), [Hedy: A Gradual Language for Programming Education (ACM)](https://dl.acm.org/doi/abs/10.1145/3372782.3406262), [hedyorg/hedy (GitHub)](https://github.com/hedyorg/hedy), [A Framework for the Localization of Programming Languages (PDF)](https://hedy.org/research/A_Framework_for_the_Localization_of_Programming_Languages_2023.pdf)
- Elm — "compiler as assistant," first-person voice, source-snippet + hints structure: [Compilers as Assistants (Harvard mirror)](https://tagteam.harvard.edu/hub_feeds/1936/feed_items/2140220), [Elm — Amazing, Informative, Paternalistic Error Messages (jamalambda)](https://jamalambda.com/posts/2021-06-13-elm-errors.html), [Syntax Error Reporting — elm/compiler (DeepWiki)](https://deepwiki.com/elm/compiler/4.1-syntax-error-reporting)
- Rust — primary/secondary labels, `help:` vs `note:`, `--explain`, suggestion applicability: [Default and expanded rustc errors RFC 1644](https://rust-lang.github.io/rfcs/1644-default-and-expanded-rustc-errors.html), [Errors and lints — rustc dev guide](https://rustc-dev-guide.rust-lang.org/diagnostics.html)
- Python 3.10–3.14 — "Did you mean…?", "Perhaps you forgot a comma?", NameError/AttributeError suggestions: [Python 3.10 Introduces Better Error Messaging (Xebia)](https://xebia.com/blog/python-3-10-introduces-better-error-messaging/), [Python 3.12 Preview: Ever Better Error Messages (Real Python)](https://realpython.com/python312-error-messages/), [What's New In Python 3.12](https://docs.python.org/3/whatsnew/3.12.html)
- Scratch / block-based — preventing syntax errors via block shapes (why Atena, being textual, must invest in recovery instead): [Block-based Programming in CS Education (CACM)](https://cacm.acm.org/magazines/2019/8/238340-block-based-programming-in-computer-science-education/fulltext), [Block-Based Coding (Scratch Wiki)](https://en.scratch-wiki.info/wiki/Block-Based_Coding)
- Novice error-message research — readability factors, frustration, plain-English enhancement: [On Designing Programming Error Messages for Novices: Readability and its Constituent Factors (CHI 2021)](https://dl.acm.org/doi/fullHtml/10.1145/3411764.3445696), [Effective compiler error message enhancement for novice programming students (ResearchGate)](https://www.researchgate.net/publication/308343816_Effective_compiler_error_message_enhancement_for_novice_programming_students), [Teaching Programming Error Message Understanding (ACM 2023)](https://doi.org/10.1145/3598579.3689377)
- Compiler error recovery — panic-mode, synchronization tokens, cascading-error limitations: [Error Detection and Recovery in Compiler (GeeksforGeeks)](https://www.geeksforgeeks.org/compiler-design/error-detection-recovery-compiler/), [Panic-Mode Error Recovery (idallen teaching notes)](https://teaching.idallen.com/cst8152/98w/panic_mode.html)
- CLI ergonomics — error rewriting, file-not-found phrasing, subcommand design, human-first defaults: [Command Line Interface Guidelines (clig.dev)](https://clig.dev/), [CLI design: Error reporting (jmmv.dev)](https://jmmv.dev/2013/08/cli-design-error-reporting.html)
- "By example" curriculum model — annotated runnable examples as the beginner on-ramp: [Go by Example](https://gobyexample.com/), [A Tour of Go](https://go.dev/tour/), [Dlang Tour](https://tour.dlang.org/)

---
*Feature research for: teaching transpiler (Atena → Python 3)*
*Researched: 2026-06-13*
