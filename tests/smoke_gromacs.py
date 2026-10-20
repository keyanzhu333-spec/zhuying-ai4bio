#!/usr/bin/env python3
"""Exercise all MD stages on a tiny water box; this is not a scientific MD protocol."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/gromacs-md/scripts"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gmx", required=True)
    args = parser.parse_args()
    gmx = shutil.which(args.gmx)
    if not gmx:
        parser.error("GROMACS executable missing")
    directory = Path(tempfile.mkdtemp(prefix="zy-water-smoke-"))
    case = directory / "case"
    source = directory / "water.pdb"
    source.write_text("END\n")
    log = directory / "smoke.log"

    def run(command):
        with log.open("a") as handle:
            subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=True)

    try:
        run([sys.executable, str(SCRIPTS / "init_md_case.py"),
             "--scenario", "single-protein", "--input", str(source), "--out-dir", str(case)])
        system = case / "simulation/system"
        run([gmx, "solvate", "-cs", "spc216.gro", "-box", "2.5", "2.5", "2.5",
             "-o", str(system / "system.gro")])
        atoms = int((system / "system.gro").read_text().splitlines()[1])
        (system / "topol.top").write_text(
            '#include "amber99sb-ildn.ff/forcefield.itp"\n'
            '#include "amber99sb-ildn.ff/spc.itp"\n'
            f"[ system ]\nSmoke water\n[ molecules ]\nSOL {atoms // 3}\n"
        )
        for mdp in (case / "simulation/mdp").glob("*.mdp"):
            lines = []
            for line in mdp.read_text().splitlines():
                key = line.partition("=")[0].strip()
                if key == "define":
                    continue
                if key == "nsteps":
                    line = "nsteps = 500" if mdp.stem == "em" else "nsteps = 20"
                if key in ("nstenergy", "nstlog", "nstxout-compressed"):
                    line = key + " = 10"
                lines.append(line)
            mdp.write_text("\n".join(lines) + "\n")
        for stage in ("em", "nvt", "npt", "production"):
            command = [sys.executable, str(SCRIPTS / "run_md_stages.py"),
                       "--project", str(case), "--gmx", gmx,
                       "--from-stage", stage, "--ntomp", "1", "--accelerator", "cpu"]
            if stage == "production":
                command.append("--approve-production")
            run(command)
            record = json.loads((case / f"simulation/{stage}/run_record.json").read_text())
            assert record["status"] == "executed_requires_scientific_review"
        run(command + ["--resume"])
    except Exception:
        print(f"Smoke test failed. Inspect {log}")
        raise
    print(f"Real GROMACS EM/NVT/NPT/production and resume passed. Local artifacts: {directory}")
    print("Twenty-step stages check software execution only, not convergence or scientific validity.")


if __name__ == "__main__":
    main()
