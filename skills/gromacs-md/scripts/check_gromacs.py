#!/usr/bin/env python3
"""Check a GROMACS executable without starting a simulation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def resolve_gmx(requested: str | None) -> str | None:
    value = requested or os.environ.get("GMX_BIN")
    if value:
        return shutil.which(os.path.expanduser(value))
    return shutil.which("gmx") or shutil.which("gmx_mpi")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gmx", help="GROMACS executable; otherwise use GMX_BIN or PATH")
    parser.add_argument("--json", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    executable = resolve_gmx(args.gmx)
    report: dict[str, object] = {"available": bool(executable), "executable": executable}
    if executable:
        proc = subprocess.run(
            [executable, "--version"], text=True, capture_output=True, check=False, timeout=20
        )
        output = (proc.stdout or proc.stderr).strip()
        report.update(
            returncode=proc.returncode,
            version_output=output,
            cuda_build="CUDA" in output.upper(),
        )
    else:
        report["error"] = "Set GMX_BIN or place gmx/gmx_mpi on PATH."

    if args.json:
        args.json.expanduser().parent.mkdir(parents=True, exist_ok=True)
        args.json.expanduser().write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if executable and report.get("returncode") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
