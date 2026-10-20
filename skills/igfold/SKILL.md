---
name: igfold
display_name: IgFold 抗体结构预测
display_name_en: IgFold Antibody Modeling
description: Predict an antibody Fab structure from VH and VL amino-acid sequences with an existing local IgFold installation. Use for antibody variable-domain modeling and PDB output; requires IgFold and its model checkpoints separately.
description_zh: 从 VH 与 VL 氨基酸序列预测抗体 Fab 结构，输出 PDB。适用于抗体可变区建模；需另行安装 IgFold 及其模型权重。
description_en: Predict an antibody Fab structure from VH and VL amino-acid sequences with an existing local IgFold installation, producing PDB output. Requires IgFold and its model checkpoints separately.
category: 科研/生物
version: 1.0.0
author: 小猪莹(keyanzhu999)
---

# IgFold Antibody Modeling

Use this skill when the user provides antibody variable-domain sequences and wants a Fab structure. IgFold, its checkpoints, and a compatible Python environment must be installed separately; this repository contains the Codex workflow and runner, not model weights.

## Inputs

- `VH`: heavy-chain variable-domain amino-acid sequence.
- `VL`: light-chain variable-domain amino-acid sequence.
- Optional: model name, output directory, CPU mode, refinement, and antibody numbering.

Keep the original sequences and use chain keys `H` and `L`. Do not infer a missing chain from a sequence label or silently substitute a different antibody.

## Run

Activate the environment in which `igfold` and its checkpoints work, then run from this skill directory:

```bash
python scripts/predict_fab.py \
  --vh @vh.fasta \
  --vl @vl.fasta \
  --name example_fab \
  --out-dir /path/to/output
```

The runner writes FASTA, PDB, and a summary file. Use `--cpu` when GPU inference is unavailable, `--no-renum` if numbering dependencies fail, and `--refine` only when a compatible refinement backend is installed and requested.

## Check

Confirm the PDB contains both `H` and `L` chains, inspect missing residues and clashes, and report the IgFold environment and checkpoint source. A predicted antibody model is a structural hypothesis, not experimental evidence of antigen binding.
