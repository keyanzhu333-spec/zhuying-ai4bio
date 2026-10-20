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

Use Python 3.10 or newer. The report hides absolute paths by default and never
prints secret values. `--private-paths` is an opt-in diagnostic for local use.
A missing command means it was not found in the active shell; activate the
intended environment or set an override from `config/tools.example.env`.
`--require gromacs` (or other listed tool names) returns nonzero when a required
command is missing. Detection is not a GPU or model-inference benchmark.

## Install skills

```bash
python3 scripts/install_skills.py --dry-run
python3 scripts/install_skills.py
```

By default the installer leaves existing skills untouched. Update an existing
installation from the repository root with:

```bash
git pull --ff-only
python3 scripts/install_skills.py --update --dry-run
python3 scripts/install_skills.py --update
```

`--update` stages the new skill files first, backs up old skill directories
beside the active skills directory under `skill-backups/`, and preserves local
runtime folders, virtual environments, weights, credentials, and private
configuration. Each installed skill records its source commit in
`.zy-ai4bio-install.json`. Installation failure rolls back the replacements.
Local edits to skill instructions/scripts remain in the backup; review those
edits before merging them into an updated skill. Use the updated skills on your
next Codex turn. Pass `--backup-dir` to choose a different backup parent.

To test without touching Codex, pass `--target /tmp/zy-ai4bio-skills`.
Selecting PPI screening includes LightDock; selecting reverse screening includes
UniDock screening, unless that dependency is already installed. Optional
follow-up tools remain separate. The installed `zy-ai4bio` includes its environment
checker, configuration examples, and this guide; it does not depend on keeping
the original repository at a particular path.

## Runtime setup by skill

Install only the environments needed for the current workflow. The following
commands run in Linux/WSL2 after installing Conda/Miniforge. Package solvers and
GPU drivers depend on the target platform; record the resolved versions for
each research project.

| Skills | Setup and verification |
| --- | --- |
| `diffdock` | Python standard library for API calls; configure your own NVIDIA key with `set_key.py`. For interactions run `python skills/diffdock/scripts/setup_plip.py`, then `--check`. |
| `gnina-dock` | Run `python skills/gnina-dock/scripts/install_gnina_runtime.py`; activate `zy-gnina`. Obtain GNINA from its official releases, set `GNINA_BIN`, and rerun with `--check`. |
| `unidock-vscreen`, `reverse-target-vscreen` | Build UniDock-Pro using its upstream CUDA/CMake instructions. Set `UNIDOCK_PRO_BIN` to the executable `udp`. Reverse screening additionally needs Open Babel (`conda install -c conda-forge openbabel`). Run the skill's `check_unidock.py` or `check_reverse_vscreen.py --strict`. |
| `lightdock`, `ppi-vscreen` | In an isolated Python environment run `python -m pip install lightdock`; check `lightdock3_setup.py --help`, `lightdock3.py --help`, and the `lgd_*` helpers. Shell workflows require Linux/WSL and Bash. |
| `haddock3-nucleic-acid` | Install `haddock3` in an isolated Python environment using `python -m pip install haddock3`. Verify `haddock3 --help`, then setup-only on the intended configuration. |
| `chai1-complex` | Upstream supports Linux, Python >=3.10 and a compatible CUDA GPU. Install `python -m pip install chai_lab==0.6.1`; verify `chai-lab fold --help`. Set `CHAI_DOWNLOADS_DIR` for weights. A CPU CLI option is not a promise of practical CPU inference. |
| `gromacs-md` | Install GROMACS (for example a CPU build with `conda create -n zy-gromacs -c conda-forge gromacs python=3.11 matplotlib`), activate it, run `check_gromacs.py`. GPU builds must match the machine's driver. |
| `igfold` | Follow IgFold's upstream environment and checkpoint instructions. Install numbering/refinement dependencies only when those features are requested. Run `predict_fab.py` with the environment's Python. |
| `literature-skill` | Python standard library; verify the RSS URL is reachable. No local GPU or separate scientific engine needed. |
| `zy-ai4bio`, `zy-ai4bio-wsl2-setup` | Python installer/diagnostic; Windows PowerShell for WSL setup. The installed bootstrap accepts the cloned repository root as its first argument. |

Official sources: [GNINA](https://github.com/gnina/gnina),
[UniDock-Pro](https://github.com/NiBoyang/UniDock-Pro),
[LightDock](https://github.com/lightdock/lightdock),
[HADDOCK3](https://github.com/haddocking/haddock3),
[Chai-1](https://github.com/chaidiscovery/chai-lab),
[GROMACS](https://manual.gromacs.org/current/install-guide/index.html),
[IgFold](https://github.com/Graylab/IgFold).

For repeated deployments, export the resolved environment after a successful
tool-specific test. The environment recipe included with GNINA is a solver
input, not a universal binary lockfile. Drivers and model files are not copied
from the developer's machine.

## Large resources

Choose a directory outside the repository and set it for the current shell:

```bash
export ZY_AI4BIO_DATA="$HOME/zy-ai4bio-data"
mkdir -p "$ZY_AI4BIO_DATA"
```

Use `config/resources.example.json` as the schema for each local ligand library, target panel, model-weight directory, or cache. Record the source URL, license, file format, index/manifest, and checksums. Do not commit downloaded SDF/PDBQT libraries or model checkpoints unless their license and size explicitly permit redistribution.
This file is an example inventory, not a database downloader. `ZY_AI4BIO_DATA`
is an organizational convention; pass concrete ligand indexes, target
manifests, and model cache paths to each tool.

## Windows

Native Windows Codex can use API- and Python-based skills. Linux scientific tools should run inside WSL2. Use `zy-ai4bio-wsl2-setup` to detect and reuse an existing distribution before creating a new Ubuntu environment.

## Privacy rules

- Never commit API keys, tokens, cookies, SSH keys, credential files, or private `.env` files.
- Use relative paths in examples and command-line arguments at runtime.
- Do not publish raw research projects, unpublished structures, trajectories, patient/sample data, or personal home-directory paths.
- Generated reports may contain source paths; inspect them before sharing.

## Repeatable checks

```bash
python -m unittest discover -s tests -v
python scripts/check_portability.py
python tests/smoke_gromacs.py --gmx gmx
```

The offline tests exercise fresh installs and controlled external commands
without API requests or GPU jobs. The optional GROMACS smoke test actually
runs a small water box through four short stages and checkpoint continuation.
It checks execution, not scientific convergence. `docs/ci/portability.yml`
is an Actions template for Linux/Windows with Python 3.10/3.12. Enable it by
copying it to `.github/workflows/portability.yml` with an account authorized to
manage workflows. It is not active with the current publishing credential.
Native Windows passing wrapper tests would not mean Linux scientific engines
can run there without WSL.

The publication scanner examines current tracked files (or `--staged` content).
It prints finding locations rather than secret values. It does not erase
Git history; old author emails and past versions remain until a separate
history migration is performed.
