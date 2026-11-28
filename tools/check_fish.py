"""Syntax and formatting checks for Fish source files."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .check_common import ROOT, CheckError, format_source, run_tool


def run_fish_check(target: str, paths: list[Path]) -> None:
    if target == "lint-fix":
        print("Fish lint-fix unsupported: Fish has no native syntax-fix operation")
        return

    for path in paths:
        if target != "lint":
            format_source(target, path, ["fish_indent", str(path)])
            continue

        result = run_tool(
            ["fish", "--no-config", "--no-execute", str(path)],
            stderr=subprocess.PIPE,
        )
        if result.stderr:
            sys.stderr.write(result.stderr.decode(errors="replace"))
        # Fish can also use 127 when opening the script fails.
        syntax_error = os.fsencode(path) + b" (line " in result.stderr
        if result.returncode and not (result.returncode in (123, 127) and syntax_error):
            raise CheckError(
                f"fish could not check {path.relative_to(ROOT)} "
                f"(status {result.returncode})"
            )
