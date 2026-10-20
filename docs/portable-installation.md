# Portable installation

ZY-AI4Bio keeps four layers separate so the repository can be shared safely:

1. **Skills and scripts** live in Git and are installed with `scripts/install_skills.py`.
2. **Scientific executables** such as GROMACS, GNINA, UniDock-Pro, HADDOCK3, LightDock, Chai-1, Open Babel, PLIP, and PyMOL are installed on each machine.
3. **Model weights and large databases** live outside Git under a user-selected data root.
4. **Credentials** stay in environment variables or the user's private credential store.

## First check

Run from the repository root:

```bash
python3 scripts/check_environment.py --versions --json environment-report.json
```

The report contains availability and paths, not secret values. A missing command means only that it was not found in the active shell. Activate the intended Conda environment or set an override from `config/tools.example.env`, then check again.

## Install skills

```bash
python3 scripts/install_skills.py --dry-run
python3 scripts/install_skills.py
```

The installer does not overwrite an existing skill. To test without touching Codex, pass `--target /tmp/zy-ai4bio-skills`.

## Large resources

Choose a directory outside the repository and set it for the current shell:

```bash
export ZY_AI4BIO_DATA="$HOME/zy-ai4bio-data"
mkdir -p "$ZY_AI4BIO_DATA"
```

Use `config/resources.example.json` as the schema for each local ligand library, target panel, model-weight directory, or cache. Record the source URL, license, file format, index/manifest, and checksums. Do not commit downloaded SDF/PDBQT libraries or model checkpoints unless their license and size explicitly permit redistribution.

## Windows

Native Windows Codex can use API- and Python-based skills. Linux scientific tools should run inside WSL2. Use `zy-ai4bio-wsl2-setup` to detect and reuse an existing distribution before creating a new Ubuntu environment.

## Privacy rules

- Never commit API keys, tokens, cookies, SSH keys, credential files, or private `.env` files.
- Use relative paths in examples and command-line arguments at runtime.
- Do not publish raw research projects, unpublished structures, trajectories, patient/sample data, or personal home-directory paths.
- Generated reports may contain source paths; inspect them before sharing.
