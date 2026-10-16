# Scenario Workflows

Use this reference after selecting a scenario in `SKILL.md`. The examples are decision rules, not universal force-field prescriptions. Record the exact parameter set and version used in every project.

## Single Protein

### Prepare

- Confirm the biologically relevant monomer or oligomer rather than assuming the crystallographic asymmetric unit is correct.
- Resolve alternate conformations, missing side-chain atoms, missing residues, termini, disulfides, protonation states, covalent modifications, cofactors, and retained waters.
- Use a validated protein force field with its supported water model. Avoid ligand parameterization steps when the system contains only standard protein residues and ions.

### Validate

- Inspect steric clashes and backbone/side-chain geometry before solvation.
- During equilibration, verify temperature, pressure, density, box dimensions, potential energy, and restraint release.
- For intrinsically disordered regions or flexible termini, interpret high mobility as a possible physical feature, not automatically as failure.

### Analyze

- Backbone or C-alpha RMSD, per-residue RMSF, radius of gyration, SASA, secondary structure, intraprotein hydrogen bonds, PCA, and FEL.
- Compare domains separately when rigid-domain motion would make a whole-protein RMSD misleading.

## Protein-Protein Complex

### Prepare

- Preserve unique chain identifiers and partner boundaries through topology generation.
- Repair clashes from docking, but do not over-minimize the interface until the starting pose loses its provenance.
- Create named groups for each partner and the interface. Define the interface by a documented starting-structure or trajectory contact cutoff.
- Apply compatible protein parameters to all partners; account explicitly for glycans, covalent links, modified residues, cofactors, and interface ions.

### Validate

- Fit the trajectory consistently before comparing partner motion.
- Check whether one partner crosses the periodic boundary or rotates/translates as a rigid body before interpreting interface distances.
- Inspect interface contacts after minimization and each equilibration stage to detect immediate pose collapse.

### Analyze

- Whole-complex RMSD plus per-partner RMSD after a stated fit.
- Inter-chain hydrogen bonds, salt bridges, contact count/occupancy, minimum distance, center-of-mass distance, interface SASA, and buried surface area.
- Optional MM/PBSA only after group definitions, dielectric assumptions, trajectory convergence, and parameter compatibility are validated. Treat it as comparative, not an absolute affinity measurement.

## Protein-Nucleic-Acid Complex

### Prepare

- Distinguish DNA from RNA and normalize residue/atom names without losing modified bases or terminal chemistry.
- Use a mutually compatible protein plus DNA/RNA force-field family and supported water/ion model.
- Preserve biologically meaningful Mg, other ions, and bridging waters. Determine whether each ion is structural, catalytic, or bulk solvent before deleting it.
- Do not split protein and nucleic acid using `ATOM` versus `HETATM`; both may be `ATOM` records.

### Validate

- Check strand direction, base pairing, backbone continuity, chain breaks, terminal phosphates, net charge, and counterion placement.
- Monitor whether restraints are needed during initial equilibration to prevent artifacts from an imperfect docked pose.
- Inspect protein-interface residues and nucleic-acid geometry after each equilibration stage.

### Analyze

- Protein backbone RMSD and nucleic-acid backbone/heavy-atom RMSD with explicitly stated fit groups.
- Protein-nucleic-acid hydrogen bonds, salt bridges, minimum distances, contact occupancy, interface SASA, and residue/nucleotide contact maps.
- DNA/RNA-specific geometry when supported: base-pair integrity, groove dimensions, helical parameters, base stacking, and phosphate contacts.
- Interpret ion-mediated contacts cautiously because residence and exchange can be sensitive to the ion model.

## Protein-Small-Molecule Complex

### Prepare

- Confirm ligand identity, stereochemistry, tautomer, protonation, formal charge, multiplicity, atom names, covalent state, and bound cofactors.
- Choose ligand parameters compatible with the protein force field. Validate charge derivation and all unusual bonded terms.
- Use a validated parameterization toolchain compatible with the selected force field; document versions, charge model, and residue naming.
- Preserve structurally important waters and ions when justified; do not treat every `HETATM` record as the ligand.

### Validate

- Compare ligand coordinates and atom ordering across PDB/MOL2/GRO/ITP files.
- Check total ligand charge, topology-coordinate atom counts, ring geometry, improper terms, and the minimized binding pose.
- Define protein and ligand groups by selection, not inherited numeric group IDs.

### Analyze

- Protein RMSD, ligand RMSD after fitting on the protein, ligand internal RMSD, center-of-mass/minimum distance, hydrogen-bond occupancy, contact occupancy, and key residue distances.
- Optional pocket volume/water occupancy when biologically relevant.
- MM/PBSA total and per-residue decomposition may support relative comparisons after convergence and uncertainty checks; they do not replace experimental affinity.

## Protein-Metal System

### Classify The Metal Site

Choose the physical model before topology generation:

- **Nonbonded ion model:** often appropriate for mobile or weakly bound ions when the selected force field was validated for that use.
- **Bonded model:** often needed for structural or catalytic sites with persistent, specific coordination.
- **Dummy-atom or advanced model:** consider when directionality, polarization, or coordination geometry cannot be represented adequately by a simple ion.
- **Cofactor model:** use validated parameters for heme, iron-sulfur clusters, or other metal-containing prosthetic groups rather than separating the metal blindly.

### Prepare And Validate

- Establish element, oxidation state, formal charge, spin state, coordination number, donor atoms, geometry, protonation of coordinating residues, covalent links, and catalytic waters.
- Trace parameters to a publication or validated parameter set compatible with the chosen biomolecular force field.
- Do not run generic `pdb2gmx` and accept a detached metal as a scientifically adequate model.
- After minimization and equilibration, inspect every metal-donor distance, coordination angle, geometry, and unintended ligand exchange.

### Analyze

- Protein RMSD/RMSF plus each metal-donor distance over time.
- Coordination number, donor occupancy, characteristic angles/dihedrals, geometry deviation, water exchange, and nearby hydrogen-bond network.
- Compare against known structural chemistry or reference structures.
- Do not apply standard MM/PBSA to a metal site unless the force-field and energy-decomposition assumptions have been specifically validated.
