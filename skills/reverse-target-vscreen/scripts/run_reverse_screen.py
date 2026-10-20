#!/usr/bin/env python3
"""Run the Open Babel and UniDock stages of a reverse target screen."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILLS_ROOT = Path(__file__).resolve().parents[2]
UNIDOCK_RUNNER = SKILLS_ROOT / "unidock-vscreen/scripts/run_unidock_screen.py"
PREFLIGHT_CHECK = Path(__file__).resolve().with_name("check_reverse_vscreen.py")
UDP = Path(os.environ.get("UNIDOCK_PRO_BIN") or shutil.which("udp") or Path.home() / "UniDock-Pro/build/udp")
REQUIRED = ["target_id", "receptor", "center_x", "center_y", "center_z", "size_x", "size_y", "size_z"]
RESULT_FIELDS = [
    "provisional_rank",
    "target_id",
    "status",
    "best_score",
    "mean_score",
    "num_modes",
    "calibrated_z",
    "rank_basis",
    "pocket_source",
    "pocket_confidence",
    "center_x",
    "center_y",
    "center_z",
    "size_x",
    "size_y",
    "size_z",
    "receptor",
    "receptor_pdb",
    "reference_ligand",
    "ligand_original",
    "ligand_pdbqt",
    "result_file",
    "case_dir",
    "message",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a reverse UniDock target screen and build follow-up queues.")
    ligand = parser.add_mutually_exclusive_group(required=True)
    ligand.add_argument("--ligand", help="Input SDF, MOL2, PDB, PDBQT, SMI, or SMILES file.")
    ligand.add_argument("--smiles", help="One SMILES string.")
    parser.add_argument("--target-manifest", required=True, help="CSV or TSV target manifest.")
    parser.add_argument("--out-dir", required=True, help="New output directory.")
    parser.add_argument("--udp", default=str(UDP))
    parser.add_argument("--search-mode", choices=["fast", "balance", "detail"], default="fast")
    parser.add_argument("--scoring", choices=["vina", "vinardo"], default="vina")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--exhaustiveness", type=int)
    parser.add_argument("--num-modes", type=int, default=9)
    parser.add_argument("--energy-range", type=float, default=3.0)
    parser.add_argument("--ph", type=float, help="Optional Open Babel protonation pH; omit to preserve input state.")
    parser.add_argument("--gnina-percent", type=float, default=10.0)
    parser.add_argument("--diffdock-count", type=int, default=10)
    parser.add_argument("--chai-count", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    dialect = csv.excel_tab if path.suffix.lower() in {".tsv", ".tab"} else csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    fields = reader.fieldnames or []
    missing = [name for name in REQUIRED if name not in fields]
    if missing:
        raise SystemExit(f"Target manifest is missing required columns: {', '.join(missing)}")
    rows = [{str(key): (value or "").strip() for key, value in row.items()} for row in reader]
    if not rows:
        raise SystemExit("Target manifest contains no target rows.")
    return rows


def resolve_path(raw: str, base: Path) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def safe_id(raw: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "._-" else "_" for char in raw.strip())
    return cleaned.strip("._-")


def run_command(cmd: list[str], log: Path | None = None) -> subprocess.CompletedProcess[str]:
    if log is None:
        return subprocess.run(cmd, text=True, capture_output=True, check=False)
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        return subprocess.run(cmd, text=True, stdout=handle, stderr=subprocess.STDOUT, check=False)


def prepare_ligand(args: argparse.Namespace, inputs: Path) -> tuple[Path, Path | None, dict[str, Any]]:
    obabel = shutil.which(os.path.expanduser(os.environ.get("OBABEL_BIN") or "obabel"))
    if not obabel:
        raise SystemExit("Open Babel executable 'obabel' was not found.")

    original: Path | None = None
    source_for_conversion: Path
    preparation: dict[str, Any] = {"open_babel": obabel, "ph": args.ph}
    if args.smiles:
        source_for_conversion = inputs / "ligand_original.smi"
        source_for_conversion.write_text(f"{args.smiles}\tquery_ligand\n", encoding="utf-8")
        original = source_for_conversion
        sdf = inputs / "ligand.sdf"
        cmd = [obabel, str(source_for_conversion), "-O", str(sdf), "--gen3d"]
        proc = run_command(cmd)
        if proc.returncode != 0 or not sdf.is_file():
            raise SystemExit(f"Open Babel failed to generate 3D SDF: {proc.stderr.strip()}")
        source_for_conversion = sdf
        preparation["generated_3d_from_smiles"] = True
    else:
        ligand_path = Path(args.ligand).expanduser().resolve()
        if not ligand_path.is_file():
            raise SystemExit(f"Ligand file not found: {ligand_path}")
        original = inputs / f"ligand_original{ligand_path.suffix.lower()}"
        shutil.copy2(ligand_path, original)
        source_for_conversion = original
        preparation["generated_3d_from_smiles"] = ligand_path.suffix.lower() in {".smi", ".smiles"}

    ligand_pdbqt = inputs / "ligand.pdbqt"
    if source_for_conversion.suffix.lower() == ".pdbqt":
        shutil.copy2(source_for_conversion, ligand_pdbqt)
    else:
        cmd = [obabel, str(source_for_conversion), "-O", str(ligand_pdbqt)]
        if source_for_conversion.suffix.lower() in {".smi", ".smiles"}:
            cmd.append("--gen3d")
        if args.ph is not None:
            cmd.extend(["-p", str(args.ph)])
        proc = run_command(cmd)
        if proc.returncode != 0 or not ligand_pdbqt.is_file():
            raise SystemExit(f"Open Babel failed to create PDBQT: {proc.stderr.strip()}")
    preparation["pdbqt"] = str(ligand_pdbqt)
    return ligand_pdbqt, original, preparation


def numeric(row: dict[str, str], names: list[str]) -> list[float]:
    try:
        values = [float(row[name]) for name in names]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid numeric field: {exc}") from exc
    return values


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_case_score(case_dir: Path) -> dict[str, str]:
    score_path = case_dir / "report" / "all_scores.csv"
    if not score_path.is_file():
        return {}
    with score_path.open(newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle), {})


def queue_rows(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    return rows[: max(0, min(count, len(rows)))]


def run_preflight(udp: str) -> dict[str, Any]:
    proc = run_command([sys.executable, str(PREFLIGHT_CHECK), "--deep", "--udp", udp])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "core_ready": False,
            "error": proc.stderr.strip() or proc.stdout.strip() or "preflight returned invalid JSON",
        }


def queued_status(has_rows: bool, ready: bool) -> str:
    if not has_rows:
        return "not_queued"
    return "queued" if ready else "blocked"


def main() -> int:
    args = parse_args()
    manifest = Path(args.target_manifest).expanduser().resolve()
    out = Path(args.out_dir).expanduser().resolve()
    if not manifest.is_file():
        raise SystemExit(f"Target manifest not found: {manifest}")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Output directory is not empty; choose a new directory: {out}")

    inputs = out / "inputs"
    screening = out / "screening"
    report = out / "report"
    queues = report / "queues"
    for directory in (inputs, screening / "unidock", screening / "logs", report, queues):
        directory.mkdir(parents=True, exist_ok=True)

    preflight = run_preflight(args.udp)
    (report / "preflight.json").write_text(json.dumps(preflight, indent=2), encoding="utf-8")
    if not preflight.get("core_ready", False):
        raise SystemExit(f"Core reverse-screening dependencies are not ready; see {report / 'preflight.json'}")

    rows = read_manifest(manifest)
    target_ids = [safe_id(row["target_id"]) for row in rows]
    if any(not item for item in target_ids) or len(set(target_ids)) != len(target_ids):
        raise SystemExit("Every target_id must be nonempty and unique after filesystem-safe normalization.")

    shutil.copy2(manifest, inputs / "target_manifest.csv")
    ligand_pdbqt, ligand_original, ligand_preparation = prepare_ligand(args, inputs)
    ligand_index = inputs / "ligand_index.txt"
    ligand_index.write_text(str(ligand_pdbqt) + "\n", encoding="utf-8")

    config = {
        "ligand_original": str(ligand_original) if ligand_original else None,
        "ligand_pdbqt": str(ligand_pdbqt),
        "target_manifest": str(manifest),
        "target_count": len(rows),
        "search_mode": args.search_mode,
        "scoring": args.scoring,
        "seed": args.seed,
        "exhaustiveness": args.exhaustiveness,
        "num_modes": args.num_modes,
        "energy_range": args.energy_range,
        "dry_run": args.dry_run,
        "ligand_preparation": ligand_preparation,
    }
    (inputs / "run_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    manifest_base = manifest.parent
    for row, target_id in zip(rows, target_ids):
        receptor = resolve_path(row["receptor"], manifest_base)
        receptor_pdb = resolve_path(row.get("receptor_pdb", ""), manifest_base)
        reference = resolve_path(row.get("reference_ligand", ""), manifest_base)
        case_dir = screening / "unidock" / target_id
        result: dict[str, Any] = {
            "provisional_rank": "",
            "target_id": target_id,
            "status": "planned" if args.dry_run else "failed",
            "best_score": "",
            "mean_score": "",
            "num_modes": "",
            "calibrated_z": "",
            "rank_basis": "not_scored" if args.dry_run else "",
            "pocket_source": row.get("pocket_source", ""),
            "pocket_confidence": row.get("pocket_confidence", ""),
            "center_x": row.get("center_x", ""),
            "center_y": row.get("center_y", ""),
            "center_z": row.get("center_z", ""),
            "size_x": row.get("size_x", ""),
            "size_y": row.get("size_y", ""),
            "size_z": row.get("size_z", ""),
            "receptor": str(receptor) if receptor else "",
            "receptor_pdb": str(receptor_pdb) if receptor_pdb else "",
            "reference_ligand": str(reference) if reference else "",
            "ligand_original": str(ligand_original) if ligand_original else "",
            "ligand_pdbqt": str(ligand_pdbqt),
            "result_file": "",
            "case_dir": str(case_dir),
            "message": "",
            "protein_sequence": row.get("protein_sequence", ""),
            "uniprot": row.get("uniprot", ""),
            "gene": row.get("gene", ""),
            "species": row.get("species", ""),
        }
        try:
            if not receptor or not receptor.is_file():
                raise ValueError(f"receptor not found: {receptor}")
            center = numeric(row, ["center_x", "center_y", "center_z"])
            size = numeric(row, ["size_x", "size_y", "size_z"])
            if any(value <= 0 for value in size):
                raise ValueError("box sizes must be positive")
            if reference and not reference.is_file():
                raise ValueError(f"reference ligand not found: {reference}")
            if reference and reference.suffix.lower() != ".pdbqt":
                raise ValueError("UniDock reference_ligand must be a prepared PDBQT file")

            cmd = [
                sys.executable,
                str(UNIDOCK_RUNNER),
                "--udp",
                args.udp,
                "--receptor",
                str(receptor),
                "--ligand-index",
                str(ligand_index),
                "--center",
                *(str(value) for value in center),
                "--size",
                *(str(value) for value in size),
                "--search-mode",
                args.search_mode,
                "--scoring",
                args.scoring,
                "--out-dir",
                str(case_dir),
                "--seed",
                str(args.seed),
                "--num-modes",
                str(args.num_modes),
                "--energy-range",
                str(args.energy_range),
                "--top",
                "1",
            ]
            if args.exhaustiveness is not None:
                cmd.extend(["--exhaustiveness", str(args.exhaustiveness)])
            if reference:
                cmd.extend(["--reference-ligand", str(reference)])
            if args.dry_run:
                cmd.append("--dry-run")
            proc = run_command(cmd, screening / "logs" / f"{target_id}.log")
            if proc.returncode != 0:
                raise ValueError(f"UniDock stage returned {proc.returncode}; see screening/logs/{target_id}.log")

            if args.dry_run:
                result["message"] = "validated and command prepared"
            else:
                score = parse_case_score(case_dir)
                if not score:
                    raise ValueError("no parseable UniDock score")
                result.update(
                    status="complete",
                    best_score=score.get("best_score", ""),
                    mean_score=score.get("mean_score", ""),
                    num_modes=score.get("num_modes", ""),
                    result_file=score.get("result_file", ""),
                )
                mean_raw = row.get("calibration_mean", "")
                sd_raw = row.get("calibration_sd", "")
                if mean_raw and sd_raw and float(sd_raw) > 0:
                    z_score = (float(result["best_score"]) - float(mean_raw)) / float(sd_raw)
                    result["calibrated_z"] = round(z_score, 4)
                    result["rank_basis"] = "target_specific_z_score"
                else:
                    result["rank_basis"] = "uncalibrated_raw_score"
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            result["status"] = "failed"
            result["message"] = str(exc)
            failures.append({"target_id": target_id, "error": str(exc)})
        results.append(result)

    completed_all = [row for row in results if row["status"] == "complete"]
    calibrated = sorted(
        [row for row in completed_all if row["calibrated_z"] != ""],
        key=lambda row: (float(row["calibrated_z"]), row["target_id"]),
    )
    uncalibrated = sorted(
        [row for row in completed_all if row["calibrated_z"] == ""],
        key=lambda row: (float(row["best_score"]), row["target_id"]),
    )
    for group in (calibrated, uncalibrated):
        for index, row in enumerate(group, start=1):
            row["provisional_rank"] = index
    completed = calibrated + uncalibrated
    planned = [row for row in results if row["status"] == "planned"]
    ranking = completed + planned + [row for row in results if row["status"] == "failed"]
    write_csv(report / "reverse_ranking.csv", ranking, RESULT_FIELDS)
    write_csv(report / "target_failures.csv", failures, ["target_id", "error"])

    queue_source = completed if completed else planned
    if calibrated and uncalibrated:
        fraction = max(0.0, min(args.gnina_percent, 100.0)) / 100.0
        gnina_rows = queue_rows(calibrated, math.ceil(len(calibrated) * fraction))
        gnina_rows += queue_rows(uncalibrated, math.ceil(len(uncalibrated) * fraction))
    else:
        gnina_count = math.ceil(len(queue_source) * max(0.0, min(args.gnina_percent, 100.0)) / 100.0)
        gnina_rows = queue_rows(queue_source, gnina_count)
    uncertain = [
        row
        for row in queue_source
        if row["pocket_confidence"].upper() in {"C", "D"}
        or row["pocket_source"].lower() in {"predicted", "unknown", "blind"}
    ]
    diffdock_rows = queue_rows(uncertain, args.diffdock_count)
    chai_rows = queue_rows(queue_source, args.chai_count)
    interaction_rows = queue_rows(queue_source, args.chai_count)
    gnina_rows = [{**row, "queue_reason": "top_fraction_within_rank_basis"} for row in gnina_rows]
    diffdock_rows = [{**row, "queue_reason": "uncertain_or_predicted_pocket"} for row in diffdock_rows]
    chai_rows = [{**row, "queue_reason": "small_final_orthogonal_check"} for row in chai_rows]
    interaction_rows = [{**row, "queue_reason": "final_pose_interaction_review"} for row in interaction_rows]
    queue_fields = RESULT_FIELDS + ["queue_reason", "protein_sequence", "uniprot", "gene", "species"]
    write_csv(queues / "gnina_queue.csv", gnina_rows, queue_fields)
    write_csv(queues / "diffdock_queue.csv", diffdock_rows, queue_fields)
    write_csv(queues / "chai1_queue.csv", chai_rows, queue_fields)
    write_csv(queues / "interaction_queue.csv", interaction_rows, queue_fields)

    follow_up = preflight.get("follow_up", {})
    gnina_ready = bool(follow_up.get("gnina_runtime", {}).get("complete", False))
    diffdock_ready = bool(follow_up.get("diffdock_skill", {}).get("available", False)) and bool(
        follow_up.get("diffdock_credentials", {}).get("configured", False)
    )
    chai_ready = bool(follow_up.get("chai1", {}).get("available", False))
    interaction_ready = bool(follow_up.get("plip", {}).get("available", False)) and bool(
        follow_up.get("structure_viewer", {}).get("available", False)
    )
    stage_status = {
        "ligand_preparation": "complete",
        "unidock": "planned" if args.dry_run else ("complete" if completed else "failed"),
        "gnina": queued_status(bool(gnina_rows), gnina_ready),
        "diffdock": queued_status(bool(diffdock_rows), diffdock_ready),
        "chai1": queued_status(bool(chai_rows), chai_ready),
        "plip_structure_viewer": queued_status(bool(interaction_rows), interaction_ready),
        "requested_targets": len(results),
        "completed_targets": len(completed),
        "failed_targets": len(failures),
        "calibrated_targets": len(calibrated),
        "uncalibrated_targets": len(uncalibrated),
        "mixed_calibration_groups": bool(calibrated and uncalibrated),
        "dry_run": args.dry_run,
    }
    (report / "stage_status.json").write_text(json.dumps(stage_status, indent=2), encoding="utf-8")
    (report / "summary.md").write_text(
        "# Reverse target screening summary\n\n"
        f"- Requested targets: {len(results)}\n"
        f"- Completed UniDock targets: {len(completed)}\n"
        f"- Failed targets: {len(failures)}\n"
        f"- Calibrated targets: {len(calibrated)}\n"
        f"- Uncalibrated targets: {len(uncalibrated)}\n"
        f"- GNINA queue: {len(gnina_rows)}\n"
        f"- DiffDock unknown-pocket queue: {len(diffdock_rows)}\n"
        f"- Chai-1 final-check queue: {len(chai_rows)}\n\n"
        f"- GNINA stage status: {stage_status['gnina']}\n"
        f"- DiffDock stage status: {stage_status['diffdock']}\n"
        f"- Chai-1 stage status: {stage_status['chai1']}\n"
        f"- PLIP/viewer stage status: {stage_status['plip_structure_viewer']}\n\n"
        "Ranks restart within each rank_basis group. Raw scores across different receptors are exploratory unless target-specific calibration is supplied.\n",
        encoding="utf-8",
    )

    print(f"Project: {out}")
    print(f"Targets: {len(results)}; completed: {len(completed)}; failed: {len(failures)}")
    print(f"Ranking: {report / 'reverse_ranking.csv'}")
    return 0 if args.dry_run or completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
