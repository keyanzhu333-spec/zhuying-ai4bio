#!/usr/bin/env python3
"""Plot numeric series from GROMACS XVG files and write an output index."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SCENARIOS = (
    "single-protein",
    "protein-protein",
    "protein-nucleic-acid",
    "protein-small-molecule",
    "protein-metal",
)

QUOTED = re.compile(r'"([^"]+)"')


def quoted_value(line: str) -> str | None:
    match = QUOTED.search(line)
    return match.group(1) if match else None


def parse_xvg(path: Path) -> tuple[dict[str, str], list[list[float]]]:
    metadata: dict[str, str] = {}
    rows: list[list[float]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("@"):
                value = quoted_value(line)
                if value and " title " in f" {line} ":
                    metadata["title"] = value
                elif value and "xaxis" in line and "label" in line:
                    metadata["xlabel"] = value
                elif value and "yaxis" in line and "label" in line:
                    metadata["ylabel"] = value
                elif value and " legend " in f" {line} ":
                    key_match = re.search(r"s(\d+)\s+legend", line)
                    if key_match:
                        metadata[f"legend_{key_match.group(1)}"] = value
                continue
            try:
                values = [float(item) for item in line.split()]
            except ValueError:
                continue
            if len(values) >= 2:
                rows.append(values)
    return metadata, rows


def safe_stem(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    return "__".join(re.sub(r"[^A-Za-z0-9_.-]+", "_", part) for part in parts)


def plot_one(path: Path, input_dir: Path, out_dir: Path, formats: list[str], dpi: int) -> dict[str, str] | None:
    metadata, rows = parse_xvg(path)
    if not rows:
        return None
    width = min(len(row) for row in rows)
    if width < 2:
        return None
    x = [row[0] for row in rows]
    relative = path.relative_to(input_dir)
    stem = safe_stem(relative)

    fig, axis = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    for column in range(1, width):
        label = metadata.get(f"legend_{column - 1}")
        if not label and width > 2:
            label = f"Series {column}"
        axis.plot(x, [row[column] for row in rows], linewidth=1.35, label=label)
    axis.set_title(metadata.get("title", relative.stem.replace("_", " ")))
    axis.set_xlabel(metadata.get("xlabel", "X"))
    axis.set_ylabel(metadata.get("ylabel", "Y"))
    axis.grid(True, linewidth=0.5, alpha=0.25)
    if width > 2 or metadata.get("legend_0"):
        axis.legend(frameon=False)

    outputs: list[str] = []
    for extension in formats:
        output = out_dir / f"{stem}.{extension}"
        fig.savefig(output, dpi=dpi)
        outputs.append(str(output))
    plt.close(fig)
    return {
        "source": str(path),
        "points": str(len(rows)),
        "series": str(width - 1),
        "outputs": ";".join(outputs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--formats", default="png,pdf", help="Comma-separated: png,pdf,svg")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    input_dir = args.input_dir.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    if not input_dir.is_dir():
        parser.error(f"input directory does not exist: {input_dir}")
    formats = [item.strip().lower() for item in args.formats.split(",") if item.strip()]
    allowed = {"png", "pdf", "svg"}
    if not formats or any(item not in allowed for item in formats):
        parser.error("formats must be a comma-separated subset of png,pdf,svg")
    if args.dpi < 72:
        parser.error("dpi must be at least 72")

    sources = sorted(input_dir.rglob("*.xvg"))
    if not sources:
        parser.error(f"no XVG files found under: {input_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    skipped = []
    for source in sources:
        record = plot_one(source, input_dir, out_dir, formats, args.dpi)
        if record:
            record["scenario"] = args.scenario
            records.append(record)
        else:
            skipped.append(str(source))

    if not records:
        parser.error("XVG files were found, but none contained at least two numeric columns")
    index_path = out_dir / "plot_index.csv"
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scenario", "source", "points", "series", "outputs"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Plotted {len(records)} XVG file(s) for {args.scenario}: {out_dir}")
    if skipped:
        print(f"Skipped {len(skipped)} file(s) without plottable numeric data")
    print(f"Index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
