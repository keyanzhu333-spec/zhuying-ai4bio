#!/usr/bin/env python3
"""Initialize a three-directory GROMACS MD case without launching simulation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from string import Template
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


def ns_to_steps(duration_ns: float, timestep_ps: float = 0.002) -> int:
    return round(duration_ns * 1000.0 / timestep_ps)


def render_mdps(destination: Path, values: dict[str, object]) -> None:
    template_dir = Path(__file__).resolve().parents[1] / "assets" / "mdp"
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted(template_dir.glob("*.mdp.template")):
        target = destination / source.name.removesuffix(".template")
        rendered = Template(source.read_text(encoding="utf-8")).substitute(values)
        write_text(target, rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--input", required=True, type=Path, help="Starting PDB/GRO or other structure file")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--temperature", type=float, default=300.0, help="Target temperature in K")
    parser.add_argument("--pressure", type=float, default=1.0, help="Target pressure in bar")
    parser.add_argument("--nvt-ns", type=float, default=0.1, help="NVT duration in ns")
    parser.add_argument("--npt-ns", type=float, default=1.0, help="NPT duration in ns")
    parser.add_argument("--production-ns", type=float, default=10.0, help="Production duration in ns")
    parser.add_argument("--seed", type=int, default=20261020, help="Velocity-generation seed")
    args = parser.parse_args()

    for name in ("temperature", "pressure", "nvt_ns", "npt_ns", "production_ns"):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be finite and positive")
    for name in ("nvt_ns", "npt_ns", "production_ns"):
        if ns_to_steps(getattr(args, name)) < 1:
            parser.error(f"--{name.replace('_', '-')} must contain at least one timestep")

    source = args.input.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    if not source.is_file():
        parser.error(f"input file does not exist: {source}")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        parser.error(f"output directory is not empty: {out_dir}")

    inputs = out_dir / "inputs"
    simulation = out_dir / "simulation"
    analysis = out_dir / "analysis"
    for directory in (inputs, simulation, analysis):
        directory.mkdir(parents=True, exist_ok=True)

    mdp_values = {
        "em_steps": 50000,
        "nvt_steps": ns_to_steps(args.nvt_ns),
        "npt_steps": ns_to_steps(args.npt_ns),
        "production_steps": ns_to_steps(args.production_ns),
        "temperature": args.temperature,
        "pressure": args.pressure,
        "seed": args.seed,
    }
    render_mdps(simulation / "mdp", mdp_values)
    for stage in ("system", "em", "nvt", "npt", "production", "logs"):
        (simulation / stage).mkdir()

    copied_input = inputs / source.name
    shutil.copy2(source, copied_input)

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": args.scenario,
        "source_input": source.name,
        "copied_input": copied_input.relative_to(out_dir).as_posix(),
        "input_sha256": sha256(copied_input),
        "top_level_directories": ["inputs", "simulation", "analysis"],
        "md_parameters": {
            "temperature_k": args.temperature,
            "pressure_bar": args.pressure,
            "timestep_ps": 0.002,
            "nvt_ns": args.nvt_ns,
            "npt_ns": args.npt_ns,
            "production_ns": args.production_ns,
            "seed": args.seed,
        },
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

    run_config = {
        "schema_version": 1,
        "topology": "simulation/system/topol.top",
        "coordinates": "simulation/system/system.gro",
        "index": "simulation/system/index.ndx",
        "reference_coordinates": "simulation/system/system.gro",
        "gromacs_command": "auto",
        "accelerator": "cpu",
        "notes": [
            "Populate simulation/system only after scenario-specific topology validation.",
            "Review generated MDP files before execution; they are starting points, not universal defaults.",
        ],
    }
    write_text(simulation / "run_config.json", json.dumps(run_config, indent=2) + "\n")

    print(f"Initialized {args.scenario} case: {out_dir}")
    print("Top-level directories: inputs, simulation, analysis")
    print("Rendered MDP files: simulation/mdp/{em,nvt,npt,production}.mdp")
    print("Next: build and validate simulation/system/topol.top and system.gro")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
