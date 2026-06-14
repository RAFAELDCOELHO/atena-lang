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
        # TODO Plan 03: replace _internal_error_message with _runtime_error_message for learner errors (D-04)
        try:
            code = compile(result, args.file, "exec")
            exec(code, {"__name__": "__main__"})  # noqa: S102
        except SystemExit:
            raise
        except BaseException as exc:  # learner program runtime error
            # Surface as a plain-English message (Plan 03 will refine this);
            # never let a Python traceback escape.
            print(_internal_error_message(exc), file=sys.stderr)
            sys.exit(1)
