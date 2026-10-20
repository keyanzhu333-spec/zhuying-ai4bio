#!/usr/bin/env python3
"""Execute selected GROMACS stages; preserve existing outputs and resume TPRs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

STAGES = ("em", "nvt", "npt", "production")


def require_file(path: Path, label: str) -> None:
    if not path.is_file() or not path.stat().st_size:
        raise SystemExit(f"Missing {label}: {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--from-stage", choices=STAGES, default="em")
    parser.add_argument("--through", choices=STAGES, help="Default: run only --from-stage")
    parser.add_argument("--gmx", help="Executable name or path; overrides GMX_BIN")
    parser.add_argument("--accelerator", choices=("cpu", "gpu"))
    parser.add_argument("--ntmpi", type=int, default=1)
    parser.add_argument("--ntomp", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--external-mpi", action="store_true", help="Omit thread-MPI-only -ntmpi")
    parser.add_argument("--maxwarn", type=int, default=0)
    parser.add_argument("--mdrun-arg", action="append", default=[])
    parser.add_argument("--approve-production", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Resume one stage from its existing TPR/CPT")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    args.through = args.through or args.from_stage
    start, end = STAGES.index(args.from_stage), STAGES.index(args.through)
    if start > end:
        parser.error("--from-stage must not follow --through")
    if args.through == "production" and not args.approve_production:
        parser.error("production requires --approve-production after equilibration review")
    if args.ntmpi < 1 or args.ntomp < 1 or args.maxwarn < 0:
        parser.error("thread counts must be positive; maxwarn cannot be negative")
    if args.resume and start != end:
        parser.error("--resume operates on one stage; select it with --from-stage")
    controlled = {"-s", "-deffnm", "-cpi", "-append", "-noappend", "-nb", "-pme",
                  "-bonded", "-update", "-ntmpi", "-ntomp", "-nsteps"}
    if any(arg.split("=")[0] in controlled for arg in args.mdrun_arg):
        parser.error("--mdrun-arg cannot override stage files, steps, or execution mode")

    project = args.project.expanduser().resolve()
    simulation = project / "simulation"
    config_path = simulation / "run_config.json"
    config = json.loads(config_path.read_text()) if config_path.is_file() else {}

    def configured(key: str, default: str) -> Path:
        path = Path(config.get(key, default)).expanduser()
        return (path if path.is_absolute() else project / path).resolve()

    topology = configured("topology", "simulation/system/topol.top")
    initial = configured("coordinates", "simulation/system/system.gro")
    reference = configured("reference_coordinates", "simulation/system/system.gro")
    index = configured("index", "simulation/system/index.ndx")
    executable = args.gmx or os.environ.get("GMX_BIN") or config.get("gromacs_command", "auto")
    gmx = (shutil.which("gmx") or shutil.which("gmx_mpi")) if executable == "auto" else shutil.which(os.path.expanduser(executable))
    if not gmx:
        parser.error("GROMACS not found; activate its environment or set --gmx / GMX_BIN")
    gmx = str(Path(gmx).resolve())
    accelerator = args.accelerator or config.get("accelerator", "cpu")
    if accelerator not in ("cpu", "gpu"):
        parser.error("run_config.json accelerator must be cpu or gpu")
    require_file(topology, "topology")
    require_file(initial, "initial coordinates")

    for position in range(start, end + 1):
        stage = STAGES[position]
        stage_dir = simulation / stage
        stem = stage_dir / stage
        tpr, cpt = stem.with_suffix(".tpr"), stem.with_suffix(".cpt")
        mdp = simulation / "mdp" / f"{stage}.mdp"
        record_path = stage_dir / "run_record.json"
        require_file(mdp, "MDP")
        previous = STAGES[position - 1] if position else None
        coordinates = simulation / previous / f"{previous}.gro" if previous else initial
        checkpoint = simulation / previous / f"{previous}.cpt" if position > 1 else None
        if position == start and not args.resume:
            require_file(coordinates, "previous-stage coordinates")
            if checkpoint:
                require_file(checkpoint, "previous-stage checkpoint")

        # Include local topology dependencies when checking continuation inputs.
        files = [mdp, initial, reference, index]
        files += sorted(p for p in topology.parent.rglob("*") if p.is_file())
        fingerprint = {
            os.path.relpath(p, project): sha256(p) for p in files if p.is_file()
        }
        commands = []
        if args.resume:
            require_file(tpr, "existing TPR")
            require_file(cpt, "existing checkpoint")
            require_file(record_path, "stage run record")
            old = json.loads(record_path.read_text())
            if old.get("input_sha256") != fingerprint or old.get("tpr_sha256") != sha256(tpr):
                parser.error("stage inputs or TPR changed; use a new case instead of resuming")
        else:
            if stage_dir.exists() and any(stage_dir.iterdir()):
                parser.error(f"stage already has output: {stage}; select another stage or --resume")
            grompp = [gmx, "grompp", "-f", str(mdp), "-c", str(coordinates),
                      "-p", str(topology), "-o", str(tpr), "-po", str(stage_dir / "processed.mdp")]
            if stage in ("nvt", "npt"):
                require_file(reference, "restraint reference")
                grompp += ["-r", str(reference)]
            if checkpoint:
                grompp += ["-t", str(checkpoint)]
            if index.is_file():
                grompp += ["-n", str(index)]
            if args.maxwarn:
                grompp += ["-maxwarn", str(args.maxwarn)]
            commands.append(grompp)

        mdrun = [gmx, "mdrun", "-s", str(tpr), "-deffnm", str(stem),
                 "-ntomp", str(args.ntomp), "-cpt", "10", "-nb", accelerator]
        if not args.external_mpi and "mpi" not in Path(gmx).name:
            mdrun += ["-ntmpi", str(args.ntmpi)]
        if accelerator == "cpu":
            mdrun += ["-pme", "cpu", "-bonded", "cpu", "-update", "cpu"]
        if args.resume:
            mdrun += ["-cpi", str(cpt), "-append"]
        commands.append(mdrun + args.mdrun_arg)
        for command in commands:
            print(shlex.join(command), flush=True)
        if args.dry_run:
            continue

        stage_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "stage": stage, "status": "running",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "input_sha256": fingerprint, "commands": commands,
            "production_approved": args.approve_production,
        }

        def save_record() -> None:
            if tpr.is_file():
                record["tpr_sha256"] = sha256(tpr)
            record_path.write_text(json.dumps(record, indent=2) + "\n")

        save_record()
        try:
            for command in commands:
                # Resolve topology includes from the prepared system directory.
                with (stage_dir / f"{command[1]}.stdout.log").open("a") as handle:
                    subprocess.run(command, cwd=topology.parent, stdout=handle,
                                   stderr=subprocess.STDOUT, check=True)
                save_record()
            require_file(stem.with_suffix(".gro"), "stage output coordinates")
            if stage != "em":
                require_file(cpt, "stage output checkpoint")
            record["status"] = "executed_requires_scientific_review"
        except BaseException:
            record["status"] = "failed_or_interrupted"
            raise
        finally:
            save_record()
        print(f"Completed commands for {stage}; review energies and geometry before advancing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
