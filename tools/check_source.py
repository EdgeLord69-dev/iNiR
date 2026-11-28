"""Run scoped, local static checks on first-party source files."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from .check_common import ROOT, CheckError, run_tool, shell_interpreter
from .check_fish import run_fish_check
from .check_go import run_go_check
from .check_qml import run_qml_check
from .check_shell import run_shell_check

LANGUAGES = {
    ".py": "python",
    ".pyi": "python",
    ".qml": "qml",
    ".sh": "shell",
    ".bash": "shell",
    ".dash": "shell",
    ".ash": "shell",
    ".fish": "fish",
    ".go": "go",
}
EXTENSIONLESS_SHELL = {"setup", "scripts/inir"}


def language(path: Path) -> str | None:
    kind = LANGUAGES.get(path.suffix)
    if kind == "shell" or not path.suffix:
        command = shell_interpreter(ROOT / path)
        if command:
            return "fish" if command == "fish" else "shell"
    return kind or ("shell" if path.as_posix() in EXTENSIONLESS_SHELL else None)


def git_records(*args: str) -> list[bytes]:
    result = subprocess.run(
        ["git", "--literal-pathspecs", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [item for item in result.stdout.split(b"\0") if item]


def checked_path(raw: str, submodules: set[Path]) -> Path:
    full = ROOT / raw
    try:
        resolved = full.resolve(strict=True)
        path = resolved.relative_to(ROOT)
    except (OSError, ValueError, RuntimeError) as error:
        raise CheckError(f"missing, invalid or external path: {raw!r}") from error
    if resolved != Path(os.path.abspath(full)):
        raise CheckError(f"symlinks are not supported: {raw!r}")
    if (
        path.parts[:1] == (".git",)
        or path in submodules
        or submodules.intersection(path.parents)
    ):
        raise CheckError(f"path is not in first-party source: {raw!r}")
    return path


def _indexed_paths() -> tuple[set[Path], set[Path]]:
    tracked: set[Path] = set()
    submodules: set[Path] = set()
    for record in git_records("ls-files", "--stage", "-z"):
        metadata, name = record.split(b"\t", 1)
        path = Path(os.fsdecode(name))
        mode = metadata.split(b" ", 1)[0]
        if mode == b"160000":
            submodules.add(path)
        elif mode != b"120000":
            tracked.add(path)
    return tracked, submodules


def _requested_paths(
    requested: list[str], tracked: set[Path], submodules: set[Path]
) -> set[Path]:
    if not requested:
        return tracked

    paths = set()
    directories = set()
    for raw in requested:
        if not raw:
            raise CheckError("empty path")
        candidate = checked_path(raw, submodules)
        full = ROOT / candidate
        if full.is_dir():
            directories.add(candidate)
        elif full.is_file() and language(candidate):
            paths.add(candidate)
        else:
            raise CheckError(f"unsupported source path: {raw!r}")

    if directories:
        paths.update(path for path in tracked if directories.intersection(path.parents))
        paths.update(
            Path(os.fsdecode(item))
            for item in git_records(
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                *sorted(map(str, directories)),
            )
        )
    return paths


def source_selection(requested: list[str]) -> dict[str, list[Path]]:
    tracked, submodules = _indexed_paths()
    paths = _requested_paths(requested, tracked, submodules)
    selected: dict[str, list[Path]] = {
        key: [] for key in ("python", "qml", "shell", "fish", "go")
    }
    for path in sorted(paths):
        full = ROOT / path
        if (
            not submodules.intersection(path.parents)
            and full.is_file()
            and full.resolve() == full
        ):
            kind = language(path)
            if kind:
                selected[kind].append(full)
    return selected


def python_lint(target: str, files: list[str]) -> None:
    fix = "--fix" if target == "lint-fix" else "--no-fix"
    result = run_tool(
        [
            "ruff",
            "check",
            "--no-cache",
            "--output-format=json",
            fix,
            "--no-unsafe-fixes",
            "--",
            *files,
        ],
        stdout=subprocess.PIPE,
    )
    if result.returncode not in (0, 1):
        raise CheckError(f"ruff check failed with status {result.returncode}")
    try:
        diagnostics = json.loads(result.stdout)
        failed = False
        for item in diagnostics:
            location = item["location"]
            path = Path(item["filename"]).relative_to(ROOT)
            code = item["code"]
            print(
                f"{path}:{location['row']}:{location['column']}: {code}: {item['message']}"
            )
            failed |= code in ("E902", "io-error")
    except (ValueError, TypeError, KeyError) as error:
        raise CheckError("invalid Ruff diagnostics") from error
    if failed or (result.returncode == 1 and not diagnostics):
        raise CheckError("ruff could not complete linting")


def python_typecheck(files: list[str]) -> None:
    result = run_tool(
        [
            "mypy",
            "--output=json",
            "--no-incremental",
            "--cache-dir=/dev/null",
            "--explicit-package-bases",
            "--",
            *files,
        ],
        stdout=subprocess.PIPE,
    )
    if result.returncode not in (0, 1, 2):
        raise CheckError(f"mypy failed with status {result.returncode}")
    try:
        missing_imports = False
        has_syntax_errors = False
        has_other_errors = False
        for line in result.stdout.strip().splitlines():
            item = json.loads(line)
            code = item["code"]
            print(
                f"{item['file']}:{item['line']}:{item['column']}: "
                f"{item['severity']}: {item['message']} [{code}]"
            )
            if item.get("hint"):
                print(item["hint"])
            if item["severity"] == "error":
                has_syntax_errors |= code == "syntax"
                has_other_errors |= code != "syntax"
            missing_imports |= code in ("import-not-found", "import-untyped")
    except (ValueError, TypeError, KeyError) as error:
        raise CheckError("invalid mypy diagnostics") from error
    if missing_imports:
        raise CheckError(
            "mypy is missing imports or type stubs; install the analysis dependencies"
        )
    if result.returncode == 2 and (not has_syntax_errors or has_other_errors):
        raise CheckError("mypy could not complete checking")
    if result.returncode == 1 and not (has_syntax_errors or has_other_errors):
        raise CheckError("mypy could not complete checking")


def run_python_check(target: str, paths: list[Path]) -> None:
    files = [str(path) for path in paths]
    if target in ("lint", "lint-fix"):
        python_lint(target, files)
    elif target == "typecheck":
        python_typecheck(files)
    else:
        mode = ["--check"] if target == "format-check" else []
        result = run_tool(["ruff", "format", "--no-cache", *mode, "--", *files])
        if result.returncode != 0 and not (mode and result.returncode == 1):
            raise CheckError(f"ruff format failed with status {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        choices=("check", "lint", "lint-fix", "format-check", "format", "typecheck"),
    )
    args = parser.parse_args()
    try:
        raw_paths = os.environ.get("PATHS")
        requested = shlex.split(raw_paths or "")
        rewriting = args.target in ("lint-fix", "format")
        if rewriting and raw_paths is not None and not requested:
            raise CheckError("PATHS is empty; omit it to rewrite all tracked source")
        selected = source_selection(requested)
        if rewriting:
            for paths in selected.values():
                for path in paths:
                    if path.stat().st_nlink > 1:
                        raise CheckError(
                            f"cannot rewrite hard-linked source: {path.relative_to(ROOT)}"
                        )
    except (CheckError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"source selection failed: {error}", file=sys.stderr)
        return 2
    aggregate = args.target == "check"
    targets = ("lint", "format-check", "typecheck") if aggregate else (args.target,)
    adapters = {
        "python": run_python_check,
        "qml": run_qml_check,
        "shell": run_shell_check,
        "fish": run_fish_check,
        "go": run_go_check,
    }
    failed = False
    for target in targets:
        for kind, adapter in adapters.items():
            if not selected[kind]:
                continue
            if target == "typecheck" and (
                kind in ("shell", "fish") or (aggregate and kind == "qml")
            ):
                continue
            try:
                adapter(target, selected[kind])
            except (CheckError, OSError) as error:
                print(f"{target} ({kind}) failed: {error}", file=sys.stderr)
                failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
