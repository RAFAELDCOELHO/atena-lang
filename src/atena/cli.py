"""
CLI entry point for the Atena transpiler.

Provides two subcommands:
  atena run file.atena   — transpile and execute
  atena build file.atena — transpile and write file.py

All user-facing errors are plain English. No raw Python exception output ever
reaches the learner. File-not-found and unreadable errors are surfaced as friendly
messages. Any unexpected internal exception is caught and converted to a
blame-free message pointing the learner to share their program for a fix.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback

from atena.pipeline import transpile

# ---------------------------------------------------------------------------
# argparse setup — built at module level so tests can import without side effects
# ---------------------------------------------------------------------------

_parser = argparse.ArgumentParser(
    prog="atena",
    description="Atena language transpiler",
)
_subparsers = _parser.add_subparsers(dest="command")

_run_parser = _subparsers.add_parser("run", help="Transpile and run an Atena program")
_run_parser.add_argument("file", metavar="FILE", help=".atena source file")

_build_parser = _subparsers.add_parser(
    "build", help="Transpile an Atena program to Python"
)
_build_parser.add_argument("file", metavar="FILE", help=".atena source file")
_build_parser.add_argument(
    "--show",
    action="store_true",
    help="Print generated Python 3 source to stdout",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_file(path: str) -> str:
    """Read and return the contents of the file at *path*.

    Raises FileNotFoundError if the file does not exist.
    Raises IsADirectoryError if *path* is a directory, not a file.
    Raises UnicodeDecodeError if the file is not valid UTF-8 text.
    Raises PermissionError if the file cannot be read for any other reason.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise
    except IsADirectoryError:
        raise
    except PermissionError:
        raise
    except UnicodeDecodeError:
        raise
    except OSError as exc:
        # Treat other OS-level read failures as generic unreadable
        raise PermissionError(str(exc)) from exc


def _file_error_message(path: str, exc: Exception) -> str:
    """Return a plain-English error message for a file I/O failure.

    Uses only the filename (basename) — never the full path — per T-00-05-04.
    """
    filename = os.path.basename(path)
    if isinstance(exc, FileNotFoundError):
        return f'I couldn\'t find a file called "{filename}".'
    if isinstance(exc, IsADirectoryError):
        return f'"{filename}" is a folder, not a file.'
    if isinstance(exc, UnicodeDecodeError):
        return (
            f'I couldn\'t read "{filename}"'
            " — it doesn't look like a text file."
        )
    return f'I couldn\'t read "{filename}".'


def _internal_error_message(exc: BaseException) -> str:
    """Return a blame-free plain-English message for an unexpected internal error.

    If *exc* carries an ``atena_line`` attribute (int), includes "near line N".
    """
    line = getattr(exc, "atena_line", None)
    if isinstance(line, int):
        return (
            f"Something went wrong inside Atena near line {line}"
            " — this isn't your fault."
            " Please share your program so we can fix it."
        )
    return (
        "Something went wrong inside Atena"
        " — this isn't your fault."
        " Please share your program so we can fix it."
    )


def _runtime_error_message(exc: BaseException, source_lines: list[str]) -> str:
    """Translate a learner-program runtime exception to a plain-English Atena message.

    Uses the Python traceback to extract the best-effort line number (D-07),
    then dispatches on the exception type (D-03 curated catalog) and formats
    the result using the canonical D-05 format:
        Error on line N: <message>
          → <source_line>

    Never surfaces raw exception class names, Python tracebacks, or the internal
    "Something went wrong inside Atena" wording — those are reserved for transpiler
    bugs caught by _internal_error_message() (D-04 split).
    """
    # --- Extract Python lineno from traceback (best-effort per D-07) ----------
    tb_frames = traceback.extract_tb(exc.__traceback__)
    python_lineno = tb_frames[-1].lineno if tb_frames else None

    # --- Map to Atena source line for the → display ---------------------------
    source_line = ""
    if python_lineno is not None and 1 <= python_lineno <= len(source_lines):
        source_line = source_lines[python_lineno - 1].strip()

    # --- Best-effort line number display (D-07) --------------------------------
    line_display: int | str = python_lineno if python_lineno is not None else "unknown"

    # --- Dispatch on exception type (D-03 curated catalog) --------------------
    if isinstance(exc, ZeroDivisionError):
        message = "you tried to divide by zero — the denominator must not be 0."
    elif isinstance(exc, KeyError):
        key = exc.args[0] if exc.args else "unknown"
        message = f"that dictionary doesn't have a key called {key!r}."
    elif isinstance(exc, ValueError):
        message = "that item wasn't in the list, so it couldn't be removed."
    elif isinstance(exc, IndexError):
        if "List positions in Atena start at 1" in str(exc):
            message = "List positions in Atena start at 1, so there's no position 0 or a negative one."
        else:
            message = "that index is out of range — check how many items are in the list."
    else:
        # Generic fallback — no raw class name, no traceback (D-03, D-04)
        message = "while running your program, an error occurred."

    return f"Error on line {line_display}: {message}\n  → {source_line}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point — called by the ``atena`` console script."""
    args = _parser.parse_args()

    if args.command is None:
        _parser.print_help()
        sys.exit(0)

    # --- File read (plain-English error on failure) --------------------------
    try:
        source = _read_file(args.file)
    except (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        print(_file_error_message(args.file, exc), file=sys.stderr)
        sys.exit(1)

    # --- Transpile (pipeline.py prints errors to stderr and returns None on failure) --
    try:
        result = transpile(source, args.file)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:
        print(_internal_error_message(exc), file=sys.stderr)
        sys.exit(1)

    # When transpile() returns None the error report has already been printed to stderr
    if result is None:
        sys.exit(1)

    if args.command == "build":
        out_path = os.path.splitext(args.file)[0] + ".py"
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(result)
        except OSError as exc:
            print(_file_error_message(out_path, exc), file=sys.stderr)
            sys.exit(1)
        print(f'Built "{os.path.basename(out_path)}".')
        if args.show:
            print(result)
    else:
        # run: exec the generated Python — wrap so no traceback reaches the learner
        try:
            code = compile(result, args.file, "exec")
            exec(code, {"__name__": "__main__"})  # noqa: S102
        except SystemExit:
            raise
        except BaseException as exc:  # learner program runtime error
            # Translate to plain-English canonical format (D-04/D-05).
            # Never surface a raw Python traceback or class name.
            print(_runtime_error_message(exc, source.splitlines()), file=sys.stderr)
            sys.exit(1)
