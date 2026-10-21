#!/bin/bash
# Fleet only: run_owner_fold.sh SOURCE_ROOT OUT. Retains all build objects.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
ROOT=$(realpath "$1"); O=$(realpath -m "$2")
mkdir -p "$O"
python3 "$H/owner_fold_bench.py" --root "$ROOT" --out "$O/inputs"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > "$O/verilator_version.txt"
for M in 0 2; do
  mkdir -p "$O/m$M/run"
  "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT="$M" \
    --top-module tb_s81sl_vs -Mdir "$O/m$M/obj" -f "$O/inputs/sources.f" \
    --build-jobs "${J:-4}" -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/m$M/build.log" 2>&1
  cp "$O/inputs/"*.mem "$O/m$M/run/"
  (cd "$O/m$M/run"; ../obj/Vtb_s81sl_vs > ../run.log 2>&1)
  if [ "$M" = 0 ]; then
    grep -q '^PASS' "$O/m$M/run.log"
  else
    grep -q '^FAIL' "$O/m$M/run.log"
    grep -q '^MISMATCH op 11' "$O/m$M/run.log"
  fi
done
echo 'PASS owner-fold RB tree; MUT2 rejected'
