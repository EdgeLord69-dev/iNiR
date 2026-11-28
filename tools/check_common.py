"""Shared process and repository context for the static check adapters."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CheckError(Exception):
    """A requested check could not be completed."""


def shell_interpreter(path: Path) -> str | None:
    with path.open("rb") as source:
        line = source.readline(4096)
    if not line.startswith(b"#!"):
        return None
    words = line[2:].split()
    if not words:
        return None
    command = words[0].rsplit(b"/", 1)[-1]
    if command == b"env":
        command = next(
            (
                word.rsplit(b"/", 1)[-1]
                for word in words[1:]
                if not word.startswith(b"-") and b"=" not in word
            ),
            b"",
        )
    if command in (b"bash", b"sh", b"dash", b"ash", b"busybox", b"fish"):
        return command.decode("ascii")
    return None


def run_tool(
    command: list[str], *, cwd: Path = ROOT, **options
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, cwd=cwd, check=False, **options)
    except FileNotFoundError as error:
        raise CheckError(
            f"{command[0]} not found; install it and add it to PATH"
        ) from error
    except OSError as error:
        raise CheckError(f"cannot start {command[0]}: {error}") from error


def format_source(target: str, path: Path, command: list[str]) -> None:
    result = run_tool(command, stdout=subprocess.PIPE)
    relative = path.relative_to(ROOT)
    if result.returncode:
        raise CheckError(
            f"{command[0]} could not format {relative} (status {result.returncode})"
        )
    if result.stdout == path.read_bytes():
        return
    if target == "format-check":
        print(f"{relative}: formatting differs")
    else:
        path.write_bytes(result.stdout)
