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

from atena.pipeline import compile_for_run, transpile

# Names of the on-demand runtime helpers injected by codegen. Errors raised
# *inside* these frames must be attributed to the Atena call site, not to the
# helper's own (synthetic) line numbers.
_HELPER_FRAMES = frozenset({"_atena_index", "_atena_concat"})

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
    except (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError):
        # Surfaced verbatim — main() maps each to a friendly _file_error_message.
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

    Because ``atena run`` compiles the Atena AST directly (see
    ``pipeline.compile_for_run``), traceback line numbers ARE Atena source
    lines.  Frames inside injected runtime helpers (``_atena_index`` /
    ``_atena_concat``) carry synthetic lines, so they are skipped in favour of
    the nearest Atena call-site frame (CR-01).
    """
    # --- Pick the innermost frame that belongs to the learner's program ------
    tb_frames = traceback.extract_tb(exc.__traceback__)
    atena_lineno: int | None = None
    for frame in reversed(tb_frames):
        if frame.name in _HELPER_FRAMES:
            continue  # synthetic helper line — attribute to the call site instead
        atena_lineno = frame.lineno
        break

    # --- Map to Atena source line for the → display ---------------------------
    source_line = ""
    if atena_lineno is not None and 1 <= atena_lineno <= len(source_lines):
        source_line = source_lines[atena_lineno - 1].strip()

    # --- Dispatch on exception type (D-03 curated catalog) --------------------
    if isinstance(exc, ZeroDivisionError):
        message = "you tried to divide by zero — the denominator must not be 0."
    elif isinstance(exc, KeyError):
        key = exc.args[0] if exc.args else "unknown"
        message = f"that dictionary doesn't have a key called {key!r}."
    elif isinstance(exc, ValueError):
        # Only a failed list.remove (the one ValueError Atena programs can raise
        # by design) gets the specific message; every other ValueError is generic
        # rather than confidently-wrong (CR-02).
        if "not in list" in str(exc):
            message = "that item wasn't in the list, so it couldn't be removed."
        else:
            message = "while running your program, an error occurred."
    elif isinstance(exc, IndexError):
        if "List positions in Atena start at 1" in str(exc):
            message = "List positions in Atena start at 1, so there's no position 0 or a negative one."
        else:
            message = "that index is out of range — check how many items are in the list."
    else:
        # Generic fallback — no raw class name, no traceback (D-03, D-04)
        message = "while running your program, an error occurred."

    # --- Format (D-05). Omit a fabricated line number we cannot prove (IN-03) -
    if atena_lineno is not None:
        return f"Error on line {atena_lineno}: {message}\n  → {source_line}"
    return f"Error: {message}"


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

    if args.command == "build":
        # Guard against silently overwriting the learner's input (WR-01):
        # `atena build foo.py` would compute out_path == foo.py.
        out_path = os.path.splitext(args.file)[0] + ".py"
        if os.path.abspath(out_path) == os.path.abspath(args.file):
            print(
                'I can only build files ending in ".atena".',
                file=sys.stderr,
            )
            sys.exit(1)

        # Transpile to a source string (pipeline prints errors + returns None).
        try:
            result = transpile(source, args.file)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:
            print(_internal_error_message(exc), file=sys.stderr)
            sys.exit(1)
        if result is None:
            sys.exit(1)

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
        # run: compile the Atena AST so tracebacks map to Atena lines (CR-01).
        # Any failure of transpile/compile is an INTERNAL bug (incl. a codegen
        # SyntaxError) and must use the blame-free wording (D-04 / CR-03).
        try:
            code = compile_for_run(source, os.path.basename(args.file))
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:
            print(_internal_error_message(exc), file=sys.stderr)
            sys.exit(1)
        if code is None:
            sys.exit(1)

        # exec the learner's program — wrap so no traceback reaches the learner.
        try:
            exec(code, {"__name__": "__main__"})  # noqa: S102
        except (SystemExit, KeyboardInterrupt):
            raise  # deliberate exit / Ctrl-C is not a program error (WR-03)
        except BaseException as exc:  # learner program runtime error
            # Translate to plain-English canonical format (D-04/D-05).
            # Never surface a raw Python traceback or class name.
            print(_runtime_error_message(exc, source.splitlines()), file=sys.stderr)
            sys.exit(1)
