---
name: zy-ai4bio
description: AI-for-biology workflow router that coordinates Codex skills for docking, screening, complex prediction, molecular dynamics, antibody modeling, visualization, databases, and literature, plus Windows/WSL2 environment setup. Use for broad or multi-step structural biology and drug-discovery tasks, or when a Windows user needs the local scientific workflows prepared under WSL2.
---

# ZY-AI4bio

Use this as the top-level coordinator for biology and drug-discovery tasks. Route to the most specific installed skill first; use this skill to combine them when a task spans multiple domains.

The sibling skills under `skills/` are bundled with this repository, but their scientific software and model weights are separate dependencies. Database, literature API, sequence-viewer, and structure-viewer plugin skills are optional Codex integrations. Check that a child skill and its runtime are available before routing work to it, and report a missing dependency when a requested stage cannot run.

For a new machine, run the repository-level `scripts/check_environment.py`
before a local scientific workflow. Resolve commands from `PATH` first, then
from documented environment-variable overrides; never insert a developer's
home directory into a skill. Keep model weights and screening databases outside
Git under `ZY_AI4BIO_DATA`, with provenance and checksums recorded using
`config/resources.example.json`.

For a Windows user who needs Linux-oriented local computation, use `zy-ai4bio-wsl2-setup` to detect and reuse an existing WSL2 distribution or prepare one when absent. Native Windows Codex can still use skills that do not require Linux executables; do not treat WSL2 as mandatory for every request. Before running shell-based scientific workflows, verify the Codex agent is actually executing in WSL2 and the required scientific software is installed there.

## Routing

Read `references/skill-map.md` when the task is broad, ambiguous, or involves more than one biology workflow.

- For protein-small molecule blind docking with NVIDIA DiffDock API, use `diffdock`.
- For large ligand-library virtual screening with local UniDock-Pro, use `unidock-vscreen`.
- For reverse virtual screening of one small molecule against many protein targets, use `reverse-target-vscreen` to coordinate Open Babel, UniDock-Pro, GNINA, DiffDock, Chai-1, PLIP, and structure inspection.
- For prepared receptor-ligand docking with GNINA CNN rescoring, PyMOL visualization, and PLIP interaction analysis, use `gnina-dock`.
- For protein-protein, protein-DNA, or protein-RNA docking, use `lightdock`.
- For virtual screening of a protein library against one target protein, use `ppi-vscreen` to orchestrate LightDock, Chai-1, optional verified HADDOCK3 protein-protein refinement, and structural validation.
- For restraint-guided protein-DNA/RNA docking and HADDOCK3 refinement from PDB structures, use `haddock3-nucleic-acid`.
- For sequence-based protein-DNA/RNA complex structure prediction with local Chai-1, use `chai1-complex`.
- For single-protein, protein-protein, protein-nucleic-acid, protein-small-molecule, or protein-metal MD, plus trajectory analysis, plotting, or carefully validated MM/PBSA, use `gromacs-md`.
- For antibody, Fab, or nanobody structure prediction, use `igfold`.
- For local molecular structure inspection or rendering, use `structure-viewer:structure-viewer`.
- For FASTA, FASTQ, GenBank, alignments, variants, or chromatograms, use `sequence-viewer:biological-sequence-viewer`.
- For public biological database lookups, use the relevant `life-sciences-databases:*` skill.
- For RSS/Atom literature monitoring, daily research alerts, and topic-filtered paper updates, use `literature-skill`.
- For biomedical literature and PubMed/PMC/preprint lookups, use the relevant `life-sciences-literature:*` skill.
- For Windows OS detection, WSL2 provisioning, and installing the skill collection into WSL2, use `zy-ai4bio-wsl2-setup`.

## Workflow Pattern

1. Identify the biological object: gene/protein, ligand, sequence, structure, antibody chain, variant, sample set, study, or dataset.
2. Choose the narrowest child skill that can complete the immediate task.
3. When the request spans steps, chain skills explicitly and keep artifacts organized by stage.
4. Preserve each child skill's own safety, credential, citation, and validation instructions.
5. Report which child skill(s) were used and where outputs were saved.

## Common Chains

- Target plus compound: `life-sciences-databases:uniprot-skill` or `life-sciences-databases:pubchem-pug-skill` for identifiers, then `diffdock` for blind DiffDock docking, `unidock-vscreen` for large prepared PDBQT libraries, or `gnina-dock` when prepared structures and a binding box/reference ligand are available, then `gromacs-md` for MD if requested.
- Compound target fishing: use `reverse-target-vscreen` for one compound against a receptor panel, then execute its GNINA, DiffDock, Chai-1, and PLIP/structure-viewer queues in that order.
- Protein-protein mechanism: database lookup, structure retrieval via `life-sciences-databases:rcsb-pdb-skill` or local files, then `lightdock`.
- Protein-protein interaction screening: use `ppi-vscreen` for candidate-library preparation, uniform LightDock first-pass screening, Chai-1 shortlist prediction, and optional verified structure/refinement follow-up.
- Protein-nucleic-acid mechanism: retrieve or inspect protein and DNA/RNA structures with `life-sciences-databases:rcsb-pdb-skill` and `structure-viewer:structure-viewer`; use `haddock3-nucleic-acid` when restraints or refinement are needed, `lightdock` for blind PDB-to-PDB candidate poses, or `chai1-complex` when the starting point is sequence-based complex prediction.
- Antibody workflow: `igfold` for VH/VL modeling, `structure-viewer:structure-viewer` for inspection, then a docking skill if the user asks for interaction modeling.
- Evidence workflow: database skills for structured facts, literature skills for papers, `literature-skill` for RSS monitoring or daily alerts, then summarize evidence levels and limitations without overclaiming.

## Output Discipline

- Do not merge unrelated outputs into one folder. Prefer stage folders such as `docking/`, `interactions/`, `report/`, `md/`, `figures/`, `tables/`, and `literature/`.
- Do not expose or store API keys in skill folders, output folders, command text, reports, or Git history.
- Do not copy Conda environments, downloaded executables, model weights, large
  SDF/PDBQT libraries, trajectories, or machine-specific absolute paths into a
  skill. Ship reproducible installers, manifests, and checks instead.
- For scientific claims, distinguish prediction, annotation, database fact, literature evidence, and experimental validation.
