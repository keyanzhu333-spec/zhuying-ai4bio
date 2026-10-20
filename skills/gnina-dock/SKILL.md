---
name: gnina-dock
display_name: GNINA 分子对接与相互作用分析
display_name_en: GNINA Docking with PyMOL and PLIP
description: Run structure-based molecular docking with GNINA, inspect poses in PyMOL, and generate and interpret PLIP protein-ligand interaction reports. Use when a user asks to dock a prepared receptor/ligand pair, use GNINA CNN rescoring, compare docking poses, visualize a docking complex, or summarize hydrogen bonds, hydrophobic contacts, aromatic interactions, salt bridges, halogen bonds, metal contacts, or water bridges.
description_zh: 用 GNINA 做基于结构的分子对接，用 PyMOL 可视化位姿，用 PLIP 生成并解读蛋白-配体相互作用报告。适用于受体/配体对接、CNN 重打分、位姿比较与氢键/疏水/盐桥等相互作用总结。
description_en: Run structure-based molecular docking with GNINA, inspect poses in PyMOL, and generate and interpret PLIP protein-ligand interaction reports. Use for receptor/ligand docking, CNN rescoring, pose comparison, and summarizing hydrogen bonds, hydrophobic contacts, salt bridges, and more.
category: 科研/生物
version: 1.0.0
author: 小猪莹(keyanzhu999)
---

# GNINA-PyMOL-PLIP Docking

## Overview

Use GNINA for reproducible docking and CNN-based pose rescoring, then connect the selected pose to PyMOL visualization and PLIP interaction analysis. Keep the three signals separate:

- `minimizedAffinity`: GNINA's empirical affinity-like score; more negative is better within the same setup.
- `CNNscore`: pose plausibility/confidence, approximately 0-1; it is not a binding affinity.
- `CNNaffinity`: GNINA CNN-predicted affinity-like score; higher is better, but it is not an experimental measurement.

Do not call a single high-scoring pose validated. Report the input state, search box, seed, GNINA settings, pose-selection rule, and chemical caveats.

## Self-installation and tool checks

At the start of a docking task, locate the required executables and Python modules. If the local runtime is incomplete, run:

```text
python scripts/install_gnina_runtime.py
```

Use `--check` for a read-only check of the active Python environment and GNINA
executable. Installation creates the isolated Linux/WSL Conda environment
`zy-gnina` using `assets/environment.yml`; activate it before invoking this skill.

GNINA's official prebuilt release is a Linux executable usable in WSL.
Obtain a platform-compatible binary from the official releases and pass
`--gnina-bin` or set `GNINA_BIN`. The analysis installer does not install the
GNINA engine or CUDA driver. Native Windows users should run installation in WSL2.
Docker remains an optional pipeline backend when the user already has a working
Docker runtime and the selected image.

### Remote Linux deployment

This skill can run on a remote Linux/SSH server without copying the bundled
Windows runtime. Install or provide native Linux executables for GNINA,
PyMOL, and PLIP, then pass them explicitly:

```text
python scripts/run_gnina_pipeline.py \\
  --receptor receptor.pdb --ligand ligand.sdf \\
  --center 12.4 -3.1 8.7 --size 20 20 20 \\
  --out-dir docking \\
  --gnina-bin /opt/gnina/gnina \\
  --pymol-bin pymol --plip-bin plip \\
  --run-pymol --run-plip
```

The wrapper uses the supplied system PyMOL for the PLIP local-pocket image
when `--pymol-bin` is set. The Windows GUI is not part of this remote skill
package; copy result files back to the local machine for interactive viewing.

Before running, record the exact executable or backend used for each stage:

- GNINA native executable, WSL executable, or Docker image;
- PyMOL headless runner;
- PLIP runner;
- Open Babel only for optional format conversion or fallback validation;
- RDKit for SDF score extraction and ranking.

Require or obtain:

- receptor structure, preferably PDB;
- ligand structure as SDF, MOL2, PDB, or PDBQT; GNINA can read PDB/SDF directly, so PDBQT conversion is not mandatory;
- a binding-site definition: a co-crystal/reference ligand, known pocket residues, or explicit box center and size;
- receptor PDB or a ready complex PDB for PyMOL/PLIP analysis.

The user must provide or confirm biological decisions that software cannot infer safely: receptor/ligand identity, chain selection, protonation and tautomer state, retained waters/cofactors/metals, and the binding-site definition. A structure image alone is not a sufficient docking input.

Read [analysis_guide.md](references/analysis_guide.md) before interpreting results.

For Windows/WSL2 environment setup, GNINA/PyMOL/PLIP installation pitfalls, and rendering conventions that match the `diffdock` skill, read [install_lessons_learned.md](references/install_lessons_learned.md).

## Standard workflow

### 1. Prepare and validate structures

Inspect chain IDs, alternate locations, residue names, formal charges, protonation, bond orders, and steric clashes. Remove crystallographic waters only when they are not part of the binding mechanism; retain catalytic or structural waters when justified. Keep cofactors and metals that belong to the site. Ensure the ligand has a chemically sensible 3D geometry and a consistent protonation/tautomer state.

Keep the original files unchanged and write any prepared structures to a separate directory. Use Meeko/Open Babel/RDKit only when preparation, validation, or a downstream format conversion requires them; do not convert to PDBQT merely because a legacy Vina workflow did so.

### 2. Define the GNINA search box

Prefer a reference ligand when one is available:

```text
--autobox_ligand crystal_ligand.sdf --autobox_add 4
```

The alternative is an explicit box:

```text
--center 12.4 -3.1 8.7 --size 20 20 20
```

Record the source and dimensions in the manifest. A blind-docking box is exploratory and must be labelled as such.

### 3. Run GNINA

For a typical single-ligand or SDF-library run:

```text
python scripts/run_gnina_pipeline.py \
  --receptor receptor.pdb \
  --ligand ligands.sdf \
  --autobox-ligand crystal_ligand.sdf \
  --out-dir docking \
  --cnn-scoring rescore \
  --cnn crossdock_default2018 \
  --exhaustiveness 16 \
  --num-modes 10 \
  --seed 42 \
  --run-pymol --run-plip
```

`rescore` is the normal default: empirical docking generates poses and the CNN rescoring stage ranks them. Use `refinement` or `all` only when the slower CNN-guided search is justified. For screening, start with exhaustiveness 8-16; for a smaller high-accuracy set, test 32-64. Use 5-20 modes and always record a seed.

If the box is explicit, replace `--autobox-ligand` with `--center X Y Z --size SX SY SZ`. The wrapper writes `docked.sdf`, `gnina.log`, `ranking.csv`, `ranking.json`, and `manifest.json`.

If an older WSL binary aborts with a CUDA `invalid device function` error, add `--no-gpu` to run a CPU validation job. Use a newer GNINA release or a compatible Docker/NVIDIA runtime for GPU production runs.

For Windows when GNINA is running through Docker, add for example:

```text
--docker-image gnina/gnina:latest
```

The wrapper mounts the input/output directories and preserves the same output layout. Prefer an already pulled, version-pinned image for reproducibility.

### 4. Rank and select poses

For each ligand, deduplicate poses before ranking. The bundled wrapper records the GNINA properties and applies this default selection aid:

1. flag poses with `CNNscore > 0.5` as plausible;
2. rank plausible poses by descending `CNNaffinity`;
3. retain `minimizedAffinity` as a separate empirical score;
4. calculate ligand efficiency as `LE = -minimizedAffinity / heavy_atoms` when heavy-atom count is available.

Do not mix scores from different GNINA CNN models or different preparation states without saying so. Compare pose families by ligand RMSD, recurring interactions, pocket complementarity, clashes, and chemical plausibility.

### 5. Build a PyMOL-ready complex

Use PyMOL to combine the receptor PDB and one selected GNINA SDF pose. The wrapper loads the SDF directly; Open Babel is only a fallback when the selected PyMOL build cannot read the SDF reliably.

Example headless PyMOL script:

```text
load receptor.pdb, receptor
load docking/docked.sdf, ligand_poses
create complex_pose1, receptor or ligand_poses, 1, 1
show cartoon, receptor
show sticks, ligand_poses
color cyan, receptor
color yellow, ligand_poses
save docking/complex_pose1.pdb, complex_pose1
save docking/complex_pose1.pse
png docking/complex_pose1.png, width=1800, height=1400, dpi=240, ray=1
quit
```

Use a stable object/state selection and confirm that the selected ligand is the intended molecule and pose. If the receptor is supplied as PDBQT, also supply `--receptor-pdb` for visualization and PLIP.

### 6. Run PLIP and inspect interactions

Run PLIP on one selected complex, not on a receptor alone and not on all poses merged together:

```text
plip -f docking/complex_pose1.pdb -o docking/plip_pose1 --txt --xml
```

Make a compact table with interaction type, receptor residue/chain, ligand atom(s), distance/angle when reported, and pose/state. Review the PyMOL image and apply chemical judgment. Flag contacts that depend on questionable protonation, a buried unsatisfied polar atom, an unrealistic geometry, a metal coordination assumption, or an omitted water/ligand.

### 7. Validate before making a claim

When a co-crystal ligand exists, perform redocking with the same box and compute pose RMSD. A practical guide is top-1 RMSD <= 2.0 A as a pass, 2-3 A as borderline, and >3 A as a failure signal. Failure triggers inspection of the pocket definition, receptor preparation, cofactors/metals/waters, ligand protonation/tautomer, and GNINA settings; it is not evidence that a new ligand is inactive.

For higher-confidence projects, cross-check physical validity with PoseBusters and interaction consistency with PLIP or ProLIF. Compare with another docking/scoring method when the decision is consequential.

## Deliverables and reporting

Return links or paths to:

- `gnina.log`, complete `docked.sdf`, and the exact command/backend;
- `ranking.csv` or `ranking.json` with GNINA scores and selection flags;
- selected pose PDB, PyMOL session, and overall PNG;
- a separate PLIP local-pocket PNG and PyMOL session showing the ligand, nearby pocket residues, and short contacts;
- PLIP TXT/XML output and a concise interaction table;
- a reproducibility block listing executable versions, input files/checksums when available, box source, CNN model/scoring mode, exhaustiveness, number of modes, seed, and preparation decisions.

Do not invent missing scores, residue names, distances, or interactions. If installation or a backend fails, stop at the last valid stage and state the exact missing dependency, network/permission issue, WSL/Docker requirement, or license requirement.

## Bundled resources

- `scripts/run_gnina_pipeline.py`: wrapper for GNINA, SDF score extraction/ranking, PyMOL assembly, and PLIP execution.
- `scripts/run_pymol.py` and `scripts/run_plip.py`: launchers for the bundled Windows wheels.
- `scripts/install_gnina_runtime.py`: idempotent local installer/checker for GNINA plus the open-source PyMOL/PLIP analysis runtime.
- `references/analysis_guide.md`: ZYDock-inspired quality gates, GNINA score semantics, pose comparison, and interaction-analysis cautions.
