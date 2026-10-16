#!/usr/bin/env python3
"""Initialize a three-directory GROMACS MD case without launching simulation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


SCENARIOS = {
    "single-protein": ["rmsd", "rmsf", "radius_of_gyration", "sasa", "secondary_structure", "pca_fel"],
    "protein-protein": ["complex_rmsd", "partner_rmsd", "interface_contacts", "interchain_hbonds", "partner_distance", "buried_sasa"],
    "protein-nucleic-acid": ["protein_rmsd", "nucleic_acid_rmsd", "interface_contacts", "interface_hbonds", "base_pair_geometry", "ion_bridges"],
    "protein-small-molecule": ["protein_rmsd", "fitted_ligand_rmsd", "ligand_pocket_distance", "hbonds", "contact_occupancy", "mmpbsa_optional"],
    "protein-metal": ["protein_rmsd", "metal_donor_distances", "coordination_number", "coordination_angles", "geometry_deviation", "water_exchange"],
}

STAGES = [
    ("01", "structure_preparation"),
    ("02", "topology_generation"),
    ("03", "box_solvation_ions"),
    ("04", "energy_minimization"),
    ("05", "nvt_equilibration"),
    ("06", "npt_equilibration"),
    ("07", "production_md"),
    ("08", "trajectory_processing"),
    ("09", "analysis_and_plotting"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--input", required=True, type=Path, help="Starting PDB/GRO or other structure file")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    if not source.is_file():
        parser.error(f"input file does not exist: {source}")
    if out_dir.exists() and any(out_dir.iterdir()):
        parser.error(f"output directory is not empty: {out_dir}")

    inputs = out_dir / "inputs"
    simulation = out_dir / "simulation"
    analysis = out_dir / "analysis"
    for directory in (inputs, simulation, analysis):
        directory.mkdir(parents=True, exist_ok=True)

    copied_input = inputs / source.name
    shutil.copy2(source, copied_input)

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": args.scenario,
        "source_input": str(source),
        "copied_input": str(copied_input),
        "input_sha256": sha256(copied_input),
        "top_level_directories": ["inputs", "simulation", "analysis"],
        "production_approved": False,
    }
    write_text(inputs / "case_config.json", json.dumps(manifest, indent=2) + "\n")

    stage_lines = ["order\tstage\tstatus\tnotes"]
    for order, stage in STAGES:
        note = "requires explicit user approval" if stage == "production_md" else ""
        stage_lines.append(f"{order}\t{stage}\tpending\t{note}")
    write_text(simulation / "stage_plan.tsv", "\n".join(stage_lines) + "\n")

    analysis_lines = ["metric\tstatus\tselection_or_definition\toutput"]
    analysis_lines.extend(f"{metric}\tpending\tTBD\tTBD" for metric in SCENARIOS[args.scenario])
    write_text(analysis / "analysis_plan.tsv", "\n".join(analysis_lines) + "\n")

    print(f"Initialized {args.scenario} case: {out_dir}")
    print("Top-level directories: inputs, simulation, analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
