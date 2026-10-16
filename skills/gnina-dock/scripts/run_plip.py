#!/usr/bin/env python3
"""Run the bundled PLIP console entry point with the local runtime on sys.path."""

from __future__ import annotations

import sys
import os
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    skill_dir = Path(__file__).resolve().parents[1]
    runtime = skill_dir / "runtime"
    pymol_runtime = skill_dir / "runtime_pymol_whl"
    if not runtime.is_dir():
        raise FileNotFoundError(f"PLIP runtime not found: {runtime}")
    sys.path.insert(0, str(pymol_runtime))
    sys.path.insert(1, str(runtime))
    for directory in (pymol_runtime, pymol_runtime / "pymol", runtime):
        if hasattr(os, "add_dll_directory") and directory.is_dir():
            os.add_dll_directory(str(directory))
    # The Windows Open Babel Python wheel may omit the InChI output plugin,
    # while PLIP asks Pybel for an InChIKey. Fall back to the installed CLI.
    from openbabel import pybel
    original_write = pybel.Molecule.write
    local_obabel = runtime / "openbabel" / "bin" / "obabel.exe"
    obabel = shutil.which("obabel") or (
        str(local_obabel) if local_obabel.exists() else r"C:\Program Files (x86)\OpenBabel-3.1.1\obabel.exe"
    )

    def write_with_inchikey(self, format="smi", filename=None, overwrite=False, opt=None):
        if format.lower() != "inchikey":
            return original_write(self, format, filename, overwrite, opt)
        try:
            return original_write(self, format, filename, overwrite, opt)
        except ValueError:
            smiles = original_write(self, "can").strip().splitlines()[0]
            result = subprocess.run(
                [obabel, f"-:{smiles}", "-oinchikey"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            return result.stdout.strip().splitlines()[0] if result.stdout.strip() else "UNAVAILABLE"

    pybel.Molecule.write = write_with_inchikey
    import pymol
    pymol.finish_launching(args=["pymol", "-pcq", "-K"])
    pymol.cmd.reinitialize()
    from plip.plipcmd import main as plip_main

    plip_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
