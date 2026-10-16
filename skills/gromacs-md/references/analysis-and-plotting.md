# Analysis And Plotting

## Prepare The Trajectory First

1. Make molecules whole and remove periodic-boundary jumps.
2. Center on a stable reference group.
3. Fit rotation and translation using a documented group appropriate to the question.
4. Use the same processed trajectory, fitting convention, time window, and units when comparing replicas or systems.

Avoid interpreting raw trajectories that place interacting partners on opposite sides of the periodic box.

## Simulation Health

Plot these before structural conclusions:

| Metric | Stage | Main check |
|---|---|---|
| Potential energy and maximum force | Minimization | Convergence and absence of severe clashes |
| Temperature | NVT/NPT/production | Stable around the target without unexplained drift |
| Pressure | NPT/production | Broad fluctuations are expected; examine the running behavior |
| Density and box dimensions | NPT/production | Stable bulk density and box |
| Total energy or conserved quantity | Appropriate ensemble | Integration or setup problems |

## Common Structural Metrics

- RMSD: state fit group, measured group, reference frame, and whether equilibrium was reached.
- RMSF: map values to residues/nucleotides and distinguish flexible termini from core instability.
- Radius of gyration: use for compactness, not as a direct binding metric.
- SASA: state whether total, polar/nonpolar, interface, or buried area was measured.
- Hydrogen bonds and contacts: report geometric definitions and occupancy cutoffs.
- PCA/FEL: state atom selection, frame window, temperature, binning, and whether replicas agree.
- Secondary structure: report the DSSP implementation/version and map changes to sequence.

## Scenario Plot Sets

| Scenario | Required core plots | Useful additions |
|---|---|---|
| Single protein | RMSD, RMSF, Rg, SASA, secondary structure | Domain distances, PCA/FEL, intraprotein H-bonds |
| Protein-protein | Complex and partner RMSD, interface contacts, inter-chain H-bonds, partner distance | Buried SASA, salt bridges, contact map, comparative MM/PBSA |
| Protein-nucleic acid | Protein and nucleic-acid RMSD, interface contacts/H-bonds, minimum distance | Base-pair/helical metrics, nucleotide contact map, ion bridges |
| Protein-small molecule | Protein RMSD, fitted ligand RMSD, ligand-pocket distance, H-bonds/contacts | Pocket water, key residue distances, MM/PBSA and decomposition |
| Protein-metal | Protein RMSD, all metal-donor distances, coordination number | Coordination angles, geometry deviation, water exchange |

## Generic XVG Plotter

Run:

```bash
python3 ../scripts/plot_md_metrics.py \
  --scenario protein-small-molecule \
  --input-dir analysis/xvg \
  --out-dir analysis/figures \
  --formats png,pdf
```

The script:

- ignores XVG metadata/comment lines while retaining title and axis labels;
- plots every numeric Y series against the first column;
- writes one or more figures per input file;
- creates `plot_index.csv` with source path, points, series count, scenario, and output paths;
- never changes the source XVG files.

For specialized FEL or MM/PBSA analyses, document the independent toolchain, input selections, and convergence checks used for the case.

## Scientific Presentation

- Show units on every axis and define all selections in the caption or report.
- Prefer replicate traces, distributions, block averages, and confidence intervals over an isolated smooth curve.
- Preserve the unsmoothed data. If smoothing is shown, state the window and plot or retain the raw trace.
- Use consistent colors, axis ranges, and time windows for direct comparisons.
- Mark discarded equilibration frames and avoid selecting the analysis window after seeing a preferred result.
- Export vector PDF for publication and high-resolution PNG for rapid review.

## Minimum Interpretation Standard

Do not call a trajectory stable based on RMSD alone. Combine simulation-health checks, at least two structural metrics, the scenario-specific interaction or coordination metrics, and evidence that conclusions are not dominated by initial equilibration or one replicate.
