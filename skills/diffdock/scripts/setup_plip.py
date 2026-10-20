#!/usr/bin/env python3
"""Install or check an isolated PLIP/Open Babel/PyMOL Conda environment."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--env", default=os.environ.get("PLIP_CONDA_ENV", "PLIP"))
    args = parser.parse_args()
    conda = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not conda:
        parser.error("Conda not found; install Miniforge or set CONDA_EXE.")
    try:
        result = subprocess.run([conda, "env", "list", "--json"], check=True,
                                capture_output=True, text=True)
        exists = any(Path(p).name == args.env for p in json.loads(result.stdout)["envs"])
        if not args.check:
            command = [conda, "install" if exists else "create", "-n", args.env,
                       "--override-channels", "-c", "conda-forge", "-c", "bioconda",
                       "--strict-channel-priority", "-y", "python=3.11",
                       "plip", "openbabel", "pymol-open-source", "imagemagick"]
            subprocess.run(command, check=True)
            exists = True
        if not exists:
            print(f"Environment {args.env!r} is missing.")
            return 1
        for command in (["plip", "-h"], ["obabel", "-V"],
                        ["python", "-c", "import pymol; from openbabel import openbabel"]):
            subprocess.run([conda, "run", "-n", args.env, *command], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"PLIP toolchain is available in {args.env!r}.")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as exc:
        print(f"PLIP environment check/install failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
