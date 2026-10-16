#!/usr/bin/env python3
"""Launch the bundled Windows PyMOL wheel with its DLL search path set."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def main() -> int:
    skill_dir = Path(__file__).resolve().parents[1]
    pymol_runtime = skill_dir / "runtime_pymol_whl"
    plip_runtime = skill_dir / "runtime"
    if not pymol_runtime.is_dir():
        raise FileNotFoundError(f"PyMOL runtime not found: {pymol_runtime}")

    sys.path.insert(0, str(pymol_runtime))
    sys.path.insert(1, str(plip_runtime))
    dll_dirs = [pymol_runtime, pymol_runtime / "pymol", plip_runtime]
    for directory in dll_dirs:
        if hasattr(os, "add_dll_directory") and directory.is_dir():
            os.add_dll_directory(str(directory))

    # pymol.__main__ consumes the normal PyMOL CLI arguments from sys.argv.
    sys.argv = ["pymol"] + sys.argv[1:]
    runpy.run_module("pymol", run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
