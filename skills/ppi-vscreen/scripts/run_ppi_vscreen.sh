#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: run_ppi_vscreen.sh TARGET_PDB CANDIDATE_PDB_DIR OUTPUT_DIR" >&2
  exit 2
fi

TARGET="$(readlink -f "$1")"
CANDIDATES="$(readlink -f "$2")"
OUTPUT="$(readlink -m "$3")"

if [[ ! -s "$TARGET" ]]; then
  echo "Target PDB not found or empty: $TARGET" >&2
  exit 2
fi
if [[ ! -d "$CANDIDATES" ]]; then
  echo "Candidate directory not found: $CANDIDATES" >&2
  exit 2
fi
if [[ -e "$OUTPUT" ]]; then
  echo "Output directory already exists; choose a new directory: $OUTPUT" >&2
  exit 2
fi

mkdir -p "$OUTPUT/cases"
printf 'candidate_id\tsource_pdb\tcase_dir\n' > "$OUTPUT/screen_manifest.tsv"

count=0
CASE_IDS=()
while IFS= read -r -d '' candidate; do
  name="$(basename "$candidate")"
  id="${name%.*}"
  id="$(printf '%s' "$id" | tr -cs 'A-Za-z0-9._-' '_')"
  [[ -n "$id" ]] || id="candidate"
  case_id="$id"
  suffix=1
  while [[ -e "$OUTPUT/cases/$case_id" ]]; do
    case_id="${id}_${suffix}"
    suffix=$((suffix + 1))
  done

  case_dir="$OUTPUT/cases/$case_id"
  mkdir -p "$case_dir"
  ln -s "$TARGET" "$case_dir/receptor.pdb"
  ln -s "$(readlink -f "$candidate")" "$case_dir/ligand.pdb"
  printf '%s\t%s\t%s\n' "$case_id" "$candidate" "$case_dir" >> "$OUTPUT/screen_manifest.tsv"
  CASE_IDS+=("$case_id")
  count=$((count + 1))
done < <(find "$CANDIDATES" -type f -iname '*.pdb' -print0 | sort -z)

if [[ "$count" -eq 0 ]]; then
  echo "No .pdb candidate files found in: $CANDIDATES" >&2
  exit 2
fi

# The existing LightDock helper defaults to ANM when ANM_FLAG is unset. A
# whitespace default expands to no flag for the cheap rigid-body first pass.
export SWARMS="${SWARMS:-50}"
export GLOWWORMS="${GLOWWORMS:-50}"
export STEPS="${STEPS:-20}"
export TOPN="${TOPN:-3}"
export SCORING="${SCORING:-fastdfire}"
export CORES="${CORES:-$(nproc 2>/dev/null || echo 8)}"
export ANM_FLAG="${ANM_FLAG- }"

LIGHTDOCK_HELPER="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lightdock/scripts" && pwd)/run_lightdock_batch.sh"
if command -v "${LIGHTDOCK_SETUP_BIN:-lightdock3_setup.py}" >/dev/null 2>&1 && command -v "${LIGHTDOCK_RUN_BIN:-lightdock3.py}" >/dev/null 2>&1; then
  bash "$LIGHTDOCK_HELPER" "$OUTPUT/cases" "${CASE_IDS[@]}"
elif command -v conda >/dev/null 2>&1; then
  conda run -n "${LIGHTDOCK_CONDA_ENV:-lightdock}" \
    bash "$LIGHTDOCK_HELPER" "$OUTPUT/cases" "${CASE_IDS[@]}"
else
  echo "LightDock is not available on PATH and Conda was not found." >&2
  exit 2
fi

printf 'candidate_id\ttop_score\tranking_file\trepresentative_pdb\n' > "$OUTPUT/screen_summary.tsv"
while IFS=$'\t' read -r case_id source_pdb case_dir; do
  [[ "$case_id" == "candidate_id" ]] && continue
  ranking="$case_dir/rank_by_scoring.list"
  top_pdb="$case_dir/top_1.pdb"
  score="NA"
  if [[ -s "$ranking" ]]; then
    score="$(awk 'NR == 2 {print $NF; exit}' "$ranking")"
  fi
  printf '%s\t%s\t%s\t%s\n' "$case_id" "$score" "$ranking" "$top_pdb" >> "$OUTPUT/screen_summary.tsv"
done < "$OUTPUT/screen_manifest.tsv"

echo "PPI screen complete: $OUTPUT"
echo "Candidates: $count"
echo "Summary: $OUTPUT/screen_summary.tsv"
