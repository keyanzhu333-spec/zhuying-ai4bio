#!/usr/bin/env python3
"""Report whether ZY-AI4Bio runtimes and private resources are available."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


COMMANDS = {
    "gromacs": (("GMX_BIN",), ("gmx", "gmx_mpi")),
    "gnina": (("GNINA_BIN",), ("gnina",)),
    "unidock_pro": (("UNIDOCK_PRO_BIN",), ("udp",)),
    "open_babel": (("OBABEL_BIN",), ("obabel",)),
    "lightdock_setup": (("LIGHTDOCK_SETUP_BIN",), ("lightdock3_setup.py",)),
    "lightdock_run": (("LIGHTDOCK_RUN_BIN",), ("lightdock3.py",)),
    "haddock3": (("HADDOCK3_BIN",), ("haddock3",)),
    "chai1": (("CHAI1_BIN",), ("chai-lab",)),
    "plip": (("PLIP_BIN",), ("plip",)),
    "pymol": (("PYMOL_BIN",), ("pymol",)),
    "nvidia_smi": ((), ("nvidia-smi",)),
    "conda": ((), ("conda", "mamba", "micromamba")),
}

PYTHON_MODULES = ("rdkit", "Bio", "matplotlib", "igfold")


def resolve_command(env_names: tuple[str, ...], candidates: tuple[str, ...]) -> dict[str, object]:
    for env_name in env_names:
        value = os.environ.get(env_name)
        if value:
            resolved = shutil.which(os.path.expanduser(value))
            return {
                "available": bool(resolved),
                "path": resolved,
                "source": env_name,
            }
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return {"available": True, "path": found, "source": "PATH"}
    return {"available": False, "path": None, "source": None}


def detect_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def version_line(path: str) -> str | None:
    for flag in ("--version", "-version"):
        try:
            proc = subprocess.run(
                [path, flag], text=True, capture_output=True, timeout=10, check=False
            )
        except (OSError, subprocess.SubprocessError):
            continue
        text = (proc.stdout or proc.stderr).strip()
        if proc.returncode == 0 and text:
            return text.splitlines()[0][:300]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Write the complete report to this JSON file")
    parser.add_argument("--versions", action="store_true", help="Probe executable version output")
    parser.add_argument("--require", nargs="+", choices=sorted(COMMANDS),
                        help="Return nonzero if any named command is missing")
    parser.add_argument("--private-paths", action="store_true", help="Include absolute paths in report")
    args = parser.parse_args()

    commands = {name: resolve_command(*spec) for name, spec in COMMANDS.items()}
    if args.versions:
        for item in commands.values():
            if item["available"] and item["path"]:
                item["version"] = version_line(str(item["path"]))

    data_root_value = os.environ.get("ZY_AI4BIO_DATA")
    data_root = Path(data_root_value).expanduser() if data_root_value else None
    report = {
        "schema_version": 1,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "wsl": detect_wsl(),
        },
        "commands": commands,
        "python_modules": {
            name: {"available": importlib.util.find_spec(name) is not None}
            for name in PYTHON_MODULES
        },
        "credentials": {
            "nvidia_api_key_configured": bool(os.environ.get("NVIDIA_API_KEY")) or
            (Path.home() / ".config/ZYDock/credentials").is_file(),
        },
        "resources": {
            "data_root": str(data_root) if data_root else None,
            "available": bool(data_root and data_root.is_dir()),
        },
    }
    if not args.private_paths:
        for item in commands.values():
            if item["path"]:
                item["path"] = Path(str(item["path"])).name
            if item.get("version"):
                item["version"] = str(item["version"]).replace(str(Path.home()), "<HOME>")
        report["resources"]["data_root"] = "<configured>" if data_root else None

    if args.json:
        destination = args.json.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Platform: {report['platform']['system']} ({'WSL' if report['platform']['wsl'] else 'native'})")
    for name, item in commands.items():
        state = "OK" if item["available"] else "MISSING"
        detail = item["path"] or "not found"
        print(f"{state:7} {name:18} {detail}")
    print(f"{'OK' if report['resources']['available'] else 'INFO':7} data_root          {report['resources']['data_root'] or 'ZY_AI4BIO_DATA not set'}")
    if args.json:
        print(f"Report: {args.json.expanduser().resolve()}")
    return 1 if any(not commands[name]["available"] for name in args.require or []) else 0


if __name__ == "__main__":
    raise SystemExit(main())
