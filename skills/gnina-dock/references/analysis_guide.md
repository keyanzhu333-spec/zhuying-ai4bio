# GNINA docking and interaction-analysis guide

This guide carries the ZYDock-style analysis discipline into a GNINA–PyMOL–PLIP workflow. It is a checklist, not a replacement for the GNINA, PyMOL, PLIP, or PoseBusters manuals.

## Quality gates

1. **Input identity** — Record receptor and ligand filenames, chains, residue/ligand identifiers, protonation/tautomer state, retained waters/cofactors/metals, and preparation tools.
2. **Box justification** — Record whether the box came from `--autobox_ligand` or explicit coordinates, the margin, and all dimensions in Å. A co-crystal-ligand box is different from a blind-docking box.
3. **Reproducibility** — Record GNINA version/backend, CNN model, CNN scoring mode, exhaustiveness, number of modes, seed, and the complete command/log.
4. **Pose integrity** — Confirm the selected SDF molecule/state is the intended ligand and pose. Check atom count, bond orders, coordinates, and GNINA score properties.
5. **Complex integrity** — Confirm receptor and ligand share the same coordinate frame and that PLIP receives one selected complex, not an unrelated receptor or all modes merged together.
6. **Chemical plausibility** — Inspect steric clashes, buried unsatisfied donors/acceptors, impossible valence, metal geometry, protonation-dependent contacts, and contacts mediated by omitted waters.

## Report schema

Use one row per detected interaction:

| Pose | CNNscore | CNNaffinity | minimizedAffinity | Type | Protein residue/chain | Ligand atom(s) | Geometry | Evidence | Caveat |
|---|---:|---:|---:|---|---|---|---|---|---|
| 1 | from SDF | from SDF | from SDF | H-bond / hydrophobic / π-stacking / π-cation / salt bridge / halogen / metal / water bridge | PLIP label | PLIP label | distance/angle if reported | PLIP TXT/XML + PyMOL | protonation, water, or geometry concern |

Summarize each pose separately before comparing poses. Prefer “pose 1 preserves the reference hinge hydrogen bond and has a better-packed hydrophobic end” over “pose 1 binds best.”

## GNINA score semantics

- **`minimizedAffinity`**: empirical GNINA affinity-like score, commonly interpreted as kcal/mol-like and used for ranking only within a comparable setup; more negative is better.
- **`CNNscore`**: CNN pose plausibility/confidence, approximately 0–1; it is not a binding affinity.
- **`CNNaffinity`**: CNN-predicted affinity-like score; higher is better, but it is not an experimental ΔG or a calibrated (K_d).
- For routine selection, flag `CNNscore > 0.5`, then rank plausible poses by `CNNaffinity` while reporting all three values.
- When comparing differently sized ligands, report ligand efficiency where possible: `LE = -minimizedAffinity / heavy_atoms`. This is a comparison aid, not a validated potency model.

## Interaction interpretation

- **Hydrogen bonds:** check donor/acceptor identity and protonation. A PLIP hit on a protonated or tautomer-sensitive atom needs a caveat.
- **Hydrophobic contacts:** interpret as packing support, not a directional bond. Repeated contacts across clustered poses are more persuasive than one isolated contact.
- **Aromatic interactions:** inspect ring orientation and chemical assignment; do not treat every close aromatic pair as a strong π interaction.
- **Salt bridges:** verify formal charges in the exact ligand/receptor state used for docking.
- **Halogen bonds:** verify covalent attachment and directional geometry; a short distance alone is not enough.
- **Metal contacts:** retain the correct metal and coordination model and flag force-field or protonation limitations.
- **Water bridges:** report only when the water is present in the analyzed complex and its placement is plausible.

## Pose comparison and validation

For multiple modes, cluster or visually group poses by ligand RMSD and binding orientation. Consider CNNscore/CNNaffinity, minimizedAffinity, recurrence of interactions with known important residues, pocket complementarity, absence of severe clashes, and consistency across seeds or modestly changed search settings. If the criteria disagree, report the trade-off and retain the leading alternatives.

When a co-crystal ligand is available, redock it with the same box and compute pose RMSD. A practical guide is top-1 RMSD ≤ 2.0 Å as a pass, 2–3 Å as borderline, and >3 Å as a failure signal. Inspect receptor preparation, box definition, cofactors/metals/waters, and ligand protonation/tautomer when redocking fails.

## Minimal PyMOL review

For a selected pose, inspect the pocket in sticks and show polar contacts. Identify the ligand by its actual object/residue rather than assuming `LIG` or chain `A`:

```text
select lig, resn LIG and chain A
select pocket, byres (receptor within 5 of lig)
show sticks, lig or pocket
show cartoon, receptor
distance hbonds, lig, pocket, 3.6, mode=2
```

The distance command is only a visual aid; use PLIP's reported interaction geometry for the table.
