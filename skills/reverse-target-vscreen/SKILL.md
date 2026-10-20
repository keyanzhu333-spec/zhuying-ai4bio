---
name: reverse-target-vscreen
display_name: 反向靶点虚拟筛选
display_name_en: Reverse Target Virtual Screening
description: Screen one small molecule against a panel of protein targets using Open Babel ligand preparation, local UniDock-Pro reverse docking, GNINA CNN rescoring of the top 5-10%, DiffDock blind-docking checks for uncertain pockets, Chai-1 validation of a very small final set, and PLIP or the molecular structure viewer for interaction analysis. Use for reverse virtual screening, target fishing, off-target prediction, drug repurposing, polypharmacology, or ranking possible protein targets for a supplied SMILES, SDF, MOL2, PDB, or PDBQT compound.
description_zh: 用 Open Babel、UniDock-Pro、GNINA、DiffDock、Chai-1 等对一个化合物在多个蛋白靶点上做反向虚拟筛选，用于靶点钓鱼、脱靶预测、药物重定位与多药理学分析。
description_en: Screen one small molecule against a panel of protein targets using Open Babel, UniDock-Pro, GNINA CNN rescoring, DiffDock, Chai-1, and PLIP. Use for reverse virtual screening, target fishing, off-target prediction, and drug repurposing.
category: 科研/生物
version: 1.0.0
author: 小猪莹(keyanzhu999)
---

# Reverse Target Virtual Screening

Run a staged target-fishing workflow for one compound against many protein receptors. Keep exactly three top-level output folders: `inputs/`, `screening/`, and `report/`.

## Workflow

1. Prepare the compound with Open Babel and preserve the original input.
2. Run the same compound against every target in the panel with UniDock-Pro.
3. Send the top 5-10% of successful targets to `gnina-dock` for CNN rescoring.
4. Send high-ranked targets with unknown or predicted pockets to `diffdock` for blind-pose checking.
5. Use `chai1-complex` only for a very small final set when its installed mixed-complex input can be represented correctly.
6. Run PLIP on one selected pose per final target and open representative structures with `structure-viewer:structure-viewer`.

Treat every stage as prioritization, not experimental target validation. Do not convert docking scores, CNN scores, DiffDock confidence, or Chai-1 confidence into `Kd`, `IC50`, or a binding probability.

## Preflight

Run the bundled check before a new screen:

```bash
python scripts/check_reverse_vscreen.py --deep
```

Open Babel and UniDock-Pro are required for the primary stage. GNINA, DiffDock credentials, Chai-1, PLIP, and the structure viewer are follow-up capabilities. If an optional stage is unavailable, preserve its queue and mark it blocked; do not discard the completed primary screen.

## Inputs

Require one compound as `SMILES`, SDF, MOL2, PDB, or PDBQT plus a CSV/TSV target manifest. The required manifest fields are:

```text
target_id,receptor,center_x,center_y,center_z,size_x,size_y,size_z
```

Use prepared receptor PDBQT files for production. Add `receptor_pdb`, `pocket_source`, `pocket_confidence`, `reference_ligand`, `calibration_mean`, `calibration_sd`, and `protein_sequence` when available. Read `references/target_manifest.md` before building or changing a target panel.

## Primary Screen

Run from a ligand file:

```bash
python scripts/run_reverse_screen.py \
  --ligand compound.sdf \
  --target-manifest targets.csv \
  --out-dir reverse_screen_run \
  --search-mode fast \
  --gnina-percent 10 \
  --diffdock-count 10 \
  --chai-count 5
```

Or run from SMILES:

```bash
python scripts/run_reverse_screen.py \
  --smiles "CC(=O)Oc1ccccc1C(=O)O" \
  --target-manifest targets.csv \
  --out-dir reverse_screen_run
```

Use `--dry-run` first for a new panel. It prepares the compound, validates all target rows, and writes per-target UniDock command files without running docking.

## Follow-Up Stages

- Read `report/queues/gnina_queue.csv`, then use `gnina-dock` with the same receptor, ligand state, box, CNN model, and reproducible seed. Keep `minimizedAffinity`, `CNNscore`, and `CNNaffinity` separate.
- Read `report/queues/diffdock_queue.csv`, then use `diffdock` only for uncertain pockets. Check its credential status without exposing the key and preserve confidence as pose confidence, not affinity.
- Read `report/queues/chai1_queue.csv`, then use `chai1-complex` only after verifying the installed Chai-1 mixed protein-small-molecule input convention. Do not invent an unsupported FASTA encoding.
- Read `report/queues/interaction_queue.csv`, choose one pose per target, run PLIP on the assembled complex, and use the structure viewer for contacts, clashes, and visual inspection.

Do not silently continue when GNINA or PLIP dependencies are missing. Record the stage as blocked and provide the exact preflight result.

## Ranking Rules

Raw Vina-style scores from different receptors are not automatically comparable. Prefer target-specific calibration using a reference-ligand or matched-decoy distribution. When `calibration_mean` and `calibration_sd` are present, the runner reports a target-specific z-score; otherwise it labels the provisional ranking `uncalibrated_raw_score`.

Prioritize targets using consensus evidence: calibrated UniDock result, plausible GNINA pose, DiffDock agreement for uncertain pockets, pocket quality, absence of severe clashes, recurring key contacts, and biological evidence. Keep tool-specific scores in separate columns rather than hiding them in one unexplained number.

## Outputs

```text
reverse_screen_run/
├── inputs/
│   ├── ligand_original.*
│   ├── ligand.pdbqt
│   ├── target_manifest.csv
│   └── run_config.json
├── screening/
│   └── unidock/<target_id>/
└── report/
    ├── reverse_ranking.csv
    ├── target_failures.csv
    ├── preflight.json
    ├── stage_status.json
    ├── summary.md
    └── queues/
```

Read `references/workflow.md` for queue selection, calibration, and recovery rules. Never overwrite an existing nonempty run directory and never place API keys in the skill, manifest, logs, or report.
