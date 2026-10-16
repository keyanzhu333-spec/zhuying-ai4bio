#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${WSL_DISTRO_NAME:-}" ]]; then
  echo "Run this bootstrap from a WSL2 shell, not native Windows or another Linux host." >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
installer="$repo_root/scripts/install_skills.py"
if [[ ! -f "$installer" ]]; then
  echo "Repository installer not found: $installer" >&2
  exit 2
fi

missing_base=()
for executable in git python3 bwrap; do
  if ! command -v "$executable" >/dev/null 2>&1; then
    missing_base+=("$executable")
  fi
done
if (( ${#missing_base[@]} )); then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Missing base tools: ${missing_base[*]}. Install them with this distribution's package manager." >&2
    exit 2
  fi
  sudo apt-get update
  sudo apt-get install -y "${missing_base[@]/bwrap/bubblewrap}"
fi

target="${CODEX_HOME:-$HOME/.codex}/skills"
mapfile -t bundled < <(python3 "$installer" --list)
missing_skills=()
for name in "${bundled[@]}"; do
  if [[ -e "$target/$name" || -L "$target/$name" ]]; then
    printf 'Keeping existing skill: %s\n' "$name"
  else
    missing_skills+=("$name")
  fi
done

if (( ${#missing_skills[@]} )); then
  python3 "$installer" --target "$target" --skills "${missing_skills[@]}"
fi

printf '\nWSL distribution: %s\nSkill directory: %s\n' "$WSL_DISTRO_NAME" "$target"
printf 'Scientific executable checks (not found on PATH does not rule out a separate Conda environment):\n'
for executable in gmx gnina udp obabel chai-lab haddock3 nvidia-smi; do
  if command -v "$executable" >/dev/null 2>&1; then
    printf '  %-12s %s\n' "$executable" "$(command -v "$executable")"
  else
    printf '  %-12s %s\n' "$executable" 'not on PATH'
  fi
done
printf 'Start a new Codex chat with its agent set to WSL2 before running these skills.\n'
