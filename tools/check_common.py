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
