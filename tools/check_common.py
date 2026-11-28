"""Shared process and repository context for the static check adapters."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CheckError(Exception):
    """A requested check could not be completed."""


def run_tool(command: list[str], *, cwd: Path = ROOT, **options) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, cwd=cwd, check=False, **options)
    except FileNotFoundError as error:
        raise CheckError(f"{command[0]} not found; install it and add it to PATH") from error
    except OSError as error:
        raise CheckError(f"cannot start {command[0]}: {error}") from error


def format_source(target: str, path: Path, command: list[str]) -> None:
    result = run_tool(command, stdout=subprocess.PIPE)
    relative = path.relative_to(ROOT)
    if result.returncode:
        raise CheckError(f"{command[0]} could not format {relative} (status {result.returncode})")
    if result.stdout == path.read_bytes():
        return
    if target == "format-check":
        print(f"{relative}: formatting differs")
    else:
        path.write_bytes(result.stdout)
