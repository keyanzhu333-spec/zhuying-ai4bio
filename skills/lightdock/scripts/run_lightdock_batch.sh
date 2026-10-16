#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: run_lightdock_batch.sh ROOT_DIR [CASE_REL ...]" >&2
  echo "Each case must contain receptor.pdb and ligand.pdb" >&2
  exit 2
fi

ROOT="$(cd "$1" && pwd)"
shift

SWARMS="${SWARMS:-400}"
GLOWWORMS="${GLOWWORMS:-200}"
STEPS="${STEPS:-100}"
SCORING="${SCORING:-fastdfire}"
CORES="${CORES:-$(nproc 2>/dev/null || echo 8)}"
TOPN="${TOPN:-10}"
ANM_FLAG="${ANM_FLAG:---anm}"
export LIGHTDOCK_ANM_REC="${LIGHTDOCK_ANM_REC:-10}"
export LIGHTDOCK_ANM_LIG="${LIGHTDOCK_ANM_LIG:-10}"

if [[ $# -eq 0 ]]; then
  mapfile -t CASES < <(find "$ROOT" -mindepth 1 -maxdepth 3 -type f -name receptor.pdb -printf '%h\n' | sort)
else
  CASES=()
  for rel in "$@"; do
    CASES+=("$ROOT/$rel")
  done
fi

run_one() {
  local dir="$1"
  local rel="${dir#$ROOT/}"
  echo "=================================================================="
  echo "LightDock case: $rel"
  echo "=================================================================="
  if [[ ! -s "$dir/receptor.pdb" || ! -s "$dir/ligand.pdb" ]]; then
    echo "[SKIP] $rel lacks receptor.pdb or ligand.pdb" >&2
    return 0
  fi

  cd "$dir"

  lightdock3_setup.py receptor.pdb ligand.pdb \
    -s "$SWARMS" -g "$GLOWWORMS" \
    $ANM_FLAG \
    --noxt --noh --now

  lightdock3.py setup.json "$STEPS" \
    -s "$SCORING" -c "$CORES"

  local sw
  for sw in swarm_*; do
    [[ -d "$sw" ]] || continue
    lgd_generate_conformations.py receptor.pdb ligand.pdb \
      "$sw/gso_${STEPS}.out" "$GLOWWORMS" >/dev/null 2>&1 || true
    lgd_cluster_bsas.py "$sw/gso_${STEPS}.out" >/dev/null 2>&1 || true
  done

  lgd_rank.py "$SWARMS" "$STEPS"
  lgd_top.py receptor.pdb ligand.pdb rank_by_scoring.list "$TOPN"

  echo "Done: $rel"
  echo "  ranking: $dir/rank_by_scoring.list"
  echo "  top pdb: $dir/top_1.pdb ... top_${TOPN}.pdb"
}

for case_dir in "${CASES[@]}"; do
  run_one "$case_dir"
done

echo "All LightDock cases complete."
