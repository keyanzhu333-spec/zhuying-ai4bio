# Reverse Screening Workflow

## Stage Gates

1. **Open Babel:** preserve the original ligand and prepare one traceable PDBQT state. Record whether protonation was supplied by the user or altered during conversion.
2. **UniDock-Pro:** use one ligand state, one scoring function, and documented search settings across the panel. Run a dry test before production.
3. **GNINA:** rescore the best 5-10% of successful targets. Use identical CNN settings and keep empirical and CNN values separate.
4. **DiffDock:** process only high-ranked targets with predicted, unknown, or disputed pockets. Use it as blind-pose evidence, not affinity evidence.
5. **Chai-1:** restrict to approximately 3-5 final targets. Verify the installed mixed-entity input format and GPU capacity before launching.
6. **PLIP/viewer:** analyze one selected complex per final target. Check protonation, clashes, metals, waters, and residue geometry.

## Recovery

Keep completed stages immutable. A missing optional dependency should leave a queue plus `blocked` status so the run can resume after installation. Do not rerun UniDock merely because GNINA, DiffDock, Chai-1, PLIP, or rendering is unavailable.

## Cross-Target Ranking

Raw docking energies are biased by receptor size, pocket composition, box definition, and preparation. Prefer one of these, in descending order:

1. target-specific score z-scores from matched reference/decoy distributions;
2. percentile ranks from target-specific background screens;
3. consensus with a known reference ligand and successful redocking;
4. uncalibrated raw ranking, clearly labeled exploratory.

Never merge UniDock, GNINA, DiffDock, and Chai-1 outputs into a single weighted score unless the weights were validated on a relevant benchmark. Present a multi-column evidence table instead.

## Queue Semantics

- `gnina_queue.csv`: provisional top fraction of successful UniDock targets.
- `diffdock_queue.csv`: top targets whose pocket source/confidence indicates uncertainty.
- `chai1_queue.csv`: very small provisional final set for orthogonal structure prediction.
- `interaction_queue.csv`: representative poses for PLIP and structure inspection.

Queues are worklists, not claims that the target binds the compound.
