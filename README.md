# Atena

**[atena-lang.org](https://atena-lang.org)**

Atena is a teaching language that removes all the punctuation noise — no colons, no braces — so you can focus on learning how programs think. It transpiles (converts) to Python 3, which means the code you write is real: it runs, it handles data, and it teaches you the algorithmic logic professionals use every day. The best part: `atena build --show` reveals the Python it generated, so you always know exactly what real language you are growing toward.

Atena is for complete beginners who want to learn algorithmic logic without fighting syntax. If you have never written a line of code, this is your starting point.

---

## Install

From the repo root, run:

```
pip install .
```

This places the `atena` command on your PATH. That is the only step.

If you plan to contribute or make changes, use an editable install instead:

```
pip install -e .
```

---

## Write your first program

Create a file called `hello.atena` with these two lines:

```
show "Hello, world!"
show "Today's count: " + 5
```

Then run it:

```
atena run hello.atena
```

You will see:

```
Hello, world!
Today's count: 5
```

The second line works because Atena handles the string-plus-number combination for you automatically — you never need to worry about converting types.

---

## Running and building programs

Atena gives you two verbs:

| Command | What it does |
|---------|--------------|
| `atena run file.atena` | Transpiles your program and runs it immediately |
| `atena build file.atena` | Translates your program to Python and saves `file.py` |
| `atena build --show file.atena` | Saves `file.py` and also prints the generated Python to the screen |

The `--show` flag is how you peek at the Python that Atena wrote for you — a direct window into the language you are learning toward.

---

## When you make a mistake

Every programmer makes mistakes. Atena's job is to help you find them quickly, without confusion.

Say you write this program:

```
score = 90
show "Result: " + result
```

You meant to write `score`, but you wrote `result` instead. When you run it, Atena tells you:

```
Error on line 2: I don't know what "result" is yet. Did you forget to create it first?
  → show "Result: " + result
```

Atena always tells you the exact line, shows you the offending code, and never dumps a wall of programming internals. It is your safety net.

---

## Language basics

### Output

```
show "Hello!"
show 42
show "Your score is: " + score
```

### Input

```
name = ask "Enter your name: "
```

`ask` always gives you text. Store it in a variable and use it however you like.

### Variables

```
score = 10
greeting = "Hello"
```

### Arithmetic

```
total = 3 + 4
difference = 10 - 3
product = 6 * 7
quotient = 10 / 2
```

Atena uses integers only (whole numbers) — there are no decimals. Division always rounds down to a whole number, so `10 / 3` is `3` (not `3.33`). When you add a number to a string with `+`, Atena handles the conversion automatically.

### Comparisons

```
score == 10
score != 5
score > 6
score < 100
score >= 6
score <= 10
```

### if / else

```
if score >= 6
    show "Passing"
else
    show "Not yet"
```

Indentation (the spaces at the start of a line) marks the block. Use consistent spaces or tabs — do not mix them.

### while loop

```
i = 1
while i <= 5
    show i
    i = i + 1
```

The block runs as long as the condition is true.

### repeat loop

```
repeat 3 times
    show "again"
```

Use `repeat` when you know exactly how many times you want to loop.

### Functions

```
function double(n)
    return n * 2

show double(5)
```

Define a function with `function`, then call it by name. Functions can take parameters and return values.

### Lists (positions start at 1)

```
grades = [8, 9, 7]
show grades[1]
```

The first item is at position 1 — not 0. This is how Atena keeps things natural for beginners.

```
add 10 to grades
remove 8 from grades
show length(grades)
```

Use `add ... to` to append, `remove ... from` to delete a value, and `length` to count items.

### Dicts (dot notation)

```
person = {name = "Ana", age = 20}
show person.name
person.age = 21
```

A dict stores named values. Access and update them with a dot.

### Boolean values

```
passed = true
failed = false
```

### Logic operators

```
if score >= 6 and attendance == true
    show "Eligible"

if not passed
    show "Try again"
```

Use `and`, `or`, and `not` to combine conditions.

---

**Atena v1.0 uses double-quoted strings and integers only. No floats, no string escaping, no elif.**

---

## Examples

The `examples/` folder contains a 9-step concept ladder — one new idea per file:

| File | Concept |
|------|---------|
| `01-show.atena` | Output with `show` |
| `02-ask.atena` | Input with `ask` |
| `03-variables.atena` | Variables and arithmetic |
| `04-conditionals.atena` | `if` / `else` |
| `05-while.atena` | `while` loop |
| `06-repeat.atena` | `repeat` loop |
| `07-functions.atena` | Functions and `return` |
| `08-lists.atena` | Lists with 1-based indexing |
| `09-dicts.atena` | Dictionaries with dot access |

`school.atena` is the capstone that brings all nine concepts together in one program.

To run any example:

```
atena run examples/01-show.atena
```

---

## For teachers

The 9-rung concept ladder is designed as a classroom curriculum — each file covers one concept and fits naturally into a single ~50-minute class period. Every file opens with a short comment header naming the concept and uses inline notes to narrate the key lines, so the file teaches itself top-to-bottom even before a student opens this README. A student who works through all nine rungs has the foundation to write `school.atena` on their own as a capstone assignment. Atena's plain-English errors mean students see encouraging guidance rather than confusing programming internals — and the `atena build --show` command gives motivated students a bridge to the real Python language they are growing toward.
