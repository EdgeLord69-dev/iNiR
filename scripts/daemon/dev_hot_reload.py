#!/usr/bin/env python3
"""Hot reload for the QML Quickshell's own watcher never sees (development checkouts only).

Quickshell watches only the files its scanner reaches through `import qs.…` lines from shell.qml
(quickshell 0.3.1, src/core/scan.cpp). Everything loaded by `source:` path (each family's panels,
Background, the dock, sidebars, OSDs: 104 of 181 QML directories on 2026-10-01) was never watched,
so edits there did not reload and tests ran stale code. Making the scanner reach them costs ~1.2 s on
every cold start; this watcher costs nothing at start. On a real content change to one of those files
it asks the shell for the same soft reload (`dev reload` → Quickshell.reload(false)).

usage: dev_hot_reload.py <shell root> <shell pid>     exits with the shell
"""
import ctypes
import ctypes.util
import hashlib
import os
import re
import struct
import subprocess
import sys
import time

ROOT = os.path.abspath(sys.argv[1])
SHELL_PID = int(sys.argv[2])
WATCHED_TREES = ("modules", "services")
SKIP = re.compile(r"/(\.git|node_modules|prebuilt|native)(/|$)")
DEBOUNCE = 0.35

IN_CLOSE_WRITE, IN_MOVED_TO, IN_CREATE, IN_ISDIR = 0x08, 0x80, 0x100, 0x40000000
libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def scanner_reach() -> set:
    """Files Quickshell's scanner reaches, by its own rules: every capitalised .qml in a directory
    it scans, and the directories named by `import qs.…` (or quoted) lines before the first `{`."""
    files, dirs = set(), set()

    def scan_file(path):
        if path in files:
            return
        files.add(path)
        imports = []
        try:
            for line in open(path, errors="replace"):
                line = line.strip()
                if line.startswith("import"):
                    at = line.find(" qs.")
                    if at != -1:
                        name = re.match(r"[\w.]+", line[at + 4:])
                        if name:
                            imports.append(os.path.join(ROOT, name.group(0).replace(".", "/")))
                    elif (quoted := re.search(r'"([^"]+)"', line)):
                        ref = quoted.group(1)
                        imports.append(os.path.join(ROOT, ref[5:].lstrip("/")) if ref.startswith("root:")
                                       else os.path.join(os.path.dirname(path), ref))
                elif "{" in line:
                    break
        except OSError:
            return
        scan_dir(os.path.dirname(path))
        for target in imports:
            if os.path.isdir(target):
                scan_dir(os.path.abspath(target))

    def scan_dir(directory):
        if directory in dirs:
            return
        dirs.add(directory)
        for name in sorted(os.listdir(directory)):
            full = os.path.join(directory, name)
            if name[:1].isupper() and name.endswith(".qml") and os.path.isfile(full):
                scan_file(full)

    scan_file(os.path.join(ROOT, "shell.qml"))
    return files | {os.path.join(d, f) for d in dirs for f in os.listdir(d) if f.endswith(".js")}


def digest(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.md5(handle.read()).hexdigest()
    except OSError:
        return None


def main():
    fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if fd < 0:
        sys.exit("inotify unavailable")
    wd_dirs = {}

    def add_tree(top):
        for current, subdirs, _ in os.walk(top):
            subdirs[:] = [d for d in subdirs if not SKIP.search(os.path.join(current, d))]
            wd = libc.inotify_add_watch(fd, current.encode(), IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE)
            if wd >= 0:
                wd_dirs[wd] = current

    for tree in WATCHED_TREES:
        add_tree(os.path.join(ROOT, tree))

    reach = scanner_reach()
    hashes = {}
    pending_since = 0.0
    while True:
        try:
            os.kill(SHELL_PID, 0)
        except ProcessLookupError:
            return
        try:
            data = os.read(fd, 65536)
        except BlockingIOError:
            data = b""
        offset = 0
        while offset < len(data):
            wd, mask, _cookie, length = struct.unpack_from("iIII", data, offset)
            name = data[offset + 16: offset + 16 + length].rstrip(b"\0").decode(errors="replace")
            offset += 16 + length
            path = os.path.join(wd_dirs.get(wd, ""), name)
            if mask & IN_ISDIR:
                if mask & IN_CREATE:
                    add_tree(path)
                continue
            if not (name.endswith(".qml") or name.endswith(".js") or name == "qmldir"):
                continue
            if path in reach:
                continue  # Quickshell reloads these itself
            new = digest(path)
            if new is None or os.path.getsize(path) == 0:
                continue  # a truncate before the write (editors save in two steps)
            if hashes.get(path) == new:
                continue  # rewritten with the same bytes
            hashes[path] = new
            pending_since = time.monotonic()
        if pending_since and time.monotonic() - pending_since >= DEBOUNCE:
            pending_since = 0.0
            subprocess.run(["qs", "-p", ROOT, "ipc", "call", "dev", "reload"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            time.sleep(2.5)  # the reload itself; a fresh scan picks up new imports
            reach = scanner_reach()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
