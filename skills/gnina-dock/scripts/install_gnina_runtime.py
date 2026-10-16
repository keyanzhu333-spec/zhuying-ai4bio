#!/usr/bin/env python3
"""Install the local GNINA–PyMOL–PLIP runtime.

The Python analysis tools are installed below the skill directory. GNINA's
official prebuilt executable is Linux-only; on Windows it is downloaded for
WSL when WSL is available. Docker can be used instead of WSL.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


GNINA_VERSION = "1.0.3"
GNINA_URL = f"https://github.com/gnina/gnina/releases/download/v{GNINA_VERSION}/gnina"
CORE_PACKAGES = [
    "plip==3.0.1",
    "openbabel==3.2.1",
    "meeko==0.7.1",
    "rdkit==2026.3.5",
    "scipy==1.18.0",
    "gemmi==0.7.5",
    "prody==2.6.1",
]
PYMOL_PACKAGES = ["pymol-open-source-whl==3.2.0.1"]


def install_packages(python: str, target: Path, packages: list[str]) -> list[str]:
    target.mkdir(parents=True, exist_ok=True)
    command = [
        python, "-m", "pip", "install", "--disable-pip-version-check",
        "--no-cache-dir", "--upgrade", "--target", str(target), *packages,
    ]
    subprocess.run(command, check=True)
    return command


def install_gnina(skill_dir: Path) -> dict[str, str | bool]:
    runtime = skill_dir / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    native = runtime / "gnina.exe"
    linux_binary = runtime / "gnina"
    has_wsl = bool(shutil.which("wsl.exe") or shutil.which("wsl"))
    if native.is_file():
        return {"backend": "native", "path": str(native.resolve()), "downloaded": False}
    if linux_binary.is_file() and (platform.system() != "Windows" or has_wsl):
        return {"backend": "wsl" if platform.system() == "Windows" else "native", "path": str(linux_binary.resolve()), "downloaded": False}

    if platform.system() == "Windows" and not has_wsl:
        if shutil.which("docker"):
            return {
                "backend": "docker",
                "path": "gnina/gnina:latest",
                "downloaded": False,
                "note": "WSL is unavailable; use --docker-image with the pipeline.",
            }
        raise RuntimeError(
            "Windows has no native GNINA binary in the official release. "
            "Install/enable WSL or Docker Desktop, then rerun this installer."
        )

    partial = linux_binary.with_suffix(".download")
    try:
        print(f"Downloading GNINA from {GNINA_URL}")
        urllib.request.urlretrieve(GNINA_URL, partial)
        partial.replace(linux_binary)
    finally:
        if partial.exists():
            partial.unlink()

    if platform.system() == "Windows":
        wsl = shutil.which("wsl.exe") or shutil.which("wsl")
        subprocess.run([wsl, "--", "chmod", "+x", "/mnt/" + linux_binary.drive[0].lower() + linux_binary.as_posix()[2:]], check=True)
        backend = "wsl"
    else:
        linux_binary.chmod(linux_binary.stat().st_mode | 0o111)
        backend = "native"
    return {"backend": backend, "path": str(linux_binary.resolve()), "downloaded": True}


def check_runtime(skill_dir: Path) -> dict[str, list[str] | str | bool]:
    runtime = skill_dir / "runtime"
    pymol_runtime = skill_dir / "runtime_pymol_whl"
    required = {
        "PLIP": runtime / "plip" / "plipcmd.py",
        "Meeko": runtime / "meeko" / "__init__.py",
        "RDKit": runtime / "rdkit" / "__init__.py",
        "SciPy": runtime / "scipy" / "__init__.py",
        "Gemmi": runtime / "gemmi" / "__init__.py",
        "ProDy": runtime / "prody" / "__init__.py",
        "PyMOL": pymol_runtime / "pymol" / "__init__.py",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    openbabel_ok = (runtime / "openbabel" / "bin" / "obabel.exe").exists() or (runtime / "bin" / "obabel.exe").exists()
    if not openbabel_ok:
        missing.append("Open Babel")
    native = runtime / "gnina.exe"
    linux_binary = runtime / "gnina"
    has_wsl = bool(shutil.which("wsl.exe") or shutil.which("wsl"))
    linux_backend_ok = linux_binary.exists() and (platform.system() != "Windows" or has_wsl)
    if not native.exists() and not linux_backend_ok and not shutil.which("gnina") and not shutil.which("docker"):
        missing.append("GNINA (native, WSL binary, or Docker)")
    backend = "native" if native.exists() or shutil.which("gnina") else ("wsl" if linux_backend_ok and platform.system() == "Windows" else ("native" if linux_backend_ok else ("docker" if shutil.which("docker") else "missing")))
    return {"missing": missing, "backend": backend, "complete": not missing}


def pymol_runtime_complete(skill_dir: Path) -> bool:
    pymol_runtime = skill_dir / "runtime_pymol_whl"
    return (
        (pymol_runtime / "pymol" / "__init__.py").exists()
        and any((pymol_runtime / "pymol").glob("_cmd*.pyd"))
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--check", action="store_true", help="Only check local runtime completeness")
    parser.add_argument("--docker-image", default="gnina/gnina:latest")
    parser.add_argument("--pull-docker", action="store_true", help="Pull the selected Docker image")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = args.skill_dir.resolve()
    before = check_runtime(skill_dir)
    if args.check:
        print(json.dumps(before, indent=2))
        return 0 if before["complete"] else 1

    gnina = install_gnina(skill_dir)
    runtime = skill_dir / "runtime"
    pymol_runtime = skill_dir / "runtime_pymol_whl"
    commands = [install_packages(args.python, runtime, CORE_PACKAGES)]
    if pymol_runtime_complete(skill_dir):
        print("Reusing the existing PyMOL runtime; pass a clean skill directory to reinstall it.")
        pymol_action = "reused_existing_runtime"
    else:
        requested_python_version = subprocess.check_output(
            [args.python, "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
            text=True,
        ).strip()
        if requested_python_version == "3.13":
            raise RuntimeError(
                "A clean PyMOL wheel install currently requires Python 3.12 on Windows "
                "because its NumPy dependency has no Python 3.13 wheel. Pass --python "
                "with a Python 3.12 executable."
            )
        commands.append(install_packages(args.python, pymol_runtime, PYMOL_PACKAGES))
        pymol_action = "installed"
    if args.pull_docker:
        docker_command = ["docker", "pull", args.docker_image]
        subprocess.run(docker_command, check=True)
        commands.append(docker_command)
    manifest = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "python": args.python,
        "gnina_url": GNINA_URL,
        "gnina_version": GNINA_VERSION,
        "gnina": gnina,
        "docker_image": args.docker_image,
        "core_packages": CORE_PACKAGES,
        "pymol_packages": PYMOL_PACKAGES,
        "pymol_action": pymol_action,
        "commands": commands,
    }
    (skill_dir / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    after = check_runtime(skill_dir)
    if not after["complete"]:
        raise RuntimeError("Runtime installation incomplete: " + ", ".join(after["missing"]))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
