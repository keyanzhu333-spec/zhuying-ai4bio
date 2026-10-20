#!/usr/bin/env python3
"""Create a Linux/WSL analysis environment or check the active GNINA toolchain."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_runtime(skill_dir: Path, python: str = sys.executable) -> dict:
    missing = []
    for module in ("rdkit", "openbabel", "pymol", "plip"):
        try:
            result = subprocess.run([python, "-c", f"import {module}"],
                                    capture_output=True, timeout=30)
            if result.returncode:
                missing.append(module)
        except (OSError, subprocess.TimeoutExpired):
            missing.append(module)
    binary = shutil.which(os.path.expanduser(os.environ.get("GNINA_BIN") or "gnina"))
    if not binary:
        local = skill_dir / "runtime" / ("gnina.exe" if os.name == "nt" else "gnina")
        binary = str(local) if local.is_file() and os.access(local, os.X_OK) else None
    if not binary:
        missing.append("GNINA (GNINA_BIN or PATH)")
    else:
        try:
            probe = subprocess.run([binary, "--help"], capture_output=True, timeout=30)
            if probe.returncode:
                missing.append("GNINA runtime probe failed")
        except (OSError, subprocess.TimeoutExpired):
            missing.append("GNINA runtime probe failed")
    return {"missing": missing, "backend": "native" if binary else "missing",
            "complete": not missing, "scope": "active Python environment"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--conda-env", default="zy-gnina")
    args = parser.parse_args()
    skill_dir = args.skill_dir.resolve()
    if args.check:
        result = check_runtime(skill_dir, args.python)
        print(json.dumps(result, indent=2))
        return 0 if result["complete"] else 1
    if platform.system() != "Linux":
        parser.error("Run installation inside Linux/WSL2. Native Windows wheels are not provisioned.")
    conda = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not conda:
        parser.error("Install Miniforge/Conda first or set CONDA_EXE.")
    environments = subprocess.run([conda, "env", "list", "--json"], check=True,
                                  capture_output=True, text=True)
    if any(Path(p).name == args.conda_env for p in json.loads(environments.stdout)["envs"]):
        parser.error("Environment already exists; activate it and use --check, or choose --conda-env.")
    subprocess.run(
        [conda, "env", "create", "-n", args.conda_env,
         "-f", str(skill_dir / "assets/environment.yml")], check=True,
    )
    print(f"Analysis environment created: {args.conda_env}")
    print("Install a compatible GNINA binary from https://github.com/gnina/gnina/releases")
    print("Set GNINA_BIN, activate the analysis environment, then run this script with --check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
