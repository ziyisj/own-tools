#!/usr/bin/env python3
"""Pull the latest project code from GitHub and verify Python files."""

from __future__ import annotations

import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    remote = run(["git", "remote", "get-url", "origin"]).stdout.strip()
    if not remote:
        print("No git remote origin configured.", file=sys.stderr)
        return 1

    run(["git", "pull", "--ff-only", "origin", "main"])
    run([sys.executable, "-m", "py_compile", "adspower_web.py", "adspower_open_chatgpt.py"])
    print("Update complete. Restart adspower_web.py if it is already running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
