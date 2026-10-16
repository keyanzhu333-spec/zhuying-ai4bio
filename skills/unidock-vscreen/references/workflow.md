# UniDock-Pro Virtual Screening Workflow

## Input Requirements

- Receptor: `.pdbqt` is preferred. UniDock-Pro help also accepts `.pdb`, but prepared `.pdbqt` is safer for production screening.
- Ligands: use a directory of `.pdbqt` files or a text ligand index with one ligand path per line.
- Search box: require center x/y/z and size x/y/z in Angstrom.
- Search mode: always set `fast`, `balance`, or `detail`; do not omit it.
- Reference ligand: provide one or more co-crystallized `.pdbqt` poses only when the user wants similarity-guided or hybrid docking.

## Choosing Parameters

- Use `fast` for large first-pass library screening.
- Use `balance` for normal virtual screening when time allows.
- Use `detail` for smaller focused libraries, hit confirmation, or hybrid docking.
- Keep `scoring=vina` unless the user explicitly asks for `vinardo`.
- Record `seed`, `num_modes`, `exhaustiveness`, and `energy_range` when changed from defaults.

## Running

Prefer `scripts/run_unidock_screen.py` because it:

- normalizes ligand paths into `inputs/ligand_index.txt`;
- writes `inputs/run_config.json`;
- keeps raw outputs under `docking/results/`;
- writes logs under `docking/logs/`;
- supports optional batching with `--batch-size`;
- runs post-analysis into `report/`.

For very large libraries, use `--batch-size` to split ligand indexes. Start with a small smoke test before committing GPU time to a full run.

## Interpreting Results

Rank by the best `REMARK VINA RESULT` score in each output PDBQT; more negative is better within the same receptor, box, scoring function, and UniDock settings. Do not compare scores across unrelated receptors or very different search boxes.

Use top hits as prioritization candidates. Recommend follow-up checks such as visual inspection, PLIP interaction analysis, GNINA rescoring, duplicate/PAINS filtering, ADMET filtering, and MD only when scientifically justified.

## Failure Handling

UniDock logs malformed ligands with messages such as structure parsing errors and `Ligand name:`. Preserve these in `report/failed_ligands.csv`. Do not silently remove bad ligands from scientific counts; report total requested ligands, successful output files, failed batches, and parsed failures separately.
