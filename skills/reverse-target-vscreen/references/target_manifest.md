# Target Manifest Schema

Use one row per receptor and one unique `target_id`. Resolve relative file paths from the manifest directory.

## Required Columns

| Column | Meaning |
|---|---|
| `target_id` | Stable filesystem-safe target identifier. |
| `receptor` | Prepared receptor PDBQT or PDB path. |
| `center_x`, `center_y`, `center_z` | Docking-box center in Angstrom. |
| `size_x`, `size_y`, `size_z` | Positive docking-box dimensions in Angstrom. |

## Optional Columns

| Column | Meaning |
|---|---|
| `receptor_pdb` | PDB used for GNINA visualization, PLIP, or the structure viewer. |
| `pocket_source` | `cocrystal`, `curated`, `transferred`, `predicted`, `unknown`, or another documented source. |
| `pocket_confidence` | Recommended `A`, `B`, `C`, or `D`; A is a validated co-crystal pocket and D is predicted/unknown. |
| `reference_ligand` | Prepared PDBQT reference ligand for UniDock guidance or redocking. |
| `calibration_mean` | Mean score from a target-specific reference/decoy distribution using the same setup. |
| `calibration_sd` | Positive standard deviation for that distribution. |
| `protein_sequence` | Optional amino-acid sequence for Chai-1 follow-up. |
| `uniprot`, `gene`, `species` | Biological identifiers retained in reports. |

Do not mix boxes derived from different conventions without recording `pocket_source`. A whole-protein blind box is exploratory and should not be ranked as equally reliable to a validated co-crystal pocket.

Calibration must use the same receptor state, box, scoring function, and search settings as the compound screen. Lower z-scores are better for Vina-style energies when calculated as `(score - mean) / sd`.

When only part of a panel is calibrated, keep calibrated and uncalibrated ranks in separate `rank_basis` groups. Do not interpret their repeated rank numbers as one common scale.
