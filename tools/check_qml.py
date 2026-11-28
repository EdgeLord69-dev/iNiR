"""Read-only QML analysis with the repository's ``qs`` imports available."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from check_common import ROOT, CheckError, run_tool


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


def run_qml_check(_target: str, paths: list[Path]) -> None:
    with qml_import_root() as import_root:
        result = run_tool(
            ["qmllint", "-E", "-I", str(import_root), "--json", "-", *map(str, paths)],
            stdout=subprocess.PIPE,
        )
    if result.returncode not in (0, 255) or not result.stdout:
        raise CheckError(f"qmllint failed with status {result.returncode}")
    try:
        entries = json.loads(result.stdout)["files"]
        if len(entries) != len(paths) or {Path(item["filename"]) for item in entries} != set(paths):
            raise ValueError("qmllint omitted selected files")
        missing_import = False
        has_diagnostics = False
        for entry in entries:
            path = Path(entry["filename"]).relative_to(ROOT)
            warnings = entry["warnings"]
            if not entry["success"] and not warnings:
                raise ValueError(f"qmllint could not read {path}")
            has_diagnostics |= bool(warnings)
            for warning in warnings:
                message = warning["message"]
                category = warning["id"]
                missing_import |= category == "import" and (
                    message.startswith(("Failed to import ", "Cannot load type description"))
                    or "module" in message.lower() and "not installed" in message.lower()
                )
                position = f":{warning['line']}:{warning.get('column', 0)}" if "line" in warning else ""
                print(f"{path}{position}: {warning['type']} [{category}]: {message}")
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise CheckError(f"invalid qmllint JSON diagnostics: {error}") from error
    if missing_import:
        raise CheckError(
            "qmllint could not resolve required QML imports or metadata; "
            "install Qt/Quickshell QML modules and set QML_IMPORT_PATH"
        )
    if result.returncode and not has_diagnostics:
        raise CheckError(f"qmllint failed with status {result.returncode}")
