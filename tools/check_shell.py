"""ShellCheck and shfmt checks for selected shell scripts."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from check_common import ROOT, CheckError, format_source, run_tool, shell_interpreter


def dialect(path: Path) -> str:
    command = shell_interpreter(path)
    return "bash" if command == "bash" or (command is None and path.suffix == ".bash") else "sh"


def _shellcheck(path: Path, shell: str, output: str, cwd: Path = ROOT) -> bytes:
    result = run_tool(
        ["shellcheck", "--norc", "--color=never", "--shell", shell, "--format", output,
         "--", str(path.relative_to(cwd))],
        cwd=cwd,
        stdout=subprocess.PIPE,
    )
    if result.returncode not in (0, 1):
        raise CheckError(f"shellcheck failed for {path.name} (status {result.returncode})")
    return result.stdout


def _fix(path: Path, shell: str) -> None:
    original = path.read_bytes()
    with tempfile.TemporaryDirectory(prefix="inir-shellcheck-") as directory:
        root = Path(directory)
        copy = root / "source.sh"
        copy.write_bytes(original)
        patch = _shellcheck(copy, shell, "diff", root)
        if not patch:
            return
        if not patch.startswith(b"--- a/source.sh\n+++ b/source.sh\n"):
            raise CheckError(f"shellcheck produced an unexpected patch for {path.relative_to(ROOT)}")
        result = run_tool(
            ["git", "apply", "--no-index", "--include=source.sh", "--whitespace=nowarn", "-"],
            cwd=root,
            input=patch,
        )
        if result.returncode or not copy.is_file():
            raise CheckError(f"shellcheck patch could not be applied to {path.relative_to(ROOT)}")
        fixed = copy.read_bytes()
        if fixed == original:
            raise CheckError(f"shellcheck patch made no change to {path.relative_to(ROOT)}")
        path.write_bytes(fixed)


def run_shell_check(target: str, paths: list[Path]) -> None:
    for path in paths:
        shell = dialect(path)
        if target in {"format", "format-check"}:
            style = "bash" if shell == "bash" else "posix"
            format_source(target, path, ["shfmt", "-ln", style, "--", str(path)])
        else:
            if target == "lint-fix":
                _fix(path, shell)
            print(_shellcheck(path, shell, "gcc").decode(errors="replace"), end="")
