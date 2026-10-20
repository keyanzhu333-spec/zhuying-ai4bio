---
name: unidock-vscreen
display_name: UniDock-Pro 虚拟筛选
display_name_en: UniDock-Pro Virtual Screening
description: Run local UniDock-Pro GPU virtual screening for receptor-ligand libraries. Use when the user asks to screen many small molecules, run UniDock or UniDock-Pro, dock a PDBQT receptor against a ligand directory or ligand index, use reference-ligand guided or hybrid docking, batch large PDBQT libraries, rank docking scores, summarize top hits, or prepare a virtual-screening report from UniDock outputs.
description_zh: 用本地 UniDock-Pro 对受体-配体库做 GPU 虚拟筛选，支持参考配体引导或混合对接、PDBQT 批量库、打分排序与命中汇总。适用于高通量小分子筛选与候选优先排序。
description_en: Run local UniDock-Pro GPU virtual screening for receptor-ligand libraries. Use for high-throughput small-molecule screening, reference-ligand guided or hybrid docking, batch PDBQT libraries, score ranking, and top-hit summarization.
category: 科研/生物
version: 1.0.0
author: 小猪莹(keyanzhu999)
---

# UniDock VScreen

Use this skill for local high-throughput protein-small molecule virtual screening with UniDock-Pro. Prefer it over single-ligand docking skills when the user has many `.pdbqt` ligands or asks for screening, ranking, top hits, or batch docking.

Find the UniDock-Pro `udp` executable from `UNIDOCK_PRO_BIN`, `PATH`, or `~/UniDock-Pro/build/udp`. Pass `--udp` to override it for a run.

Maintainer's local installation:

```text
~/UniDock-Pro/build/udp
```

## Workflow

1. Confirm inputs before running: receptor `.pdbqt` or `.pdb`, ligand directory or ligand index of `.pdbqt` files, search box center and size in Angstrom, and `search_mode` (`fast`, `balance`, or `detail`).
2. Run `scripts/check_unidock.py` to verify the UniDock-Pro binary and version.
3. Use `scripts/run_unidock_screen.py` for new screening runs. It creates exactly three top-level output folders: `inputs/`, `docking/`, and `report/`.
4. Use `scripts/analyze_unidock_results.py` when the user already has UniDock result files and only needs ranking or interpretation.
5. Read `references/workflow.md` for parameter choices, failure handling, and report interpretation.

## Commands

Check the local binary:

```bash
python scripts/check_unidock.py
```

Run a screen from a ligand directory:

```bash
python scripts/run_unidock_screen.py \
  --receptor receptor.pdbqt \
  --ligand-dir ligands/ \
  --center 30.346 43.402 53.131 \
  --size 30 30 30 \
  --search-mode fast \
  --out-dir unidock_screen
```

Run a reference-ligand guided or hybrid screen:

```bash
python scripts/run_unidock_screen.py \
  --receptor receptor.pdbqt \
  --reference-ligand ref_ligand.pdbqt \
  --ligand-index ligand_index.txt \
  --center 32.790 38.342 58.486 \
  --size 28 28 28 \
  --search-mode balance \
  --out-dir unidock_hybrid_screen
```

Analyze existing outputs:

```bash
python scripts/analyze_unidock_results.py \
  --results-dir docking/results \
  --log docking/unidock.log \
  --out-dir report
```

## Output Rules

Keep each run in one project directory with only these top-level folders:

```text
project/
├── inputs/
├── docking/
└── report/
```

- `inputs/`: copied receptor, normalized ligand index, batch files, and `run_config.json`.
- `docking/`: UniDock raw PDBQT outputs, logs, and failed-batch records.
- `report/`: `top_hits.csv`, `all_scores.csv`, `summary.txt`, and parsed failure tables.

Do not claim docking scores are experimental affinity. Report them as scoring-function estimates useful for prioritization. Always include the receptor, ligand source, box center/size, search mode, scoring function, and number of successfully parsed outputs.
