#!/usr/bin/env python3
"""Run Chai-1 from PATH, an override, or a named Conda environment."""

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
    value = requested or os.environ.get("CHAI1_BIN") or shutil.which("chai-lab")
    if value:
        return [str(Path(value).expanduser())]
    conda = shutil.which("conda") or shutil.which("mamba") or shutil.which("micromamba")
    if conda:
        return [conda, "run", "-n", conda_env, "chai-lab"]
    raise SystemExit("Chai-1 was not found. Set CHAI1_BIN, activate its environment, or install Conda.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Multi-entity FASTA input")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--chai", help="Path to chai-lab")
    parser.add_argument("--conda-env", default="chai1")
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--num-diffn-samples", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args, extra = parser.parse_known_args()

    source = args.input.expanduser().resolve()
    output = args.out_dir.expanduser().resolve()
    if not source.is_file() or source.stat().st_size == 0:
        parser.error(f"input FASTA does not exist or is empty: {source}")
    first_content = next(
        (line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()),
        "",
    )
    if not first_content.startswith(">"):
        parser.error(f"input does not begin with a FASTA header: {source}")
    if output.exists() and any(output.iterdir()):
        parser.error(f"output directory is not empty: {output}")
    if args.num_diffn_samples is not None and args.num_diffn_samples < 1:
        parser.error("--num-diffn-samples must be positive")

    command = command_prefix(args.chai, args.conda_env) + ["fold", str(source), str(output)]
    if args.device:
        command.extend(["--device", args.device])
    if args.num_diffn_samples:
        command.extend(["--num-diffn-samples", str(args.num_diffn_samples)])
    command.extend(extra)
    print(shlex.join(command))
    if args.dry_run:
        return 0

    output.mkdir(parents=True, exist_ok=True)
    log = output / "chai1.log"
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    record = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(source),
        "output": str(output),
        "command": command,
        "returncode": proc.returncode,
    }
    (output / "run_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if proc.returncode:
        raise SystemExit(f"Chai-1 failed with exit code {proc.returncode}; inspect {log}")
    print(f"Output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
