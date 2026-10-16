---
name: ppi-vscreen
description: Run hierarchical virtual screening of candidate protein interaction partners against a target protein using local LightDock structure-based docking, Chai-1 sequence-based complex prediction, optional HADDOCK3 restraint-guided refinement, structure inspection, and downstream MD. Use when the user has one target protein plus a protein library and wants to rank possible protein-protein interaction partners, receptors, binders, or decoys.
metadata:
  short-description: Hierarchical protein-protein interaction screening
---

# Protein-Protein Interaction Virtual Screening

Use this skill to screen a library of candidate proteins against one target protein. It combines sequence-level and structure-level evidence, but it does not claim experimental interaction, cellular specificity, or binding affinity from docking scores alone.

## Tool Selection

- **Candidate PDB library:** use LightDock for a uniform blind protein-protein docking screen.
- **Candidate FASTA library or a small number of sequence-only candidates:** use Chai-1 to predict complex structures for shortlisted pairs. Do not run Chai-1 blindly across a very large library as though it were a cheap docking score.
- **Known interface residues, cross-links, mutagenesis, or other restraints:** use a dedicated protein-protein HADDOCK3 configuration only after verifying that the local workflow supports protein partners. Do not route a protein-protein case to the `haddock3-nucleic-acid` skill, which is reserved for DNA/RNA complexes.
- **Top structural candidates:** inspect with `structure-viewer:structure-viewer`; use `gromacs-md` only for a small number of biologically plausible complexes.

For a purely protein-protein screen, the primary docking engine is LightDock. Chai-1 is complementary structure prediction, not a replacement for a comparable high-throughput docking score.

## Inputs

Required:

- one target protein structure, preferably `target.pdb`; or a target sequence when structure prediction is needed;
- a candidate library, either a directory of protein PDB files or a multi-entry protein FASTA file;
- a candidate manifest when available, with stable IDs, source, species, isoform, chain, and any positive/negative-control labels.

Preferred PDB preparation:

- keep only the intended protein chains;
- preserve chain IDs and residue numbering;
- remove unrelated waters, ligands, and alternate conformations after checking their relevance;
- resolve missing backbone/side-chain atoms before docking when they affect the interface;
- use the same preparation policy for the target and every candidate.

Do not mix monomers, oligomers, truncated domains, and full-length proteins without recording the difference. Deduplicate identical or near-identical candidate sequences before expensive docking.

## Screening Workflow

1. **Define the screen.** Record target identity, candidate IDs, structures/sequences, controls, cutoff rules, and the exact tool parameters. Keep a new output directory for each screen.
2. **Triage inputs.** Validate PDB readability, chain content, residue numbering, sequence length, missing coordinates, and obvious clashes. For sequence-only candidates, separate candidates that require Chai-1 structure prediction from candidates that already have PDBs.
3. **Run a coarse structural screen.** Put the target and every candidate PDB into separate LightDock case directories and use identical low-cost settings. The bundled script prepares these cases and launches the local LightDock batch workflow.
4. **Rank conservatively.** Combine the LightDock score with top-pose recurrence/cluster support, interface size, clashes, buried surface plausibility, electrostatics, and biological metadata. Rank only within runs using the same protocol; do not compare scores from different parameter sets as if they were calibrated affinities.
5. **Rescreen the shortlist.** Re-run the top candidates with larger sampling and, when appropriate, ANM flexibility. Keep the first-pass and production-pass results separate.
6. **Add orthogonal evidence.** For a small sequence-only shortlist, run Chai-1 complex prediction and compare model confidence, interface consistency, and contacts. If experimental interface restraints exist, perform HADDOCK3 refinement only through a verified protein-protein-compatible workflow and record every restraint source.
7. **Inspect and validate.** View representative complexes, check clashes and interface contacts, and reserve MD for a small number of candidates. Produce a ranked table with evidence fields rather than a single unsupported “binder” label.

## Quick PDB-Library Screen

The bundled helper accepts one target PDB, a directory containing candidate PDB files, and a new output directory:

```bash
scripts/run_ppi_vscreen.sh \
  /absolute/path/to/target.pdb \
  /absolute/path/to/candidate_pdbs \
  /absolute/path/to/ppi_screen_run
```

The first pass uses a small, reproducible LightDock setting by default:

```bash
SWARMS=50 GLOWWORMS=50 STEPS=20 TOPN=3 \
scripts/run_ppi_vscreen.sh \
  target.pdb candidate_pdbs ppi_screen_smoke
```

For a production rescreen, use a separate output directory and increase sampling, for example `SWARMS=400 GLOWWORMS=200 STEPS=100 TOPN=10`. Set `ANM_FLAG=--anm` only after the candidate structures and the local LightDock installation have passed the rigid-body smoke test.

## Outputs

Keep outputs organized as:

```text
ppi_screen_run/
├── screen_manifest.tsv
├── screen_summary.tsv
└── cases/
    ├── candidate_001/
    │   ├── receptor.pdb
    │   ├── ligand.pdb
    │   ├── rank_by_scoring.list
    │   └── top_*.pdb
    └── candidate_002/
```

Report the exact parameters, skipped/failed candidates, top LightDock scores, candidate IDs, representative PDB paths, and any Chai-1/HADDOCK3/structure-validation evidence. A high score without a physically plausible interface or reproducibility across poses is not sufficient.

## Scientific Guardrails

- Protein-protein virtual screening is a hypothesis-generation workflow, not proof of interaction.
- Use positive and negative controls when available, and do not tune parameters on the final ranking only.
- Keep biological metadata separate from computational scores.
- Treat score direction and scale as tool-specific; do not convert LightDock or Chai-1 outputs into `Kd`, `IC50`, or probability without a validated calibration set.
- Record whether each candidate was docked from an experimental structure, a predicted structure, a truncated construct, or a multimeric assembly.
- Do not overwrite prior screens and do not store credentials in manifests or output folders.

For detailed ranking and validation guidance, read [references/ppi_screening_workflow.md](references/ppi_screening_workflow.md).
