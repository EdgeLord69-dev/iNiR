"""QML analysis and rewrites with the repository's ``qs`` imports available."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .check_common import ROOT, CheckError, format_source, run_tool


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
    if message.startswith(
        (
            "Failed to import ",
            "Cannot load type description",
            "Could not open qmldir file:",
            "QML types file ",
            "File or directory you are trying to import does not exist:",
        )
    ):
        return True
    message = message.lower()
    return "module" in message and "not installed" in message


def _diagnostics(
    returncode: int, output: bytes, paths: list[Path]
) -> tuple[list[dict], bool, int]:
    if returncode not in (0, 255) or not output:
        raise CheckError(f"qmllint failed with status {returncode}")
    try:
        report = json.loads(output)
        entries = report["files"]
        if len(entries) != len(paths) or {
            Path(item["filename"]) for item in entries
        } != set(paths):
            raise ValueError("qmllint omitted selected files")
        for entry in entries:
            path = Path(entry["filename"]).relative_to(ROOT)
            warnings = entry["warnings"]
            if not entry["success"] and (
                not warnings
                or any(
                    warning["message"].startswith("Failed to open file ")
                    for warning in warnings
                )
            ):
                raise CheckError(f"qmllint could not read {path}")
        return (
            entries,
            any(
                _is_missing_import(warning)
                for entry in entries
                for warning in entry["warnings"]
            ),
            report["revision"],
        )
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise CheckError(f"invalid qmllint JSON diagnostics: {error}") from error


def _report_lint_result(result: subprocess.CompletedProcess, paths: list[Path]) -> None:
    entries, missing_import, _ = _diagnostics(result.returncode, result.stdout, paths)
    _report_diagnostics(result.returncode, entries, missing_import)


def _report_diagnostics(
    returncode: int, entries: list[dict], missing_import: bool
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
    if returncode and not any(entry["warnings"] for entry in entries):
        raise CheckError(f"qmllint failed with status {returncode}")


def _fix_targets(entry: dict, revision: int, path: Path) -> set[Path]:
    if revision not in (3, 4, 6):
        raise CheckError(f"qmllint fix JSON revision {revision} is unsupported")
    targets: set[Path] = set()
    for warning in entry["warnings"]:
        for suggestion in warning.get("suggestions", []):
            applicable = (
                not suggestion["isHint"]
                if revision == 3
                else suggestion["isAutoApplicable"]
            )
            if not applicable:
                continue
            if revision == 6:
                targets.update(
                    ROOT / edit["filename"] for edit in suggestion["documentEdits"]
                )
            else:
                targets.add(ROOT / suggestion.get("fileName", path))
    return targets


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
        entries, missing_import, revision = _diagnostics(
            result.returncode, diagnostics.read_bytes(), [path]
        )
        if missing_import:
            _report_diagnostics(result.returncode, entries, True)
        try:
            targets = _fix_targets(entries[0], revision, path)
        except (KeyError, TypeError) as error:
            raise CheckError("invalid qmllint fix suggestions") from error
        if not targets:
            _report_diagnostics(result.returncode, entries, False)
            continue
        if targets != {path}:
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
