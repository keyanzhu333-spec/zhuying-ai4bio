#!/usr/bin/env python3
"""Predict an antibody Fab structure with local IgFold."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


VALID_AA = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")


def read_sequence(value: str) -> str:
    """Read a sequence from text, @file, or file path and remove non-sequence text."""
    if value.startswith("@"):
        raw = Path(value[1:]).read_text()
    else:
        path = Path(value)
        raw = path.read_text() if path.exists() and path.is_file() else value

    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if ":" in stripped and re.match(r"^(VH|VL|H|L)\s*:", stripped, re.I):
            stripped = stripped.split(":", 1)[1]
        lines.append(stripped)

    seq = re.sub(r"[^A-Za-z]", "", "".join(lines)).upper()
    bad = sorted(set(seq) - VALID_AA)
    if not seq:
        raise ValueError("Empty sequence after cleaning input")
    if bad:
        raise ValueError(f"Unsupported residue letters in sequence: {''.join(bad)}")
    return seq


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predict a Fab PDB from VH and VL sequences using local IgFold."
    )
    parser.add_argument("--vh", required=True, help="VH sequence text, @file, or file path")
    parser.add_argument("--vl", required=True, help="VL sequence text, @file, or file path")
    parser.add_argument("--name", default="antibody_fab", help="Output file stem")
    parser.add_argument("--out-dir", required=True, help="Directory for FASTA/PDB/summary")
    parser.add_argument("--num-models", type=int, default=2, help="Number of IgFold checkpoints")
    parser.add_argument("--cpu", action="store_true", help="Force CPU instead of GPU")
    parser.add_argument("--refine", action="store_true", help="Run OpenMM/PyRosetta refinement")
    parser.add_argument("--no-renum", action="store_true", help="Disable AbNumber renumbering")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    conda_bin = Path(sys.prefix) / "bin"
    os.environ["PATH"] = f"{conda_bin}:{os.environ.get('PATH', '')}"

    from igfold import IgFoldRunner

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sequences = {
        "H": read_sequence(args.vh),
        "L": read_sequence(args.vl),
    }

    fasta = out_dir / f"{args.name}.fasta"
    pdb_path = out_dir / f"{args.name}_igfold.pdb"
    summary = out_dir / f"{args.name}_igfold_summary.txt"

    fasta.write_text(
        f">{args.name}_H\n{sequences['H']}\n>{args.name}_L\n{sequences['L']}\n"
    )

    runner = IgFoldRunner(num_models=args.num_models, try_gpu=not args.cpu)
    out = runner.fold(
        str(pdb_path),
        sequences=sequences,
        do_refine=args.refine,
        do_renum=not args.no_renum,
    )

    summary.write_text(
        f"IgFold Fab model: {args.name}\n"
        f"PDB: {pdb_path}\n"
        f"FASTA: {fasta}\n"
        f"Heavy length: {len(sequences['H'])}\n"
        f"Light length: {len(sequences['L'])}\n"
        f"Total length: {len(sequences['H']) + len(sequences['L'])}\n"
        f"prmsd shape: {tuple(out.prmsd.shape)}\n"
        f"do_refine: {args.refine}\n"
        f"do_renum: {not args.no_renum}\n"
        f"try_gpu: {not args.cpu}\n"
    )

    print(f"PDB={pdb_path}")
    print(f"FASTA={fasta}")
    print(f"SUMMARY={summary}")
    print(f"heavy_len={len(sequences['H'])} light_len={len(sequences['L'])}")
    print(f"prmsd_shape={tuple(out.prmsd.shape)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
