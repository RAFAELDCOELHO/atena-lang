# Pitfalls Research

**Domain:** Hand-built teaching transpiler (Atena → Python 3), 4-phase pipeline: Lexer → Parser → Analyzer → Generator
**Researched:** 2026-06-13
**Confidence:** HIGH (core compiler-construction failure modes are well-documented; CPython's INDENT/DEDENT algorithm, unary-vs-binary minus handling, and Python negative-index semantics verified against official docs)

These pitfalls are specific to *this* transpiler. They are ordered by how expensive they are to fix once shipped: INDENT/DEDENT and index-shift bugs cause silent wrong output (worst — the learner runs code that lies); precedence and coercion bugs cause crashes or wrong results; error-recovery bugs cause infinite loops or error spam (the product's whole selling point is good errors). Each is mapped to the phase that owns it.

---

## Critical Pitfalls

### Pitfall 1: DEDENT to an unmatched indentation level

**What goes wrong:**
A line dedents to a column that was never on the indent stack. Example:

```
if x > 1
        show "a"     ← indent 8
    show "b"         ← dedent to 4, but 4 was never pushed
```

The naive lexer pops until it finds a level ≤ 4, emits one DEDENT, and silently continues as if `show "b"` belonged to an outer block — producing structurally wrong (but valid) Python.

**Why it happens:**
Developers implement the "pop while top > current" half of the algorithm but forget the invariant: after popping, the new top **must equal** the current indentation. CPython enforces this; a hand-rolled lexer usually doesn't unless told to.

**How to avoid:**
Implement the exact CPython stack algorithm: push `0` before line 1. Per logical line, compare indentation to stack top — equal → nothing; greater → push + emit INDENT; smaller → pop + emit DEDENT for each level popped, **then assert the new top equals current indentation**. If it doesn't, emit a plain-English error (`Error on line N: This line's indentation doesn't match any open block → {source}`). Do not silently continue.

**Warning signs:**
Generated Python has blocks at the wrong nesting depth but still runs. A test with "staircase" indentation (4, 8, then back to 6) passes when it should error.

**Phase to address:** Lexer

---

### Pitfall 2: EOF does not close open blocks

**What goes wrong:**
The file ends while blocks are still open (indentation stack has entries > 0). If the lexer stops emitting tokens at EOF without draining the stack, the parser sees an unterminated block and either crashes with an opaque Python `IndexError`/`StopIteration` or produces a truncated AST.

**Why it happens:**
The DEDENT-on-dedent logic only fires when a *new* line is read. EOF is not a line, so the developer forgets to run the drain step.

**How to avoid:**
At EOF, before emitting the final token, generate one DEDENT for every stack entry greater than zero (verified CPython behavior: "At the end of the file, a DEDENT token is generated for each number remaining on the stack that is larger than zero"). Also emit a final NEWLINE if the last logical line didn't end in one, so the parser's statement-terminator logic is uniform.

**Warning signs:**
A program with no trailing newline, or one ending inside a nested block, throws an internal Python exception instead of producing output. The parser's "expect DEDENT" path is never exercised by EOF tests.

**Phase to address:** Lexer

---

### Pitfall 3: Blank lines and comment-only lines emit spurious NEWLINE/INDENT/DEDENT

**What goes wrong:**
An indented blank line or comment-only line is treated as a real logical line. It either (a) emits a NEWLINE that confuses the parser into ending a statement early, or (b) its indentation gets measured and pushed/popped, corrupting the indent stack so the *next* real line dedents wrongly.

**Why it happens:**
Indentation is computed per *physical* line, but INDENT/DEDENT must be computed only for *logical* lines (lines with actual tokens). Blank and comment-only lines are not logical lines.

**How to avoid:**
Match CPython exactly: "A logical line that contains only spaces, tabs, formfeeds and possibly a comment is ignored (no NEWLINE token is generated)." Skip the line entirely *before* measuring indentation — do not push/pop the stack, do not emit NEWLINE/INDENT/DEDENT. Strip the comment first, then check if anything remains.

**Warning signs:**
Adding a blank line or a comment inside a block changes the parse. A comment indented deeper than its surrounding code triggers a phantom INDENT error.

**Phase to address:** Lexer

---

### Pitfall 4: Mixed tabs and spaces accepted silently or measured inconsistently

**What goes wrong:**
The constraint says a file uses tabs OR spaces, not both. If the lexer measures indentation by character count without detecting mixing, a tab-indented line and an 8-space-indented line may compare equal or unequal unpredictably, producing nondeterministic block structure.

**Why it happens:**
Developers count `len(leading_whitespace)` and never check character *kind*. The bug is invisible until a user's editor inserts a tab.

**How to avoid:**
On the first indented line, record the indent character (tab or space). On every subsequent indented line, if a different indent character appears, emit a plain-English error (`Error on line N: Don't mix tabs and spaces for indentation → {source}`). Do not try to be clever with tab-width normalization (CPython's 1-to-8-space tab rule); for a teaching language, forbidding mixing outright is simpler and clearer than emulating tab stops.

**Warning signs:**
A file that looks correctly indented in one editor parses differently in another. No test feeds a tab character into the lexer.

**Phase to address:** Lexer

---

### Pitfall 5: Variable index shift breaks negatives-are-errors, or `items[i]` where `i==0` silently returns the last element

**What goes wrong:**
This is the single most dangerous bug in the project because it produces *runnable Python that gives wrong answers*. Atena is 1-indexed; `items[1]` → `items[0]`. For literal indices the analyzer can check at compile time (`items[0]` is an error). For *variable* indices (`items[i]`) the shift must happen at runtime, and the naive rewrite `items[i - 1]` has two traps:

1. If `i` holds `0` at runtime, `items[i - 1]` becomes `items[-1]` — Python silently returns the **last** element instead of raising the intended "lists start at 1" error. (Verified: Python's valid index range is `-n` to `n-1`; `-1` is the last element.)
2. If `i` holds a negative value, `items[i - 1]` shifts it further negative, still a valid Python negative index — so a value Atena should reject is silently accepted as from-the-end indexing.

**Why it happens:**
The analyzer applies the `-1` shift uniformly and assumes Python's bounds checking will catch bad indices. But Python *doesn't* bounds-check negatives the way Atena's mental model requires — negatives are legal in Python and mean "from the end."

**How to avoid:**
Do **not** emit a bare `items[i - 1]`. Generate a runtime helper that enforces the 1-indexed contract and converts, e.g.:

```python
def _atena_index(seq, i):  # i is the 1-based Atena index
    if i < 1:
        raise _AtenaError("Lists in Atena start at 1, not 0")
    return seq[i - 1]
```

Generate `_atena_index(items, i)` for every variable subscript (read and write paths). The helper raises an *Atena* error (caught and reformatted to plain English at runtime), never a raw Python `IndexError`. For literal indices, the analyzer still rejects `0`/negatives at compile time so the learner gets a line-numbered error without running.

**Warning signs:**
A test where a loop variable reaches `0` returns the last element instead of erroring. No test exercises `items[i]` with `i = 0` or a negative variable. Generated code contains `[i - 1]` directly.

**Phase to address:** Analyzer (decides shift + helper insertion), Generator (emits helper), Testing (must run the generated Python)

---

### Pitfall 6: Double-shifting the index

**What goes wrong:**
Both the analyzer and the generator (or two passes within the analyzer) apply the `-1` conversion, so `items[2]` becomes `items[0]` instead of `items[1]`. Or a literal already lowered to 0-based gets shifted again.

**Why it happens:**
The "who owns the 1→0 rewrite" boundary is fuzzy. If the AST node isn't marked as "already converted," a later pass re-converts it. Nested indexing (`grid[i][j]`) multiplies the chances.

**How to avoid:**
Make the conversion a single, idempotent step owned exclusively by the analyzer. Tag converted subscript nodes (e.g., `node.index_converted = True`) and assert no node is converted twice. The generator must treat indices as already-0-based and emit them verbatim — it never touches index math. Write a test with nested subscripts (`grid[2][3]` → `grid[1][2]`) to catch multiplicative double-shift.

**Warning signs:**
`items[2]` returns the first element. Off-by-one only on the second dimension of nested access. Two code paths both contain `- 1`.

**Phase to address:** Analyzer (owns conversion), Generator (must NOT convert)

---

### Pitfall 7: Unary-minus vs binary-minus ambiguity in the parser

**What goes wrong:**
`-x` (negation) and `a - b` (subtraction) share the `-` token. A recursive-descent/Pratt parser that doesn't distinguish them will either parse `5 - 3` as `5` followed by `-3` (two expressions), or fail to parse leading `-5`. Worse, getting unary precedence wrong makes `-2 * 3` parse as `-(2 * 3)` vs `(-2) * 3` (same value here, but `-a + b` vs `-(a + b)` differ).

**Why it happens:**
The token is the same; the *position* disambiguates. In Pratt terms, `-` needs both a `nud` (prefix/null-denotation, no left operand → unary) and a `led` (infix/left-denotation, has left operand → binary). Developers implement only one.

**How to avoid:**
Use the Pratt nud/led split (verified standard technique): `-` as a prefix operator (nud) parses a unary negation with **high** binding power; `-` as an infix operator (led) parses subtraction with normal additive binding power. The parser decides which based on whether a left operand is present. Since Atena has no `**` operator (integers only, no exponent in scope), the classic `-2 ** 2` ambiguity does not apply — but document this so it isn't reintroduced.

**Warning signs:**
`x = -5` fails to parse. `5 - 3` produces two statements. `-a + b` evaluates as `-(a + b)`. No test covers a leading unary minus or `a - -b`.

**Phase to address:** Parser

---

### Pitfall 8: Operator precedence and associativity errors

**What goes wrong:**
`2 + 3 * 4` parses as `(2 + 3) * 4 = 20` instead of `2 + (3 * 4) = 14`. Or left-associative subtraction parses right: `10 - 3 - 2` becomes `10 - (3 - 2) = 9` instead of `(10 - 3) - 2 = 5`. Comparison/logical operator precedence (`and`/`or`/`not`, `>`, `==`) is also easy to get wrong relative to arithmetic.

**Why it happens:**
Precedence is encoded as binding-power numbers; one wrong number inverts an entire tier. Associativity is controlled by whether the recursive call uses `bp` or `bp + 1` (or `bp - 1`) for the right operand — a single off-by-one flips left/right associativity.

**How to avoid:**
Write the full precedence table from the spec as a single source of truth (one place mapping operator → binding power → associativity). Drive the Pratt loop from that table. For left-associative binary operators, parse the right operand with `bp + 1`; for right-associative, with `bp`. Add a golden test per precedence boundary: `2 + 3 * 4`, `10 - 3 - 2`, `not a and b`, `a > b == c` (or whatever the spec allows). Since the transpiler emits Python, you can cross-check: the generated expression should evaluate to the same value Python gives for the equivalent fully-parenthesized form.

**Warning signs:**
Arithmetic gives wrong results that "look almost right." `10 - 3 - 2` ≠ 5. Precedence is hardcoded in `if/elif` chains rather than a table.

**Phase to address:** Parser

---

### Pitfall 9: Postfix chaining (`a[1].b(c)`) parsed with wrong left-binding

**What goes wrong:**
Chained postfix operators — subscript `[ ]`, member access `.`, call `( )` — must left-associate and bind tighter than any binary operator. A naive parser parses `a[1]` then stops, or parses `a.b(c)` as `a.(b(c))`, or applies a binary operator before completing the postfix chain (`x + a[1]` grabs `a` not `a[1]`).

**Why it happens:**
Postfix operators are easy to forget in a Pratt setup because they're "led" operators with no right operand to recurse on — they consume a delimiter instead. Chaining requires looping: after parsing one postfix, loop to check for another.

**How to avoid:**
Treat `[`, `.`, `(` as the highest-binding-power infix/postfix operators. After parsing a primary, run a postfix loop: while the next token is `[`, `.`, or `(`, wrap the current node (subscript/member/call) and continue. This naturally produces left-associative chains: `a[1].b(c)` → `call(member(subscript(a, 1), b), c)`. Add tests for each chain shape and for a chain inside a larger expression (`total + scores[i].count()` if the grammar allows methods; otherwise the relevant subset).

**Warning signs:**
`a[1][2]` only applies one subscript. `x + a[1]` binds `+` before the subscript. The dict-write path (`config.key = v`) and dict-read path (`config.key`) take different code paths and disagree.

**Phase to address:** Parser

---

### Pitfall 10: Type-coercion injection wraps the wrong operand, or can't decide string-ness statically

**What goes wrong:**
The spec: `string + number` and `string + boolean` auto-wrap the *non-string* side in `str()`; `number + number` and `string + string` are untouched; other combos are an error. The traps:

1. **Static type unknown.** For `name + 1`, if `name` is an identifier whose type the analyzer can't prove, it can't know whether to coerce. Coercing a number identifier (`x + 1` where `x` is a number) would wrongly produce `str(x) + 1` and crash.
2. **Wrong operand wrapped.** `1 + "a"` must wrap the `1` (left), not the `"a"`. Off-by-one in which side gets `str()`.
3. **Not coercing `number + number`.** Accidentally wrapping when both sides are numbers.
4. **Chained `+`.** `"a" + 1 + 2` parses as `("a" + 1) + 2`. The left subtree `"a" + 1` has result type *string*, so the outer `+ 2` must coerce `2`. If the analyzer only inspects leaf types, it wraps wrong or misses the second coercion.

**Why it happens:**
Coercion is a *typed* transformation but the analyzer often has incomplete type information (no full type inference for identifiers). And `+` result-type propagation up a chain is overlooked.

**How to avoid:**
Give every expression node an inferred type: `NUMBER`, `STRING`, `BOOLEAN`, or `UNKNOWN`. Literals are known; identifiers resolve to their last-assigned type if statically determinable, else `UNKNOWN`. Coercion rule for `+`, evaluated bottom-up so chains propagate result types:
- both `NUMBER` → no coercion, result `NUMBER`
- both `STRING` → no coercion, result `STRING`
- one `STRING`, other `NUMBER`/`BOOLEAN` → wrap the non-string side in `str()`, result `STRING`
- any operand `UNKNOWN` → decide policy explicitly (either emit a runtime coercion helper `_atena_concat(a, b)` that checks types at runtime, OR require type to be inferable; the spec's "silent coercion never crashes" goal argues for the **runtime helper** so unknown-typed operands still never crash)
- otherwise → `Error on line N: cannot combine [type] and [type] → {source}`

Critically: because result type propagates, compute it bottom-up so `"a" + 1 + 2` correctly coerces both `1` and `2`.

**Warning signs:**
`"a" + 1 + 2` produces `"a1" + 2` (crash) instead of `"a12"`. `1 + "x"` wraps the string. `x + 1` (both numbers) emits `str(x) + 1`. The analyzer has no notion of expression result type.

**Phase to address:** Analyzer (type inference + coercion injection), Generator (emits `str()` / helper)

---

### Pitfall 11: The "cannot combine [type] and [type]" error path is wrong or missing

**What goes wrong:**
The error case (e.g., `list + number`, `boolean + boolean` if disallowed) either isn't detected, is reported with the wrong type names, or names the operands in the wrong order relative to the source.

**Why it happens:**
The coercion logic handles the happy paths and falls through to "no coercion" for the error cases, silently emitting code that crashes at runtime — defeating the no-stack-traces promise.

**How to avoid:**
Make the coercion function total: every (left-type, right-type) pair maps to exactly one outcome — no-coerce, coerce-left, coerce-right, or error. There is no implicit fall-through. The error message uses the human type names in source order. Add a table-driven test covering every type-pair combination.

**Warning signs:**
Some type combination produces Python that throws `TypeError` at runtime. Error names types in a confusing order. No exhaustive type-pair test exists.

**Phase to address:** Analyzer

---

### Pitfall 12: Cascading / duplicate errors after one real error

**What goes wrong:**
One real mistake (e.g., undefined variable `total`) triggers a flood of follow-on errors (`total` used on five later lines → five "undefined" errors; a parse error mid-expression spawns errors for every subsequent token). The learner sees 20 errors for one typo — the opposite of the friendly experience promised.

**Why it happens:**
Error recovery without *suppression*. Each phase keeps reporting derived problems caused by the first.

**How to avoid:**
- Analyzer: once a variable is reported undefined, record it in the symbol table as a poisoned/known entry so later uses don't re-report. Use an `ERROR`/`UNKNOWN` type that suppresses downstream type errors (an `UNKNOWN`-typed operand never produces a coercion error).
- Parser: on a syntax error, recover to a synchronization point (end of statement / next NEWLINE or DEDENT) before resuming, so one bad line yields one error, not one-per-token.
- Deduplicate the final error list (same line + same message → collapse).

**Warning signs:**
A single typo yields a wall of errors. The same message repeats per usage. No test asserts the *count* of errors for a known-bad input.

**Phase to address:** Parser (sync points), Analyzer (poisoned symbols, UNKNOWN suppression)

---

### Pitfall 13: Parser infinite loop when a token isn't consumed on error

**What goes wrong:**
The parser hits an unexpected token, records an error, but its main loop doesn't advance past the offending token. Next iteration sees the same token, records the same error, forever — the transpiler hangs.

**Why it happens:**
Error-recovery code reports the error and `continue`s without consuming a token. The "always make progress" invariant is violated.

**How to avoid:**
Enforce the invariant: **every** error-recovery path must consume at least one token (or reach a sync point that does). Add a loop guard in the top-level parse loop: track the token position at loop entry; if a full iteration ends at the same position, force-advance one token and assert (defensive) so the bug surfaces in tests instead of hanging. Cap total iterations as a backstop.

**Warning signs:**
Tests time out on malformed input. The parser hangs on a specific bad file. Error-recovery branches lack a `self.advance()`.

**Phase to address:** Parser

---

### Pitfall 14: Errors not ordered by line; unbounded error output

**What goes wrong:**
Because errors are collected across phases, they can come out in phase order (all lexer errors, then all parser errors) rather than source order — so line 50's error prints before line 3's. And a pathological file can emit thousands of errors, burying the real ones.

**Why it happens:**
Each phase appends to its own list; nobody sorts the merged list. No cap is applied.

**How to avoid:**
Every error carries a line number. Merge all phases' errors and sort by `(line, column)` before printing. Cap output at a sane limit (e.g., first 50) with a trailing "...and N more errors." Stable-sort so same-line errors keep insertion order.

**Warning signs:**
Errors print out of source order. A stress-test file prints 10,000 errors. Errors lack a line field, making sorting impossible.

**Phase to address:** CLI / error-reporting layer (shared), enforced by every phase recording line numbers

---

### Pitfall 15: Generated Python has invalid indentation

**What goes wrong:**
The generator emits Python with inconsistent indentation (mixing widths, off-by-one nesting), so the *generated* file is itself a Python `IndentationError` — the learner sees a Python stack trace, the one thing the product promises never happens.

**Why it happens:**
Indentation is generated by string concatenation with an ad-hoc depth counter that drifts. Nested blocks (loop inside if inside function) compound the drift.

**How to avoid:**
Track an explicit integer indent level; emit `"    " * level` (4 spaces, consistently) at the start of every statement line. Increment on entering a block, decrement on exit, in `try/finally`-style paired calls so they can't get out of sync. After generation, **parse the emitted Python with `ast.parse()` or `compile()`** as a build-time self-check; if it fails, that's an internal bug (not a user error) and tests must catch it.

**Warning signs:**
Generated `.py` won't import/compile. Deeply nested programs misbehave. The generator builds indentation by hand without a paired enter/exit.

**Phase to address:** Generator (+ Testing: compile-check every generated output)

---

### Pitfall 16: Forgetting the trailing colon on Python block headers

**What goes wrong:**
Atena has no colons; Python requires them. `if x > 1` must become `if x > 1:`. Omitting the colon on any block header (`if`, `else`, `while`/`for` from `repeat`, `function`/`def`) produces a Python `SyntaxError`.

**Why it happens:**
Each block-header generator is written separately; one forgets the colon. Easy to miss `else:` specifically (it has no condition).

**How to avoid:**
Centralize block-header emission in one helper that always appends `:` and the newline, used by every block construct. The `ast.parse()` self-check from Pitfall 15 catches any miss immediately.

**Warning signs:**
A specific construct (often `else` or a bare loop) yields a `SyntaxError`. Colon is appended in some generators but not others.

**Phase to address:** Generator (+ compile-check)

---

### Pitfall 17: `repeat N times` loop-variable name collision

**What goes wrong:**
`repeat 3 times` generates `for _i in range(3):`. Nested repeats both use `_i` — the inner `for _i` shadows the outer, breaking the outer loop's count if it referenced `_i` (and even if not, it's a latent bug). Or `_i` collides with a user variable named `_i` (unlikely but possible) or with a nested-loop counter.

**Why it happens:**
A hardcoded throwaway name reused at every nesting level.

**How to avoid:**
Generate a *unique* loop variable per `repeat`, e.g., a monotonic counter `_atena_i0`, `_atena_i1`, … or a name guaranteed not to clash with any user identifier (prefix that user identifiers can't produce). Since `repeat` counters are never user-visible, uniqueness is free. Test nested `repeat` blocks explicitly.

**Warning signs:**
Nested `repeat` loops run the wrong number of times. Two `for` loops in generated code share a variable name.

**Phase to address:** Generator

---

### Pitfall 18: Atena identifiers collide with Python reserved words

**What goes wrong:**
A learner names a variable or function `class`, `lambda`, `import`, `yield`, `is`, `None`, `True`, etc. These are legal Atena identifiers but illegal Python — the generated code is a `SyntaxError`, surfacing a Python error to the learner.

**Why it happens:**
The generator emits Atena names verbatim as Python names, assuming the identifier sets overlap. They don't — Python has ~35 keywords plus soft keywords Atena doesn't reserve.

**How to avoid:**
At generation, map any Atena identifier that is a Python keyword to a safe mangled form (e.g., append a reserved suffix: `class` → `class_atena`), consistently for both declaration and use so references still resolve. Maintain the mapping in the analyzer's symbol table so the same Atena name always maps to the same Python name within scope. Keep a list of Python keywords (`keyword.kwlist` is available in the stdlib) as the source of truth. Test with a program that uses several Python keywords as Atena variable names.

**Warning signs:**
A program using `class` or `import` as a variable name crashes with a Python `SyntaxError`. Identifiers are emitted without keyword checking.

**Phase to address:** Analyzer (assign safe names) + Generator (emit them)

---

### Pitfall 19: Dict dot-write vs dot-read generate inconsistently

**What goes wrong:**
Atena dictionaries accessed via dot (`student.name`) must become Python subscript (`student["name"]`) since Python objects don't support attribute access on dicts. The read path (`show student.name`) and the write path (`set student.name to "x"`) are generated by different code, and one uses `student["name"]` while the other emits `student.name` (an `AttributeError` at runtime) — or they disagree on quoting the key.

**Why it happens:**
Read and write are handled in separate AST node types / generator branches. The dot-to-subscript rewrite is applied in one but not the other.

**How to avoid:**
Normalize dot-access to a single subscript AST node in the analyzer (one rewrite, both read and write inherit it). The generator then emits `dict["key"]` uniformly. Test round-trips: write then read the same key, run the generated Python, assert the value.

**Warning signs:**
Reading a dict field works but writing it throws `AttributeError` (or vice versa). The key is quoted in one path, bare in the other.

**Phase to address:** Analyzer (normalize), Generator (uniform emission)

---

### Pitfall 20: Functions — defined-before-called not enforced (or over-enforced)

**What goes wrong:**
The spec requires defined-before-called *without* hoisting. Two failure modes: (a) the analyzer doesn't check, so calling an undefined function emits Python that throws `NameError`; (b) the analyzer checks but uses a single global pass that effectively hoists (sees all definitions first), wrongly accepting a call that appears before its definition.

**Why it happens:**
Python itself hoists `def` (functions are resolved at call time, not definition order), so naive generation "works" in Python even when Atena should reject it — masking the missing check.

**How to avoid:**
The analyzer walks the program top-to-bottom maintaining a set of *already-defined* function names. A call to a name not yet in the set is an error (`Error on line N: function 'foo' is called before it is defined → {source}`). Do not pre-scan all definitions. Test a call-before-def program and assert it errors *at analysis time*, not at Python runtime.

**Warning signs:**
Calling a function before its definition runs fine (Python hoisted it) instead of erroring. The function check is a single global symbol gather.

**Phase to address:** Analyzer

---

### Pitfall 21: Function arity check missing or with unhelpful messages; `return` outside a function

**What goes wrong:**
- Calling a function with the wrong number of arguments emits Python that throws `TypeError: f() takes 2 positional arguments but 3 were given` — a Python error reaches the learner.
- A `return` statement outside any function emits Python with a `SyntaxError: 'return' outside function`.

**Why it happens:**
The analyzer records function definitions but not their parameter counts, or doesn't track "am I currently inside a function body" when validating `return`.

**How to avoid:**
- Store each function's arity (parameter count) in the symbol table at definition. At each call, compare argument count to arity; mismatch → plain-English error naming the function, expected count, and given count.
- Track a "function depth" during analysis; a `return` at depth 0 → `Error on line N: 'return' can only be used inside a function → {source}`.
Test wrong-arity calls (too few, too many) and a top-level `return`.

**Warning signs:**
Wrong-argument-count calls produce Python `TypeError`. Top-level `return` produces Python `SyntaxError`. Symbol table stores names but not arities.

**Phase to address:** Analyzer

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Compute INDENT/DEDENT in the parser instead of the lexer | One fewer phase boundary | Tangles indentation state with grammar; every parser path must track columns; CPython explicitly moved this *out* of the parser for good reason | Never — keep it in the lexer |
| Emit `items[i - 1]` directly for variable indices | Less codegen | Silently breaks negatives-are-errors and the `i==0` case (Pitfall 5); produces wrong-but-running code | Never |
| Hardcode precedence in if/elif chains instead of a table | Quick to write first operator | Adding/reordering operators flips precedence subtly; no single source of truth | Only for a throwaway spike |
| Skip the `ast.parse()` self-check on generated Python | Faster build | Lets invalid Python (bad indent, missing colon) reach the learner as a stack trace — violates core value | Never for shipped builds |
| Reuse `_i` for every `repeat` loop | Simpler generator | Nested-loop corruption (Pitfall 17) | Never — unique names are free |
| Fail-fast on first error during early development | Simpler control flow | Must be undone later; error-recovery (poisoning, sync points) is architectural, not bolt-on | Only within a single phase's earliest TDD iterations, with a tracked task to add recovery before the phase is "green" |
| Treat all identifiers as UNKNOWN type (skip inference) | No type tracking needed | Either over-coerces or can't decide coercion; pushes everything to a runtime helper (slower, but safe) | Acceptable as a deliberate v1.0 simplification *if* paired with a runtime coercion helper so behavior stays correct |

## Integration Gotchas

The only "external service" is the Python runtime the generated code targets and runs on.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Python runtime (generated code execution in `atena run`) | Letting a Python exception from generated code reach the user as a raw traceback | Wrap execution; map any leaked Python exception to a plain-English Atena error, ideally tied back to an Atena line via injected line markers/helpers |
| Python `ast`/`compile` for self-check | Not running it, or treating its failure as a user error | Run `ast.parse()` on every generated program at build time; a failure is an *internal transpiler bug*, surfaced in tests, never shown to the user |
| Python keyword set | Hardcoding an outdated keyword list | Use `keyword.kwlist` (and `keyword.softkwlist`) from the stdlib as the source of truth for identifier mangling (Pitfall 18) |
| Negative indexing semantics | Assuming Python bounds-checks negatives like Atena wants | Python treats negatives as from-the-end; enforce Atena's "≥1" rule explicitly via the index helper (Pitfall 5) |

## Performance Traps

This is a single-file, offline transpiler for teaching programs — performance is not a scaling concern. The only "performance" failure is non-termination, covered as a correctness bug.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Parser infinite loop on malformed input (Pitfall 13) | Transpiler hangs; test timeout | Progress invariant + loop guard | Any malformed file; not scale-related |
| Unbounded error list on pathological input (Pitfall 14) | Huge output, slow print | Cap at ~50 errors with "...N more" | Adversarial/garbage input |
| Deep recursion in Pratt parser on deeply nested expressions | Python `RecursionError` | Acceptable for teaching-scale programs; optionally cap nesting depth with a friendly error | Pathological nesting only (hundreds deep) |

## Security Mistakes

Minimal attack surface (offline CLI, learner's own code), but `atena run` executes generated code.

| Mistake | Risk | Prevention |
|---------|------|------------|
| `atena run` uses `exec()`/`eval()` on generated code without consideration | The learner's own code runs with full Python privileges; the *transpiler itself* could be tricked if codegen ever interpolated source text unescaped | Generated Python comes from a typed AST, never from raw string interpolation of user source — so no injection path; keep it that way (never `f"...{user_source}..."` into emitted code) |
| Reading arbitrary file paths from CLI args without validation | Path traversal when reading the `.atena` file | Standard: resolve/validate the input path; low risk for a local CLI |
| Writing the `.py` output to an attacker-influenced path (`atena build`) | Overwriting unintended files | Write next to the source or to an explicit `-o` path only |

## UX Pitfalls

The product *is* the error experience — these are first-class, not afterthoughts.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Error message names a Python concept (`NoneType`, `IndentationError`, `traceback`) | Breaks the "never see Python" promise; confuses a non-programmer | Every error is plain English, names the Atena line and shows the offending source line, per the `Error on line N: ... → {source}` format |
| One typo produces 20 cascading errors (Pitfall 12) | Overwhelms a beginner; hides the real problem | Suppress derived errors (poisoned symbols, parser sync) so one mistake ≈ one error |
| Errors printed out of source order (Pitfall 14) | Learner can't map errors to their code top-to-bottom | Sort all errors by line before printing |
| The deliberate `items[0]` error message is generic | Misses the teaching moment | Use the specific, instructive message: "Lists in Atena start at 1, not 0" |
| Generated Python crashes at runtime with a traceback | Worst-case: the promise is broken at the moment of running code | Compile-check generated output; wrap runtime execution; index/coercion helpers raise Atena errors, not Python ones |

## "Looks Done But Isn't" Checklist

- [ ] **Lexer INDENT/DEDENT:** Often missing EOF drain and the unmatched-dedent assertion — verify with a file ending mid-block and a staircase-dedent file.
- [ ] **Lexer blank/comment lines:** Often still touch the indent stack — verify an indented blank line and a deeply-indented comment don't change the parse.
- [ ] **Variable index shift:** Often emits bare `[i-1]` — verify `items[i]` with `i=0` and `i` negative both raise the Atena error, not return an element.
- [ ] **Coercion chains:** Often only inspects leaf types — verify `"a" + 1 + 2` produces `"a12"` by *running* the generated Python.
- [ ] **Coercion error path:** Often falls through silently — verify every disallowed type-pair produces a plain-English error, not runtime `TypeError`.
- [ ] **Parser error recovery:** Often lacks the progress invariant — verify malformed input terminates (no hang) and yields a bounded, deduplicated error count.
- [ ] **Generated Python validity:** Often not compile-checked — verify every generator test runs `ast.parse()`/`compile()` on its output.
- [ ] **Trailing colons:** Often missed on `else` and bare loops — covered by the compile-check.
- [ ] **Nested `repeat`:** Often shares `_i` — verify nested repeats run the correct counts.
- [ ] **Python keyword identifiers:** Often unhandled — verify a program using `class`/`import` as variable names transpiles and runs.
- [ ] **Dict dot read/write parity:** Often inconsistent — verify write-then-read round-trips by running the generated code.
- [ ] **Function rules:** Often miss call-before-def, arity, and top-level `return` — verify each errors at *analysis* time, before any Python runs.
- [ ] **Error ordering & cap:** Often phase-ordered/unbounded — verify multi-error output is line-sorted and capped.
- [ ] **End-to-end golden program runs:** Often only the AST/text is checked — verify the spec's canonical example transpiles AND the generated Python actually executes to the expected output.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Index double-shift / bare `[i-1]` shipped (5, 6) | MEDIUM | Centralize conversion in analyzer, route all subscripts through the index helper, add `i=0`/negative/nested tests; re-verify every example program's output |
| INDENT/DEDENT structural bug | MEDIUM | Rewrite lexer indentation to the exact CPython stack algorithm; add staircase/EOF/blank/comment test suite; re-run all golden parses |
| Coercion wrong-operand / chain bug (10) | MEDIUM | Add expression result-type field, evaluate coercion bottom-up, add exhaustive type-pair + chain tests that *run* the output |
| Cascading errors / parser hang (12, 13) | MEDIUM | Add poisoned-symbol suppression, parser sync points, and the progress-invariant loop guard; add error-count and timeout tests |
| Generated invalid Python (15, 16) | LOW | Add `ast.parse()` self-check to the generator test harness; it pinpoints the exact construct |
| Keyword-collision / dict parity (18, 19) | LOW | Add identifier mangling map and dot-to-subscript normalization in the analyzer; add targeted tests |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Unmatched-level dedent | Lexer | Staircase-dedent file errors; assertion fires |
| 2. EOF doesn't close blocks | Lexer | Mid-block-EOF and no-trailing-newline files parse cleanly |
| 3. Blank/comment-line spurious tokens | Lexer | Indented blank line & deep comment don't change parse |
| 4. Mixed tabs/spaces | Lexer | Tab-in-space file errors with plain-English message |
| 5. Variable index shift / `i==0` last-element | Analyzer + Generator + Testing | `items[i]` with `i=0` and negative `i` raise Atena error when run |
| 6. Double-shift | Analyzer | `items[2]`→`items[1]`; nested `grid[2][3]`→`grid[1][2]` |
| 7. Unary vs binary minus | Parser | `-5`, `5 - 3`, `a - -b`, `-a + b` parse and evaluate correctly |
| 8. Precedence/associativity | Parser | `2+3*4`=14, `10-3-2`=5, logical precedence tests |
| 9. Postfix chaining | Parser | `a[1].b(c)`, `a[1][2]`, chain inside larger expr |
| 10. Coercion operand/chain | Analyzer + Generator | `"a"+1+2`="a12", `1+"x"` wraps the 1, `x+1` (numbers) untouched — all by running output |
| 11. "Cannot combine" error path | Analyzer | Exhaustive type-pair test; no runtime `TypeError` |
| 12. Cascading/duplicate errors | Parser + Analyzer | One typo → one error; error count asserted |
| 13. Parser infinite loop | Parser | Malformed input terminates; loop guard tested |
| 14. Error order & cap | CLI/error layer (all phases record lines) | Multi-error output line-sorted and capped |
| 15. Invalid generated indentation | Generator + Testing | `ast.parse()` self-check on all outputs |
| 16. Missing trailing colon | Generator + Testing | Compile-check catches `else`/loop misses |
| 17. `repeat` `_i` collision | Generator | Nested `repeat` runs correct counts |
| 18. Python-keyword identifiers | Analyzer + Generator | `class`/`import` as variable names transpile and run |
| 19. Dict dot read/write parity | Analyzer + Generator | Write-then-read round-trip runs correctly |
| 20. Defined-before-called (no hoisting) | Analyzer | Call-before-def errors at analysis time |
| 21. Arity + `return` outside function | Analyzer | Wrong-arity and top-level `return` error at analysis time |

**Cross-cutting testing principle (applies to every phase):** Because the product's value is *runnable, correct Python with plain-English errors*, golden-text tests are necessary but insufficient. Three test layers are required: (1) golden token/AST/text snapshots, kept minimal to avoid brittleness; (2) **execution tests** that run the generated Python and assert its *output* (catches index, coercion, codegen-semantics bugs that text snapshots miss); (3) **error-path tests** that feed known-bad programs and assert the exact plain-English errors, their count, and their line order (catches cascading/ordering/recovery bugs). Brittle golden tests that snapshot huge outputs should be avoided in favor of targeted assertions; and no phase is "green" until its error paths are tested, not just its happy path.

## Sources

- Python Language Reference, §2 Lexical Analysis — INDENT/DEDENT stack algorithm, blank/comment-line handling, EOF DEDENT generation, tab/space TabError rule (HIGH): https://docs.python.org/3/reference/lexical_analysis.html
- "A Deep Dive into Python's Tokenizer" — Benjamin Woodruff, on CPython moving indentation handling into the tokenizer (MEDIUM): https://benjam.info/blog/posts/2019-09-18-python-deep-dive-tokenizer/
- "Pratt Parsers: Expression Parsing Made Easy" — Bob Nystrom, on nud/led prefix-vs-infix split for unary/binary minus and precedence/associativity via binding power (HIGH, canonical reference): https://journal.stuffwithstuff.com/2011/03/19/pratt-parsers-expression-parsing-made-easy/
- "Top-Down operator precedence (Pratt) parsing" — Eli Bendersky, on nud/led and associativity control (HIGH): https://eli.thegreenplace.net/2010/01/02/top-down-operator-precedence-parsing/
- Python negative-index semantics (`-n`..`n-1`, `-1` = last element) — confirms the `items[i-1]` `i==0` trap (HIGH): https://docs.python.org/3/reference/lexical_analysis.html and general Python sequence semantics
- Project specification: /Users/juliorcoelho/atena-lang/.planning/PROJECT.md (source of truth for Atena v1.0 rules)

---
*Pitfalls research for: teaching transpiler (Atena → Python 3)*
*Researched: 2026-06-13*
