#!/usr/bin/env bash
# el1013-hbm-redesign-suvop: unit bench of the SU.VOP leaf ot_hgi_sv_lane2 + ot_hgi_sv_lmem (tb_hgi_sv_leaf: 12 seeds of
# stage / scrub / drain jobs against a behavioural VM wide-lane model).
#   usage: run_sv_leaf.sh <outdir> [MUT_V ...]      default: 0 1 2 5   (0 must PASS; 1, 2, 5 must FAIL)
#   one mutant alone (job mutant bench): run_sv_leaf.sh <outdir> 2  -> prints "LEAF_TB FAIL ..." and exits 1 when killed.
# Exit 0 only when every listed variant behaves as expected; a failed build is exit 2, never a pass.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "${1:-/tmp/hgi_sv_leaf}"); shift || true
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"; rc=0; set -- ${@:-0 1 2 5}; single=$#
for m in "$@"; do
  O=$OUT/obj_m$m
  "$VL" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-BLKSEQ -Wno-MULTIDRIVEN -O2 -j ${JOBS:-8} +define+MUT_V=$m ${LQ:+ +define+LQ=$LQ} \
     --top-module tb_hgi_sv_leaf --Mdir "$O" -o tb rtl/hbm_accel/generic/peers/ot_hgi_sv_unit.sv \
     rtl/hbm_accel/generic/adapters/tb/tb_hgi_sv_leaf.sv > "$OUT/build_m$m.log" 2>&1 \
     || { tail -15 "$OUT/build_m$m.log"; echo "MUT_V $m: BUILD FAILED"; exit 2; }
  "$O/tb" > "$OUT/leaf_m$m.log" 2>&1 || true
  grep -E "LEAF_TB (PASS|FAIL|stats)" "$OUT/leaf_m$m.log" | tail -2
  if [ "$m" = 0 ]; then grep -q "LEAF_TB PASS" "$OUT/leaf_m$m.log" || { echo "MUT_V 0: did not pass"; rc=1; }
  else grep -q "LEAF_TB FAIL" "$OUT/leaf_m$m.log" || { echo "MUT_V $m: NOT KILLED"; rc=1; }; fi
done
if [ "$single" = 1 ] && [ "$1" != 0 ]; then [ $rc = 0 ] && exit 1 || exit 0; fi     # one mutant: exit 1 = killed
[ $rc = 0 ] && echo "SV_LEAF GATE PASS" || { echo "SV_LEAF GATE FAIL"; exit 1; }
