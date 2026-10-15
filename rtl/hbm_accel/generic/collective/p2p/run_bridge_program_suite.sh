#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory};mkdir -p "$OUT"
P=$ROOT/rtl/hbm_accel/generic/collective/p2p
for mode in q3 q2 scale4 data wrap;do
 args=();[[ $mode != q2 ]] || args+=(-GQID=1);[[ $mode != scale4 ]] || args+=(-GNBANKS=4)
 [[ $mode != data ]] || args+=(-GMUT_DATA=1);[[ $mode != wrap ]] || args+=(-GMUT_WRAP=1)
 set +e
 "$P/run_bridge_program_bench.sh" "$OUT/$mode" "${args[@]}" > "$OUT/$mode.log" 2>&1
 rc=$?
 set -e
 if [[ $mode == data || $mode == wrap ]];then
  [[ $rc != 0 ]];grep -q 'CONTROL mismatch' "$OUT/$mode/run.log";echo "BRIDGE_PROGRAM MUTANT PASS $mode"
 else
  [[ $rc == 0 ]];grep '^BRIDGE_PROGRAM' "$OUT/$mode/run.log"
 fi
 if [[ $mode == q3 || $mode == q2 ]];then
  q=0;[[ $mode != q2 ]] || q=1
  "$OUT/$mode/obj/Vtb_hgi_coll_bridge_program" +image="$ROOT/results/arch/hcoll_bridge_program_1015/g96_d0q$q.catalogue.hex" +length=1093 > "$OUT/$mode/g96.log" 2>&1
  grep '^BRIDGE_PROGRAM' "$OUT/$mode/g96.log"
 fi
 if grep -Eq '%Warning-(MULTIDRIVEN|LATCH|UNOPTFLAT)' "$OUT/$mode/build.log";then exit 1;fi
done
