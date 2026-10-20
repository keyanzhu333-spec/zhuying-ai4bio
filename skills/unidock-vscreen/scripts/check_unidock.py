#!/usr/bin/env python3
"""Check the local UniDock-Pro executable."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_UDP = os.environ.get("UNIDOCK_PRO_BIN") or shutil.which("udp") or str(Path.home() / "UniDock-Pro/build/udp")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check UniDock-Pro availability.")
    parser.add_argument("--udp", default=DEFAULT_UDP, help="Path to UniDock-Pro udp binary.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    resolved = shutil.which(os.path.expanduser(args.udp))
    udp = Path(resolved or args.udp).expanduser()
    result = {
        "udp": str(udp),
        "exists": udp.exists(),
        "executable": os.access(udp, os.X_OK),
        "ok": False,
        "version": None,
        "error": None,
    }

    if not result["exists"]:
        result["error"] = "UniDock-Pro binary does not exist."
    elif not result["executable"]:
        result["error"] = "UniDock-Pro binary is not executable."
    else:
        try:
            proc = subprocess.run(
                [str(udp), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=20,
                check=False,
            )
            output = proc.stdout or ""
            match = re.search(r"UniDock-Pro\s+v[^\s]+", output)
            result["version"] = match.group(0) if match else None
            result["ok"] = proc.returncode == 0 and "UniDock-Pro" in output
            if not result["ok"]:
                result["error"] = f"Unexpected return code {proc.returncode}."
        except Exception as exc:  # pragma: no cover - defensive CLI boundary
            result["error"] = str(exc)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"udp: {result['udp']}")
        print(f"exists: {result['exists']}")
        print(f"executable: {result['executable']}")
        print(f"version: {result['version'] or 'unknown'}")
        print(f"ok: {result['ok']}")
        if result["error"]:
            print(f"error: {result['error']}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
