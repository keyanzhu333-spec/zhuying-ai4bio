#!/usr/bin/env python3
"""Run a HADDOCK3 configuration without assuming a personal install path."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def command_prefix(requested: str | None, conda_env: str) -> list[str]:
    value = requested or os.environ.get("HADDOCK3_BIN") or shutil.which("haddock3")
    if value:
        resolved = shutil.which(os.path.expanduser(value))
        if not resolved:
            raise SystemExit("Configured HADDOCK3 executable is missing or not executable.")
        return [str(Path(resolved).resolve())]
    conda = shutil.which("conda") or shutil.which("mamba") or shutil.which("micromamba")
    if conda:
        return [conda, "run", "-n", conda_env, "haddock3"]
    raise SystemExit("HADDOCK3 was not found. Set HADDOCK3_BIN or activate/install its environment.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="HADDOCK3 run configuration")
    parser.add_argument("--haddock3", help="Path to haddock3")
    parser.add_argument("--conda-env", default="haddock3")
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--record", type=Path, help="Run-record path; defaults beside config")
    args = parser.parse_args()

    config = args.config.expanduser().resolve()
    if not config.is_file() or config.stat().st_size == 0:
        parser.error(f"configuration does not exist or is empty: {config}")
    command = command_prefix(args.haddock3, args.conda_env)
    if args.setup_only:
        command.append("--setup")
    command.append(str(config))
    print(shlex.join(command))
    if args.dry_run:
        return 0

    log = config.with_suffix(config.suffix + ".log")
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(command, cwd=config.parent, stdout=handle, stderr=subprocess.STDOUT, check=False)
    record = args.record.expanduser() if args.record else config.with_suffix(config.suffix + ".run.json")
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config),
        "command": command,
        "setup_only": args.setup_only,
        "returncode": proc.returncode,
        "log": str(log),
    }, indent=2) + "\n", encoding="utf-8")
    if proc.returncode:
        raise SystemExit(f"HADDOCK3 failed with exit code {proc.returncode}; inspect {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
