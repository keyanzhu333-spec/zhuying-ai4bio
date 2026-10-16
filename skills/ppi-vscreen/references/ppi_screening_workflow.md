# PPI Screening Workflow Reference

## Recommended Evidence Ladder

Use the cheapest defensible stage first and reserve expensive prediction for a shortlist:

1. sequence and metadata checks;
2. structure availability and PDB quality checks;
3. coarse LightDock blind docking for candidates with prepared PDBs;
4. higher-sampling LightDock reruns for reproducible hits;
5. Chai-1 complex prediction for a small sequence-only or top-hit set;
6. restraint-guided refinement when interface evidence exists;
7. structure inspection, contact analysis, and optional MD.

Chai-1 can be useful when no partner structure exists, but its model confidence and interface metrics are not directly interchangeable with LightDock scores. For a large FASTA library, first reduce the set using domain/sequence criteria or external biological evidence, then use Chai-1 on a bounded shortlist.

## LightDock Case Layout

Each case must contain exactly the intended target and candidate structures under the conventional names:

```text
cases/candidate_001/
├── receptor.pdb
└── ligand.pdb
```

Use the same target structure and the same sampling/scoring settings for all first-pass cases. The helper records source paths in `screen_manifest.tsv` and extracts the best available first score into `screen_summary.tsv`; inspect the full `rank_by_scoring.list` files before making a final selection.

## Ranking Fields

At minimum, retain:

- candidate ID and source structure;
- LightDock top score and number of nonredundant top-pose clusters;
- clashes and interface contact counts;
- representative complex path;
- Chai-1 model confidence and interface consistency, when run;
- restraint satisfaction, when HADDOCK3 is used;
- biological controls and prior evidence.

Prefer candidates supported by several independent poses or clusters and by plausible interface chemistry. A single extreme score with severe clashes or an unstable interface should be down-ranked.

## Rerun Policy

Do not mix smoke-test scores with production scores. Copy the shortlist into a new production directory, repeat the same preparation policy, increase sampling, and record the settings in a manifest. If a target or candidate structure changes, treat it as a new screen.
