#!/usr/bin/env python3
"""Run validated GROMACS system files through explicit MD stages."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


STAGES = ("em", "nvt", "npt", "production")


def resolve_gmx(requested: str | None) -> str:
    value = requested or os.environ.get("GMX_BIN") or shutil.which("gmx") or shutil.which("gmx_mpi")
    if not value:
        raise SystemExit("GROMACS was not found. Set GMX_BIN or pass --gmx.")
    path = Path(value).expanduser() if os.sep in value else None
    if path and not (path.is_file() and os.access(path, os.X_OK)):
        raise SystemExit(f"GROMACS executable is not usable: {path}")
    return str(path.resolve()) if path else value


def require_file(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"Missing {label}: {path}")


def run(command: list[str], log_path: Path, dry_run: bool) -> None:
    rendered = shlex.join(command)
    print(rendered)
    if dry_run:
        return
    with log_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if proc.returncode:
        raise SystemExit(f"Command failed with exit code {proc.returncode}; inspect {log_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="Initialized three-directory MD project")
    parser.add_argument("--through", choices=STAGES, default="npt")
    parser.add_argument("--gmx", help="GROMACS executable; otherwise use GMX_BIN or PATH")
    parser.add_argument("--accelerator", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--ntmpi", type=int, default=1)
    parser.add_argument("--ntomp", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--maxwarn", type=int, default=0, help="Explicit grompp warning allowance; default is zero")
    parser.add_argument("--mdrun-arg", action="append", default=[], help="Extra single mdrun argument; repeat as needed")
    parser.add_argument("--approve-production", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Use an existing stage checkpoint with -cpi")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.through == "production" and not args.approve_production:
        parser.error("production requires --approve-production after reviewing topology, MDPs, and equilibration")
    if args.ntmpi < 1 or args.ntomp < 1 or args.maxwarn < 0:
        parser.error("--ntmpi/--ntomp must be positive and --maxwarn cannot be negative")

    project = args.project.expanduser().resolve()
    simulation = project / "simulation"
    topology = simulation / "system" / "topol.top"
    initial = simulation / "system" / "system.gro"
    index = simulation / "system" / "index.ndx"
    reference = simulation / "system" / "system.gro"
    require_file(topology, "validated topology")
    require_file(initial, "validated coordinates")
    gmx = resolve_gmx(args.gmx)

    commands: list[dict[str, object]] = []
    previous_coordinates = initial
    previous_checkpoint: Path | None = None
    for stage in STAGES[: STAGES.index(args.through) + 1]:
        stage_dir = simulation / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        mdp = simulation / "mdp" / f"{stage}.mdp"
        require_file(mdp, f"{stage} MDP")
        deffnm = stage_dir / stage
        grompp = [
            gmx, "grompp", "-f", str(mdp), "-c", str(previous_coordinates),
            "-p", str(topology), "-o", str(deffnm.with_suffix(".tpr")),
            "-po", str(stage_dir / "processed.mdp"),
        ]
        if stage != "em":
            require_file(reference, "restraint reference coordinates")
            grompp.extend(["-r", str(reference)])
        if previous_checkpoint:
            grompp.extend(["-t", str(previous_checkpoint)])
        if index.is_file() and index.stat().st_size:
            grompp.extend(["-n", str(index)])
        if args.maxwarn:
            grompp.extend(["-maxwarn", str(args.maxwarn)])

        mdrun = [
            gmx, "mdrun", "-deffnm", str(deffnm),
            "-ntmpi", str(args.ntmpi), "-ntomp", str(args.ntomp), "-cpt", "10",
        ]
        if args.accelerator == "gpu":
            mdrun.extend(["-nb", "gpu"])
        if args.resume and deffnm.with_suffix(".cpt").is_file():
            mdrun.extend(["-cpi", str(deffnm.with_suffix(".cpt")), "-append"])
        mdrun.extend(args.mdrun_arg)

        commands.extend((
            {"stage": stage, "kind": "grompp", "command": grompp},
            {"stage": stage, "kind": "mdrun", "command": mdrun},
        ))
        run(grompp, stage_dir / "grompp.log", args.dry_run)
        run(mdrun, stage_dir / "mdrun.log", args.dry_run)
        previous_coordinates = deffnm.with_suffix(".gro")
        previous_checkpoint = None if stage == "em" else deffnm.with_suffix(".cpt")
        if not args.dry_run:
            require_file(previous_coordinates, f"{stage} output coordinates")
            if previous_checkpoint:
                require_file(previous_checkpoint, f"{stage} checkpoint")

    record = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "through": args.through,
        "accelerator": args.accelerator,
        "dry_run": args.dry_run,
        "production_approved": args.approve_production,
        "commands": commands,
    }
    record_path = simulation / "logs" / "last_run.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Run record: {record_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
