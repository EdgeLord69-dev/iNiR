"""Package-aware static checks for Go source files."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from check_common import ROOT, CheckError, format_source, run_tool

_SOURCE_DIAGNOSTIC = re.compile(r"^(?:vet: )?.+\.go:\d+(?::\d+)?:")


def _source_failure(output: str) -> bool:
    lines = [
        line
        for line in output.splitlines()
        if line and not line.startswith(("#", " ", "\t"))
    ]
    return bool(lines) and all(
        _SOURCE_DIAGNOSTIC.match(line)
        or line.endswith(": function main is undeclared in the main package")
        for line in lines
    )


def _package(directory: Path) -> dict | None:
    result = run_tool(
        ["go", "list", "-e", "-json", "-mod=readonly", "."],
        cwd=directory,
        stdout=subprocess.PIPE,
    )
    relative = directory.relative_to(ROOT)
    if result.returncode:
        raise CheckError(f"go list failed in {relative} (status {result.returncode})")
    try:
        package = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise CheckError(
            f"go list returned invalid package data in {relative}"
        ) from error
    package_error = package.get("Error") or {}
    message = package_error.get("Err", "")
    dependency_errors = package.get("DepsErrors", [])
    if dependency_errors:
        details = "\n".join(error["Err"] for error in dependency_errors)
        raise CheckError(f"Go dependencies unavailable in {relative}:\n{details}")
    if package_error:
        if package.get("IgnoredGoFiles") and message.startswith(
            "build constraints exclude all Go files"
        ):
            print(f"{relative}: no Go files match the active build constraints")
            return None
        position = package_error.get("Pos", "")
        if _SOURCE_DIAGNOSTIC.match(f"{position}:") or message.startswith(
            "found packages "
        ):
            print(f"{relative}: {position + ': ' if position else ''}{message}")
            return None
        raise CheckError(f"go list could not load {relative}: {message}")
    return package


def _go_vet(directory: Path) -> None:
    result = run_tool(
        ["go", "vet", "-mod=readonly", "."],
        cwd=directory,
        stderr=subprocess.PIPE,
    )
    stderr = result.stderr.decode(errors="replace")
    sys.stderr.write(stderr)
    if result.returncode and not (result.returncode == 1 and _source_failure(stderr)):
        raise CheckError(
            f"go vet failed in {directory.relative_to(ROOT)} (status {result.returncode})"
        )


def _go_build(directory: Path) -> None:
    # The temporary output prevents go build from leaving an executable in the
    # source tree; the temporary directory is removed on every exit path.
    with tempfile.TemporaryDirectory(prefix="inir-go-check-") as temporary:
        result = run_tool(
            [
                "go",
                "build",
                "-json",
                "-mod=readonly",
                "-buildvcs=false",
                "-o",
                str(Path(temporary) / "check"),
                ".",
            ],
            cwd=directory,
            stdout=subprocess.PIPE,
        )
    output: dict[str, list[str]] = {}
    failures = set()
    for line in result.stdout.splitlines():
        try:
            item = json.loads(line)
            if item["Action"] == "build-output":
                text = item["Output"]
                output.setdefault(item["ImportPath"], []).append(text)
                sys.stderr.write(text)
            elif item["Action"] == "build-fail":
                failures.add(item["ImportPath"])
        except (ValueError, KeyError, TypeError) as error:
            raise CheckError(
                f"go build returned invalid output in {directory.relative_to(ROOT)}"
            ) from error
    if result.returncode and not (
        result.returncode == 1
        and failures
        and all(
            _source_failure("".join(output.get(package, []))) for package in failures
        )
    ):
        raise CheckError(
            f"go build failed in {directory.relative_to(ROOT)} (status {result.returncode})"
        )


def run_go_check(target: str, paths: list[Path]) -> None:
    if target == "lint-fix":
        print("Go lint-fix unsupported: no native Go lint-fix operation")
        return
    if target in ("format", "format-check"):
        for path in paths:
            format_source(target, path, ["gofmt", str(path)])
        return

    for directory in sorted({path.parent for path in paths}):
        package = _package(directory)
        if package is None:
            continue
        production = package.get("GoFiles") or package.get("CgoFiles")
        if target == "lint" and (
            production or package.get("TestGoFiles") or package.get("XTestGoFiles")
        ):
            _go_vet(directory)
        elif target == "typecheck" and production:
            _go_build(directory)
