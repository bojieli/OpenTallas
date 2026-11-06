#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:?staged event root}; OUT=${2:?new output}; MEM=${3:-24}; CPUS=${4:-8}
grep -q "DATA wire FIXED and healthy driver locked" "$ROOT/construction.log"
OT_ECO_FROM=final OT_PRD_TARGETED=1 OT_PRD_TARGET_SLEW_PS=300 OT_PRD_MAX_WIRE_LENGTH=80 \
 OT_LEC_SOLVER="$ROOT/solver" python3 -I "$ROOT/tools_bg/tools/die_plan/eco_loop.py" run \
 --kit "$ROOT/kit" --out "$OUT" --runner "$ROOT/kit/run_kit_hbm.sh" \
 --max-iter 2 --mem "$MEM" --cpus "$CPUS" --keep --lec --lec-tool "$ROOT/tools_bg/tools/die_plan/lec.py"
