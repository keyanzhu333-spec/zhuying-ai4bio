#!/usr/bin/env python3
"""Rank UniDock-Pro PDBQT outputs and summarize logs."""

from __future__ import annotations

import argparse
import csv
import re
import statistics
from pathlib import Path


VINA_RE = re.compile(r"REMARK VINA RESULT:\s*([-+]?\d+(?:\.\d+)?)")
NAME_RE = re.compile(r"REMARK\s+Name\s*=\s*(.+)")
LIGAND_NAME_RE = re.compile(r"Ligand name:\s*(.+)")


def parse_pdbqt(path: Path) -> dict[str, object] | None:
    scores: list[float] = []
    source_name = ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            score_match = VINA_RE.search(line)
            if score_match:
                scores.append(float(score_match.group(1)))
            if not source_name:
                name_match = NAME_RE.search(line)
                if name_match:
                    source_name = name_match.group(1).strip()
    if not scores:
        return None
    return {
        "ligand_id": path.name.removesuffix("_out.pdbqt").removesuffix(".pdbqt"),
        "result_file": str(path),
        "source_name": source_name,
        "best_score": round(min(scores), 3),
        "mean_score": round(statistics.fmean(scores), 3),
        "num_modes": len(scores),
    }


def parse_failed_ligands(log_path: Path | None) -> list[dict[str, str]]:
    if not log_path or not log_path.exists():
        return []
    failures: list[dict[str, str]] = []
    pending_error = ""
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if "Structure parsing error:" in stripped:
                pending_error = stripped
            else:
                ligand_match = LIGAND_NAME_RE.search(stripped)
                if ligand_match:
                    failures.append(
                        {
                            "ligand": ligand_match.group(1).strip(),
                            "error": pending_error,
                        }
                    )
                    pending_error = ""
    return failures


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze UniDock-Pro virtual-screening outputs.")
    parser.add_argument("--results-dir", required=True, help="Directory containing UniDock output PDBQT files.")
    parser.add_argument("--log", help="UniDock log file to parse for malformed ligands.")
    parser.add_argument("--out-dir", required=True, help="Report output directory.")
    parser.add_argument("--top", type=int, default=50, help="Number of top hits to write.")
    args = parser.parse_args()

    results_dir = Path(args.results_dir).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    log_path = Path(args.log).expanduser() if args.log else None
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for pdbqt in sorted(results_dir.rglob("*.pdbqt")):
        parsed = parse_pdbqt(pdbqt)
        if parsed:
            rows.append(parsed)
    rows.sort(key=lambda item: (float(item["best_score"]), str(item["ligand_id"])))

    fields = ["rank", "ligand_id", "best_score", "mean_score", "num_modes", "result_file", "source_name"]
    ranked_rows = [{"rank": index + 1, **row} for index, row in enumerate(rows)]
    write_csv(out_dir / "all_scores.csv", ranked_rows, fields)
    write_csv(out_dir / "top_hits.csv", ranked_rows[: args.top], fields)

    failures = parse_failed_ligands(log_path)
    write_csv(out_dir / "failed_ligands.csv", failures, ["ligand", "error"])

    best = ranked_rows[0]["best_score"] if ranked_rows else "NA"
    with (out_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("UniDock-Pro virtual screening summary\n")
        handle.write("====================================\n")
        handle.write(f"Results directory: {results_dir}\n")
        handle.write(f"Log file: {log_path or 'NA'}\n")
        handle.write(f"Parsed output files: {len(rows)}\n")
        handle.write(f"Parsed failed ligands from log: {len(failures)}\n")
        handle.write(f"Best docking score: {best}\n")
        handle.write("\nInterpretation: lower Vina-style scores are better only within the same receptor, box, scoring function, and search settings.\n")

    print(f"Wrote {out_dir / 'top_hits.csv'}")
    print(f"Wrote {out_dir / 'all_scores.csv'}")
    print(f"Wrote {out_dir / 'summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
