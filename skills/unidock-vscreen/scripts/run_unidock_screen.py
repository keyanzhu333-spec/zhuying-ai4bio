#!/usr/bin/env python3
"""Run a UniDock-Pro virtual screen with organized outputs."""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_UDP = os.environ.get("UNIDOCK_PRO_BIN") or shutil.which("udp") or str(Path.home() / "UniDock-Pro/build/udp")


def collect_ligands(ligand_dir: str | None, ligand_index: str | None) -> list[Path]:
    if ligand_dir:
        root = Path(ligand_dir).expanduser()
        if not root.is_dir():
            raise SystemExit(f"Ligand directory does not exist: {root}")
        ligands = sorted(root.glob("*.pdbqt"))
    else:
        index_path = Path(ligand_index or "").expanduser()
        if not index_path.is_file():
            raise SystemExit(f"Ligand index does not exist: {index_path}")
        base = index_path.parent
        ligands = []
        for raw in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
            item = raw.strip()
            if not item or item.startswith("#"):
                continue
            path = Path(item).expanduser()
            if not path.is_absolute():
                path = base / path
            ligands.append(path)
    return [path.resolve() for path in ligands if path.name.endswith(".pdbqt")]


def write_index(path: Path, ligands: list[Path]) -> None:
    path.write_text("\n".join(str(ligand) for ligand in ligands) + "\n", encoding="utf-8")


def batched(items: list[Path], batch_size: int) -> list[list[Path]]:
    if batch_size <= 0:
        return [items]
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local UniDock-Pro virtual screening.")
    parser.add_argument("--udp", default=DEFAULT_UDP, help="Path to UniDock-Pro udp binary.")
    parser.add_argument("--receptor", required=True, help="Prepared receptor PDBQT/PDB.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--ligand-dir", help="Directory containing ligand PDBQT files.")
    input_group.add_argument("--ligand-index", help="Text file containing ligand PDBQT paths.")
    parser.add_argument("--reference-ligand", nargs="*", default=[], help="Reference ligand PDBQT file(s).")
    parser.add_argument("--center", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--size", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--search-mode", choices=["fast", "balance", "detail"], required=True)
    parser.add_argument("--scoring", choices=["vina", "vinardo"], default="vina")
    parser.add_argument("--out-dir", required=True, help="Project output directory.")
    parser.add_argument("--batch-size", type=int, default=0, help="Ligands per UniDock call; 0 means one batch.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--exhaustiveness", type=int, default=None)
    parser.add_argument("--num-modes", type=int, default=None)
    parser.add_argument("--energy-range", type=float, default=None)
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true", help="Prepare inputs and command files without running UniDock.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory.")
    args = parser.parse_args()

    resolved = shutil.which(os.path.expanduser(args.udp))
    if not resolved:
        raise SystemExit("UniDock-Pro binary missing or not executable; set --udp or UNIDOCK_PRO_BIN.")
    udp = Path(resolved).resolve()
    receptor = Path(args.receptor).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    if not all(math.isfinite(value) for value in args.center + args.size) or any(value <= 0 for value in args.size):
        parser.error("Box coordinates must be finite and sizes must be positive.")
    if not receptor.is_file():
        raise SystemExit(f"Receptor not found: {receptor}")
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit(f"Output directory is not empty; use --force to replace it: {out_dir}")
    if out_dir.exists() and args.force:
        shutil.rmtree(out_dir)

    inputs_dir = out_dir / "inputs"
    docking_dir = out_dir / "docking"
    report_dir = out_dir / "report"
    results_dir = docking_dir / "results"
    logs_dir = docking_dir / "logs"
    batches_dir = inputs_dir / "batches"
    for directory in [inputs_dir, results_dir, logs_dir, report_dir, batches_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    ligands = collect_ligands(args.ligand_dir, args.ligand_index)
    if not ligands:
        raise SystemExit("No ligand PDBQT files were found.")
    missing = [path for path in ligands if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing ligand files, first missing path: {missing[0]}")

    receptor_copy = inputs_dir / receptor.name
    shutil.copy2(receptor, receptor_copy)
    normalized_index = inputs_dir / "ligand_index.txt"
    write_index(normalized_index, ligands)

    reference_ligands = [str(Path(item).expanduser().resolve()) for item in args.reference_ligand]
    config = {
        "udp": str(udp.resolve()),
        "receptor": str(receptor.resolve()),
        "ligand_count": len(ligands),
        "reference_ligand": reference_ligands,
        "center": args.center,
        "size": args.size,
        "search_mode": args.search_mode,
        "scoring": args.scoring,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "exhaustiveness": args.exhaustiveness,
        "num_modes": args.num_modes,
        "energy_range": args.energy_range,
        "dry_run": args.dry_run,
    }
    (inputs_dir / "run_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    batches = batched(ligands, args.batch_size)
    failed_batches: list[dict[str, object]] = []
    command_log = logs_dir / "commands.txt"
    combined_log = logs_dir / "unidock.log"

    with command_log.open("w", encoding="utf-8") as commands:
        for index, batch in enumerate(batches, start=1):
            batch_index = batches_dir / f"batch_{index:04d}.txt"
            write_index(batch_index, batch)
            cmd = [
                str(udp),
                "--receptor",
                str(receptor_copy),
                "--ligand_index",
                str(batch_index),
                "--center_x",
                str(args.center[0]),
                "--center_y",
                str(args.center[1]),
                "--center_z",
                str(args.center[2]),
                "--size_x",
                str(args.size[0]),
                "--size_y",
                str(args.size[1]),
                "--size_z",
                str(args.size[2]),
                "--search_mode",
                args.search_mode,
                "--scoring",
                args.scoring,
                "--dir",
                str(results_dir),
            ]
            if reference_ligands:
                cmd.extend(["--reference_ligand", *reference_ligands])
            if args.seed is not None:
                cmd.extend(["--seed", str(args.seed)])
            if args.exhaustiveness is not None:
                cmd.extend(["--exhaustiveness", str(args.exhaustiveness)])
            if args.num_modes is not None:
                cmd.extend(["--num_modes", str(args.num_modes)])
            if args.energy_range is not None:
                cmd.extend(["--energy_range", str(args.energy_range)])

            commands.write(shlex.join(cmd) + "\n")
            if args.dry_run:
                continue
            with combined_log.open("a", encoding="utf-8", errors="replace") as log_handle:
                log_handle.write(f"\n=== batch {index}/{len(batches)} size={len(batch)} ===\n")
                proc = subprocess.run(cmd, stdout=log_handle, stderr=subprocess.STDOUT, check=False)
            if proc.returncode != 0:
                failed_batches.append({"batch": index, "ligands": len(batch), "returncode": proc.returncode})

    if failed_batches:
        failed_path = docking_dir / "failed_batches.csv"
        with failed_path.open("w", encoding="utf-8") as handle:
            handle.write("batch,ligands,returncode\n")
            for row in failed_batches:
                handle.write(f"{row['batch']},{row['ligands']},{row['returncode']}\n")

    if not args.dry_run:
        analyzer = Path(__file__).with_name("analyze_unidock_results.py")
        subprocess.run(
            [
                sys.executable,
                str(analyzer),
                "--results-dir",
                str(results_dir),
                "--log",
                str(combined_log),
                "--out-dir",
                str(report_dir),
                "--top",
                str(args.top),
            ],
            check=True,
        )
    else:
        (report_dir / "summary.txt").write_text(
            "Dry run complete. Review inputs/run_config.json and docking/logs/commands.txt before running.\n",
            encoding="utf-8",
        )

    print(f"Project: {out_dir}")
    print(f"Ligands: {len(ligands)}")
    print(f"Batches: {len(batches)}")
    print(f"Expected top-level folders: inputs, docking, report")
    return 1 if failed_batches else 0


if __name__ == "__main__":
    raise SystemExit(main())
