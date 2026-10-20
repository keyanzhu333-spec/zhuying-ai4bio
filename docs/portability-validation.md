# Portability verification

This record distinguishes repository behavior from scientific-runtime readiness.

## Verified in the portability review

- Fresh installation copies skill resources and the coordinator's environment
  checker/configuration examples. Runtime folders, credentials, and Python caches
  are excluded.
- Thirteen offline regression tests pass with Python 3.10 and an isolated
  Python 3.12 environment. They cover installation, command overrides, quoted
  paths, Chai-1 output-directory requirements, stage preservation, CPU selection,
  and checkpoint continuation.
- A small water box generated using GROMACS's distributed water coordinates ran
  EM, NVT, NPT, a twenty-step production test, and checkpoint continuation using
  GROMACS 2026.0. No private protein, ligand, or research project was used.
- The source publication scan checks for personal absolute paths, literal host
  IPs, private-key material, token patterns, and accidental runtime/binary files.
  Intentional public contact information and copyright notices are retained.

## Target-machine checks still required

- GPU driver/build compatibility, GPU memory, and model weights for inference.
- Live NVIDIA API credentials/service availability.
- A validated scientific input and force-field configuration for each real job.
- Tool-specific installation in the user's selected environment. Conda recipes
  describe dependencies; solver success does not prove every native library or
  GPU kernel works on every host.

The Actions template in `docs/ci/portability.yml` defines the offline suite for
Linux and Windows with Python 3.10 and 3.12. It is not enabled: the publishing
credential lacks the `workflow` scope. Copy it to `.github/workflows/portability.yml`
using an account with that permission, then inspect the actual Actions result
before claiming a platform passed. Windows cloud tests have not run in this review.
The Linux-oriented scientific engines still require
Linux/WSL even when Python wrapper tests pass on Windows.

Run commands and dependency setup are in [portable-installation.md](portable-installation.md).
Continuation behavior follows the [GROMACS checkpoint documentation](https://manual.gromacs.org/current/user-guide/managing-simulations.html).
