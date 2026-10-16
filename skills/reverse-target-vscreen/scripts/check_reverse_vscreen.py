#!/usr/bin/env python3
"""Check local readiness for staged reverse target screening."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
UDP = Path(os.environ.get("UNIDOCK_PRO_BIN") or shutil.which("udp") or Path.home() / "UniDock-Pro/build/udp")
GNINA_CHECK = SKILLS_ROOT / "gnina-dock/scripts/install_gnina_runtime.py"
DIFFDOCK = SKILLS_ROOT / "diffdock/SKILL.md"
DIFFDOCK_CREDENTIALS = Path.home() / ".config" / "ZYDock" / "credentials"
CHAI = shutil.which("chai-lab")
PLIP = shutil.which("plip")
VIEWER_ROOT = CODEX_HOME / "plugins/cache/openai-curated-remote/structure-viewer"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check reverse-screening dependencies.")
    parser.add_argument("--deep", action="store_true", help="Run the GNINA runtime checker.")
    parser.add_argument("--strict", action="store_true", help="Fail if a core dependency is missing.")
    args = parser.parse_args()

    obabel = shutil.which("obabel")
    gnina_runtime: dict[str, object] = {
        "checked": False,
        "complete": bool(shutil.which("gnina")),
        "backend": "native" if shutil.which("gnina") else "unknown",
    }
    if args.deep and GNINA_CHECK.is_file():
        proc = subprocess.run(
            ["python3", str(GNINA_CHECK), "--check"],
            text=True,
            capture_output=True,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"complete": False, "error": proc.stderr.strip() or proc.stdout.strip()}
        gnina_runtime = {"checked": True, **payload}

    report = {
        "core": {
            "open_babel": {"available": bool(obabel), "executable": obabel},
            "unidock_pro": {"available": UDP.is_file() and os.access(UDP, os.X_OK), "executable": str(UDP)},
        },
        "follow_up": {
            "gnina_runtime": gnina_runtime,
            "diffdock_skill": {"available": DIFFDOCK.is_file()},
            "diffdock_credentials": {
                "configured": bool(os.environ.get("NVIDIA_API_KEY")) or DIFFDOCK_CREDENTIALS.is_file(),
                "secret_displayed": False,
            },
            "chai1": {"available": bool(CHAI), "executable": CHAI},
            "plip": {"available": bool(PLIP), "executable": PLIP},
            "structure_viewer": {"available": any(VIEWER_ROOT.glob("*/skills/structure-viewer/SKILL.md"))},
        },
    }
    report["core_ready"] = all(item["available"] for item in report["core"].values())
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 1 if args.strict and not report["core_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
