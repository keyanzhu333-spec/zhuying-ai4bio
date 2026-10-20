---
name: chai1-complex
description: Run local Chai-1 complex structure prediction for protein-DNA, protein-RNA, protein-protein, and mixed biomolecular complexes from FASTA or sequence inputs. Use when the user asks for Chai-1, sequence-based nucleic-acid complex prediction, multimer structure modeling, or a complementary structural hypothesis before docking or molecular dynamics.
metadata:
  short-description: Local Chai-1 biomolecular complex prediction
---

# Chai-1 Complex Prediction

Use this skill for local sequence-based complex structure prediction with Chai-1. Chai-1 supports proteins, DNA, RNA, and small molecules; this skill focuses on protein-DNA and protein-RNA complexes, with protein-protein or mixed complexes handled when requested. Detect and report the version on the current machine instead of assuming the developer's version.

Chai-1 predicts candidate structures from sequence and model features. It is not a conventional docking engine and does not by itself provide an experimentally validated binding affinity or a UniDock/GNINA-style docking score.

## Inputs

Prepare a multi-entity FASTA file. Use standard sequence alphabets:

```fasta
>protein|protein_A
MSEQUENCE...
>dna|dna_B
ACGTACGT...
>rna|rna_C
AUGCAUGC...
```

Use protein one-letter amino-acid codes, DNA `A/C/G/T`, and RNA `A/C/G/U`. A sequence containing only `A/C/G` can be ambiguous between DNA and RNA; resolve the entity type using the installed Chai parser or an explicit input convention before a production run. Keep each physical chain as its own FASTA entity and use stable names.

## Quick Run

Use the portable runner, which resolves `CHAI1_BIN`, the active `PATH`, or a
named Conda environment and records the command:

```bash
python3 scripts/run_chai1.py \
  --input /absolute/path/to/complex.fasta \
  --out-dir /absolute/path/to/chai1_output \
  --device cuda \
  --num-diffn-samples 5
```

Use `--dry-run` before expensive inference. Additional options supported by the
installed Chai-1 CLI can be appended after `--` in the runner command.
The log is written beside the output directory because Chai-1 requires an empty
output directory at startup.

The equivalent direct command is:

```bash
conda run -n chai1 chai-lab fold \
  /absolute/path/to/complex.fasta \
  /absolute/path/to/chai1_output
```

For a GPU run with extra sampling, use options supported by the local CLI, for example:

```bash
conda run -n chai1 chai-lab fold \
  /absolute/path/to/complex.fasta \
  /absolute/path/to/chai1_output \
  --device cuda \
  --num-diffn-samples 5
```

Check the installed option set with:

```bash
conda run -n chai1 chai-lab fold --help
```

Do not overwrite an existing output directory. Chai-1 may write CIF/PDB structures, scores, and intermediate artifacts; inspect the output directory and report the best available model paths rather than assuming a fixed filename.

## Workflow And Interpretation

1. Validate that each sequence is the intended entity and that DNA/RNA alphabets are unambiguous.
2. Run a small test first to confirm the environment, GPU visibility, and output format.
3. Run production sampling into a new case-specific directory.
4. Inspect generated structures in `structure-viewer:structure-viewer` and evaluate protein-nucleic-acid contacts, chain orientation, clashes, and model confidence.
5. If the user needs restrained docking, explicit interface sampling, or a docking score, continue with `haddock3-nucleic-acid` or `lightdock` using prepared PDB structures.

Chai-1 confidence and model ranking should be reported as prediction evidence, not as proof of binding. For nucleic-acid complexes, check base-specific contacts, backbone contacts, electrostatics, steric clashes, and consistency across sampled models.

## Troubleshooting

- Use `conda run -n chai1 chai-lab --help` to verify the executable and local installation.
- GPU memory can limit complex length and sampling count; reduce sampling or model size for a smoke test.
- If a sequence is classified incorrectly, make its DNA/RNA identity explicit according to the installed parser and rerun.
- Keep FASTA, logs, model outputs, and reports together in a case-specific directory, and never store API keys in the input or output files.
