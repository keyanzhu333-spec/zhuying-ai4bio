# LightDock Workflow Reference

## Environment

Activate the local environment with:

```bash
conda activate lightdock
```

For non-interactive execution, prefer:

```bash
conda run -n lightdock <command>
```

## Per-Case Commands

Run from a directory containing `receptor.pdb` and `ligand.pdb`:

- Protein-protein: receptor and ligand are protein PDB structures.
- Protein-DNA: receptor is the protein PDB and ligand is a DNA PDB.
- Protein-RNA: receptor is the protein PDB and ligand is an RNA PDB.

For DNA/RNA, begin with rigid-body docking (`ANM_FLAG=""`) and a small smoke test. Enable ANM only after confirming that the installed LightDock version handles the nucleic-acid representation correctly.

```bash
lightdock3_setup.py receptor.pdb ligand.pdb \
  -s "$SWARMS" -g "$GLOWWORMS" \
  $ANM_FLAG \
  --noxt --noh --now

lightdock3.py setup.json "$STEPS" \
  -s "$SCORING" -c "$CORES"

for sw in swarm_*; do
  lgd_generate_conformations.py receptor.pdb ligand.pdb \
    "$sw/gso_${STEPS}.out" "$GLOWWORMS" >/dev/null 2>&1 || true
  lgd_cluster_bsas.py "$sw/gso_${STEPS}.out" >/dev/null 2>&1 || true
done

lgd_rank.py "$SWARMS" "$STEPS"
lgd_top.py receptor.pdb ligand.pdb rank_by_scoring.list "$TOPN"
```

## Parameter Guidance

- Full-size proteins: `SWARMS=400 GLOWWORMS=200 STEPS=100`
- Faster exploratory run: `SWARMS=100 GLOWWORMS=100 STEPS=50`
- Smoke test: `SWARMS=50 GLOWWORMS=50 STEPS=20 TOPN=3`
- Use `CORES=$(nproc)` unless the user wants to leave CPUs free.

## Troubleshooting

- If `lightdock3_setup.py` is not found, check that `conda run -n lightdock which lightdock3_setup.py` succeeds.
- If ranking fails, check whether each `swarm_*/gso_${STEPS}.out` exists.
- If generated complexes look wrong, confirm receptor/ligand chain contents, DNA/RNA residue names, backbone/base atom completeness, and whether the PDBs include only the intended partners.
- If a rerun is requested in an existing case directory, move old `swarm_*`, rank files, and `top_*.pdb` into a timestamped backup unless the user explicitly asks to overwrite.
