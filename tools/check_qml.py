"""QML analysis and rewrites with the repository's ``qs`` imports available."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from check_common import ROOT, CheckError, format_source, run_tool


@contextmanager
def qml_import_root() -> Iterator[Path]:
    try:
        directory = tempfile.TemporaryDirectory(prefix="inir-qml-imports-")
    except OSError as error:
        raise CheckError(f"cannot prepare QML import root: {error}") from error
    with directory as name:
        root = Path(name)
        (root / "qs").symlink_to(ROOT, target_is_directory=True)
        yield root


def run_qml_check(target: str, paths: list[Path]) -> None:
    if target in ("format", "format-check"):
        for path in paths:
            format_source(target, path, ["qmlformat", "--ignore-settings", str(path)])
        return
    with qml_import_root() as import_root:
        if target == "lint-fix":
            _fix_qml(paths, import_root)
        else:
            _report_lint_result(_lint(paths, import_root), paths)


def _lint(paths: list[Path], import_root: Path) -> subprocess.CompletedProcess:
    return run_tool(
        ["qmllint", "-E", "-I", str(import_root), "--json", "-", *map(str, paths)],
        stdout=subprocess.PIPE,
    )


def _is_missing_import(warning: dict) -> bool:
    if warning["id"] != "import":
        return False
    message = warning["message"]
    if message.startswith(("Failed to import ", "Cannot load type description")):
        return True
    message = message.lower()
    return "module" in message and "not installed" in message


def _diagnostics(
    returncode: int, output: bytes, paths: list[Path]
) -> tuple[list[dict], bool, bool]:
    if returncode not in (0, 255) or not output:
        raise CheckError(f"qmllint failed with status {returncode}")
    try:
        entries = json.loads(output)["files"]
        if len(entries) != len(paths) or {
            Path(item["filename"]) for item in entries
        } != set(paths):
            raise ValueError("qmllint omitted selected files")
        for entry in entries:
            Path(entry["filename"]).relative_to(ROOT)
            warnings = entry["warnings"]
            if not entry["success"] and not warnings:
                raise ValueError("qmllint could not read a selected file")
        return (
            entries,
            any(item["warnings"] for item in entries),
            any(
                _is_missing_import(warning)
                for entry in entries
                for warning in entry["warnings"]
            ),
        )
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise CheckError(f"invalid qmllint JSON diagnostics: {error}") from error


def _report_lint_result(result: subprocess.CompletedProcess, paths: list[Path]) -> None:
    _report_diagnostics(
        result.returncode, *_diagnostics(result.returncode, result.stdout, paths)
    )


def _report_diagnostics(
    returncode: int, entries: list[dict], has_diagnostics: bool, missing_import: bool
) -> None:
    for entry in entries:
        path = Path(entry["filename"]).relative_to(ROOT)
        for warning in entry["warnings"]:
            position = (
                f":{warning['line']}:{warning.get('column', 0)}"
                if "line" in warning
                else ""
            )
            print(
                f"{path}{position}: {warning['type']} [{warning['id']}]: {warning['message']}"
            )
    if missing_import:
        raise CheckError(
            "qmllint could not resolve required QML imports or metadata; "
            "install Qt/Quickshell QML modules and set QML_IMPORT_PATH"
        )
    if returncode and not has_diagnostics:
        raise CheckError(f"qmllint failed with status {returncode}")


def _fix_qml(paths: list[Path], import_root: Path) -> None:
    changed = []
    diagnostics = import_root / "diagnostics.json"
    for path in paths:
        diagnostics.unlink(missing_ok=True)
        result = run_tool(
            [
                "qmllint",
                "-E",
                "-I",
                str(import_root),
                "--fix",
                "--dry-run",
                "--json",
                str(diagnostics),
                str(path),
            ],
            stdout=subprocess.PIPE,
        )
        if not diagnostics.is_file():
            raise CheckError(
                f"qmllint did not produce diagnostics for {path.relative_to(ROOT)}"
            )
        entries, has_diagnostics, missing_import = _diagnostics(
            result.returncode, diagnostics.read_bytes(), [path]
        )
        if missing_import:
            _report_diagnostics(result.returncode, entries, has_diagnostics, True)
        suggestions = [
            suggestion
            for warning in entries[0]["warnings"]
            for suggestion in warning.get("suggestions", [])
            if suggestion.get("isAutoApplicable")
        ]
        if not suggestions:
            _report_diagnostics(result.returncode, entries, has_diagnostics, False)
            continue
        if any(
            Path(edit["filename"]) != path
            for suggestion in suggestions
            for edit in suggestion.get("documentEdits", [])
        ):
            raise CheckError(
                f"qmllint fix for {path.relative_to(ROOT)} targets another file"
            )
        if not result.stdout or result.returncode:
            raise CheckError(
                f"qmllint could not apply an available fix to {path.relative_to(ROOT)}"
            )
        path.write_bytes(result.stdout)
        changed.append(path)
    if changed:
        _report_lint_result(_lint(changed, import_root), changed)
