#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:?staged event root}; OUT=${2:?new ECO output}; MEM=${3:-24}; CPUS=${4:-8}
grep -q 'Q3_CLOCK_RECTANGLE PASS' "$ROOT/construction.log"
OT_ECO_FROM=final OT_PRD_TARGETED=1 OT_PRD_TARGET_SLEW_PS=300 OT_PRD_MAX_WIRE_LENGTH=100 \
 OT_LEC_SOLVER="$ROOT/solver" python3 -I "$ROOT/tools_bg/tools/die_plan/eco_loop.py" run \
 --kit "$ROOT/kit_A" --out "$OUT" --runner "$ROOT/kit_A/run_kit_hbm.sh" \
 --max-iter 2 --mem "$MEM" --cpus "$CPUS" --keep --lec --lec-tool "$ROOT/tools_bg/tools/die_plan/lec.py"
