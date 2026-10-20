---
name: gromacs-md
display_name: GROMACS 多场景分子动力学
display_name_en: GROMACS Multi-Scenario Molecular Dynamics
description: Prepare, run, troubleshoot, analyze, and plot GROMACS molecular dynamics for single proteins, protein-protein complexes, protein-DNA/RNA complexes, protein-small-molecule complexes, and protein-metal systems. Use when Codex needs to choose a scientifically appropriate MD setup, generate ligand or metal-aware parameters, run minimization/equilibration/production, analyze trajectories, make publication-ready plots, or perform carefully validated MM/PBSA calculations.
description_zh: 为单蛋白、蛋白-蛋白、蛋白-核酸、蛋白-小分子、蛋白-金属等体系准备、运行、排错、分析并绘制 GROMACS 分子动力学，含配体/金属参数化、轨迹分析与发表级绘图，及经过验证的 MM/PBSA 计算。
description_en: Prepare, run, troubleshoot, analyze, and plot GROMACS molecular dynamics for single proteins and protein-protein, protein-nucleic-acid, protein-small-molecule, and protein-metal systems, including trajectory analysis, publication-ready plots, and validated MM/PBSA.
category: 科研/生物
version: 1.0.0
author: 小猪莹(keyanzhu999)
---

# GROMACS Multi-Scenario MD

Use one skill with five scenario branches. Keep each project under exactly three top-level directories:

```text
<project>/
├── inputs/
├── simulation/
└── analysis/
```

Do not launch a long production run unless the user explicitly asks. Prefer preparation, topology validation, minimization, and a short restrained or unrestrained test before consuming substantial compute time.

## Select The Scenario

Classify the system before choosing commands or force fields:

| Scenario | Trigger | Main special handling |
|---|---|---|
| `single-protein` | One protein or oligomer studied without another biomolecular partner | Missing residues, termini, protonation, disulfides, oligomeric state |
| `protein-protein` | Two or more interacting protein partners | Preserve chain identity; build partner and interface groups |
| `protein-nucleic-acid` | Protein-DNA or protein-RNA complex | Use a compatible protein/nucleic-acid force-field family; preserve meaningful ions |
| `protein-small-molecule` | Protein plus organic ligand, drug, substrate, or inhibitor | Parameterize ligand charge and bonded terms with a validated, force-field-compatible workflow |
| `protein-metal` | Protein coordinated to a metal ion or metal cofactor | Establish oxidation state, coordination model, geometry, charge, and spin before topology generation |

Read `references/scenario-workflows.md` for the scenario-specific setup, validation, and analysis requirements. Do not force a system into the protein-ligand template merely because non-protein atoms are written as `HETATM`.

## Initialize A Case

Create the three-directory layout and scenario manifest:

```bash
python3 scripts/init_md_case.py \
  --scenario protein-protein \
  --input complex.pdb \
  --out-dir <project>
```

The initializer also renders reviewed starting-point MDP files for minimization,
NVT, NPT, and production under `simulation/mdp/`. Temperature, pressure,
durations, and random seed are explicit command-line parameters. These files are
not universal force-field recommendations: inspect them against the selected
force field, membrane/solvent model, restraints, and scientific question.

Check the local runtime independently of any project:

```bash
python3 scripts/check_gromacs.py --json gromacs-environment.json
```

Before execution, place a validated `topol.top` and `system.gro` in
`simulation/system/`; add `index.ndx` when named custom groups are required.
The skill does not pretend that arbitrary ligands, metals, or nucleic acids can
be parameterized by one generic command.

## Preflight

1. Confirm biological assembly, chains, residue names, alternate conformations, missing atoms/residues, termini, disulfides, protonation, cofactors, ions, crystallographic waters, and nonstandard residues.
2. Record the intended force field, water model, ionic strength, temperature, pressure, box type, padding, timestep, restraints, equilibration schedule, production duration, and replicate count before production.
3. Keep protein, nucleic acid, ligand, metal, and solvent parameters mutually compatible. Do not combine force fields based only on matching file formats.
4. Generate selections by names and expressions where possible. Inspect `index.ndx`; never trust numeric group IDs copied from another system.
5. Review every `gmx grompp` warning. Resolve the cause instead of adding `-maxwarn` by habit.
6. Check total charge, atom count, molecule count, bonded connectivity, coordinate/topology ordering, and periodic box before minimization.

## Common Simulation Stages

Use the same gated progression for all scenarios:

1. **Preparation:** clean a copy of the structure and preserve provenance of the original input.
2. **Topology:** generate standard biomolecule topology, then add validated parameters for ligands, metals, and other nonstandard groups.
3. **System construction:** define the box, solvate, add ions, and create named analysis groups.
4. **Energy minimization:** inspect convergence, maximum force, geometry, clashes, and restrained special sites.
5. **NVT/NPT equilibration:** inspect temperature, pressure, density, box stability, restraint behavior, and any metal/interface geometry.
6. **Production:** run only after the short validation is clean; prefer multiple independent replicas over one unsupported narrative from a single trajectory.
7. **Trajectory processing:** remove PBC artifacts, make molecules whole, center consistently, and fit using a stated selection before analysis.
8. **Analysis and plotting:** calculate common and scenario-specific metrics, assess convergence, and retain commands, selections, frame ranges, and units.

## Execute Validated Stages

Dry-run the exact commands first:

```bash
python3 scripts/run_md_stages.py \
  --project <project> \
  --from-stage em \
  --dry-run
```

Run one stage at a time and review its energies and geometry before advancing:

```bash
python3 scripts/run_md_stages.py --project <project> --from-stage em
python3 scripts/run_md_stages.py --project <project> --from-stage nvt
python3 scripts/run_md_stages.py --project <project> --from-stage npt
```

Production is gated and requires explicit approval:

```bash
python3 scripts/run_md_stages.py \
  --project <project> \
  --from-stage production \
  --approve-production
```

The default accelerator is CPU for portability. Use `--accelerator gpu` only
after `check_gromacs.py` and a short test confirm a compatible GROMACS/CUDA
runtime. Override the executable with `--gmx` or `GMX_BIN`. The runner does not
add `-maxwarn`; a nonzero allowance must be supplied explicitly and justified.
`simulation/run_config.json` paths are resolved relative to the project.
Existing stage outputs are preserved. To resume one interrupted stage use
`--from-stage STAGE --resume`; production also requires `--approve-production`.
Continuation reuses the existing TPR and checkpoint and verifies local input
checksums. A successful command is not an equilibration or convergence verdict.
For an external MPI GROMACS build use `--external-mpi`; multi-node launch is
managed by the site's scheduler.

The provided cutoff/dispersion settings are an AMBER-style aqueous starting
point, not a preset for CHARMM force switching, membranes, nonaqueous solvents,
or every metal model. Edit the MDPs for the selected force field. The templates
require GROMACS with C-rescale support and POSRES-enabled topology includes.

## Analysis And Plotting

At minimum assess simulation health plus structural stability. Add scenario-specific metrics from `references/analysis-and-plotting.md`.

Generate consistent PNG/PDF plots from GROMACS XVG files:

```bash
python3 scripts/plot_md_metrics.py \
  --scenario protein-nucleic-acid \
  --input-dir <project>/analysis/xvg \
  --out-dir <project>/analysis/figures \
  --formats png,pdf
```

The plotting tool recursively discovers XVG files, honors embedded titles and axis labels, and writes `plot_index.csv`. Validate specialized PCA/FEL or MM/PBSA analyses separately before reporting them.

## Reporting Requirements

Report enough detail for another researcher to reproduce and judge the run:

- Input structure identity and all structural edits
- Scenario, force field, water model, special parameter sources, and software versions
- Box, ions, thermodynamic settings, restraints, timestep, stage durations, replicas, and random seeds
- PBC treatment, fitting group, analysis selections, frame interval, and units
- Equilibration evidence, convergence limitations, failed checks, and excluded frames
- Scenario-specific interaction or coordination metrics, with uncertainty or replicate variation when available

Do not describe docking score, one RMSD trace, one MM/PBSA number, or a short trajectory as proof of biological binding or mechanism.
