# HADDOCK3 Workflow Notes

## Configuration Pattern

HADDOCK3 uses a TOML-like workflow configuration. Keep inputs and outputs in a case-specific directory:

```text
case/
├── inputs/
│   ├── protein.pdb
│   ├── dna.pdb
│   └── ambig.tbl
├── run.cfg
└── haddock3_protein_dna_run/
```

The top-level `run_dir` controls the result directory and `molecules` lists the input PDB files. A typical sequence is topology preparation, rigid-body sampling, flexible refinement, and final analysis. The exact available module parameters must be checked with the installed HADDOCK3 documentation or `haddock3 --help` before adding advanced options.

## Restraints

Use restraints when the user has biochemical or structural evidence about the interface. Ambiguous restraints can describe alternative contacts; unambiguous restraints can enforce a specific contact. Treat predicted contacts as hypotheses and label them separately from experimentally supported restraints.

For a no-restraint baseline, use a HADDOCK-supported center-of-mass or surface restraint option in the rigid-body stage when appropriate. Do not invent residue restraints merely to force a desired pose.

## Nucleic-Acid Checks

- DNA and RNA need compatible topology and standard residue naming.
- Preserve chain IDs and residue numbering referenced by restraint tables.
- Check protonation, termini, modified bases, metal ions, and bound cofactors explicitly.
- Compare multiple clusters, not only the top-scoring model.
- Use a structure viewer or PLIP-like contact analysis after docking to inspect the interface.
