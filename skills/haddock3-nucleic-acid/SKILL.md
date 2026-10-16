---
name: haddock3-nucleic-acid
description: Run local HADDOCK3 restraint-guided docking and refinement for protein-DNA or protein-RNA complexes from PDB inputs, with optional ambiguous or unambiguous restraint tables, built-in DNA/RNA topologies, reproducible run directories, and result summaries. Use when the user asks for HADDOCK3, restrained protein-nucleic-acid docking, protein-DNA/RNA interface modeling, or refinement of a nucleic-acid complex.
metadata:
  short-description: Local HADDOCK3 protein-DNA/RNA docking
---

# HADDOCK3 Protein-Nucleic-Acid Docking

Use this skill for local HADDOCK3 runs involving one protein and one DNA or RNA partner. The installed environment is `haddock3`, version `2026.7.0`. HADDOCK3 is especially appropriate when the user has interface information, residue restraints, experimental contacts, mutagenesis evidence, or wants explicit refinement after rigid-body sampling.

HADDOCK3 produces ranked structural models and cluster statistics. Scores are computational model-selection signals, not experimental binding affinities.

## Choose The Workflow

- Use `haddock3-nucleic-acid` when PDB structures are available and restraints or HADDOCK-style refinement are desired.
- Use `lightdock` for a fast, blind, rigid-body search when no restraints are available and both partners are already in PDB format.
- Use `chai1-complex` when only sequences are available or a sequence-based complex structure hypothesis is wanted.

## Inputs

Required:

- `protein.pdb`: the protein partner.
- `dna.pdb` or `rna.pdb`: the nucleic-acid partner.

Optional:

- `ambig.tbl`: ambiguous interaction restraints.
- `unambig.tbl`: unambiguous interaction restraints.
- `reference.pdb`: a known or reference complex for CAPRI-style comparison when available.

Keep protein chain IDs and canonical nucleic-acid residue names intact. DNA commonly uses `DA`, `DT`, `DG`, `DC`; RNA commonly uses `A`, `U`, `G`, `C`. Preserve backbone and base atoms that belong to the modeled interface. Remove unrelated waters or alternate conformations only after checking that they are not part of the intended model.

Before running, inspect the PDBs for missing coordinates, duplicate atoms, malformed chain records, and unintended extra chains. Do not silently convert DNA/RNA records into amino-acid records.

## Minimal Run

Create a separate run directory and a HADDOCK3 configuration file. A minimal protein-DNA example is:

```toml
run_dir = "haddock3_protein_dna_run"
molecules = ["inputs/protein.pdb", "inputs/dna.pdb"]

[topoaa]
autohis = true

[rigidbody]
sampling = 1000
cmrest = true
```

For protein-RNA, replace `inputs/dna.pdb` with `inputs/rna.pdb`. For a restrained run, add the restraint-file parameters supported by the installed HADDOCK3 version and verify the referenced `.tbl` files before launching. The detailed configuration notes are in `references/haddock3_workflow.md`.

Run with the installed environment:

```bash
conda run -n haddock3 haddock3 /absolute/path/to/run.cfg
```

For a setup-only validation before a long run:

```bash
conda run -n haddock3 haddock3 --setup /absolute/path/to/run.cfg
```

Never overwrite an existing run directory without explicit permission. Use a new output directory for each parameter set or restraint version.

## Result Handling

Inspect the generated stage directories, including `0_topoaa`, `1_rigidbody`, refinement stages, and the final analysis directory. Summarize:

- run configuration and input paths;
- number of models and clusters;
- top cluster/model scores;
- restraint violations or warnings;
- paths to representative PDB files and analysis tables.

For protein-DNA/RNA models, separately inspect base contacts, phosphate/backbone contacts, electrostatic complementarity, chain orientation, and whether the restraints are satisfied. Do not call a model biologically validated from HADDOCK score alone.

## Validation And Troubleshooting

- Confirm the command with `conda run -n haddock3 haddock3 --help` and record the local version.
- Start with a small rigid-body sampling value to validate topology and restraints, then increase sampling for the production run.
- If a nucleic-acid topology or residue is rejected, inspect the local HADDOCK3 DNA/RNA topology files and correct residue naming rather than deleting atoms.
- If `ambig.tbl` or `unambig.tbl` is supplied, validate chain IDs, residue numbers, atom names, and distance syntax before starting production sampling.
- Keep a machine-readable run log and do not place credentials in the configuration or output directory.
