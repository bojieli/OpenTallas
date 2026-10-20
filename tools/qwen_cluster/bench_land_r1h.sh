#!/bin/bash
# Lockstep bench of rtl/physical/qcluster/qfd_c_land_r1h.sv vs qfd_c_land_r (rtl/physical/qcluster/qfd_c_land.sv),
# Verilator 5.050 (closure daemon pin).  usage: bench_land_r1h.sh OUTDIR [CASE...]  (repo root; default all cases)
#   MUT0K1 MUT0K2 MUT0K3 : unmutated, K 1/2/3                    -> LAND_R1H_PASS
#   M1 : one-hot reset value off by one slot (all groups)        -> LAND_R1H_MISMATCH
#   M2 : warm copy reset to 1 AND written-flag gating dropped (stale ring slot read after a reset) -> LAND_R1H_MISMATCH
#        (each alone is an equivalent mutant: warm and vld both block the first K unwritten reads)
#   M3 : one-hot rotates right instead of left                   -> LAND_R1H_MISMATCH
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1"); shift
CASES=${*:-MUT0K1 MUT0K2 MUT0K3 M1 M2 M3}
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
DUT=rtl/physical/qcluster/qfd_c_land_r1h.sv; REF=rtl/physical/qcluster/qfd_c_land.sv; TB=tools/qwen_cluster/tb_land_r1h.sv
rc=0
for C in $CASES; do
 S="$OUT/src_$C"; mkdir -p "$S"; F="$S/qfd_c_land_r1h.sv"; cp "$DUT" "$F"; K=2
 case $C in
  MUT0K1) K=1;; MUT0K2) K=2;; MUT0K3) K=3;;
  M1) sed -i 's/1.b1} << S0;/1'"'"'b1} << ((S0 + 1) % D);/' "$F";;
  M2) sed -i -e 's/wg <= 1.b0; end/wg <= 1'"'"'b1; end/' -e 's/{N{oh\[s\] \& vld\[s\]}}/{N{oh[s]}}/' "$F";;
  M3) sed -i 's/oh <= {oh\[D-2:0\], oh\[D-1\]};/oh <= {oh[0], oh[D-1:1]};/' "$F";;
  *) echo "unknown case $C"; rc=1; continue;;
 esac
 nd=$(diff "$DUT" "$F" | grep -c '^>'); echo "== $C: K=$K source lines mutated: $nd"
 if [[ $C == M* && $C != MUT0* && $nd == 0 ]]; then echo "LAND_R1H_BENCH $C: sed matched nothing"; rc=1; continue; fi
 B="$OUT/obj_$C"
 "$V" --binary --timing -j 4 -Wno-fatal --top-module tb -GK=$K -Mdir "$B" $TB $REF "$F" > "$OUT/build_$C.log" 2>&1 \
   || { rm -rf "$B"; "$V" --binary --timing -j 4 -Wno-fatal --top-module tb -GK=$K -Mdir "$B" $TB $REF "$F" > "$OUT/build_$C.log" 2>&1; }
 [[ -x "$B/Vtb" ]] || { echo "LAND_R1H_BENCH $C: build failed"; tail -20 "$OUT/build_$C.log"; rc=1; continue; }
 "$B/Vtb" > "$OUT/$C.log" 2>&1; xrc=$?; tail -5 "$OUT/$C.log"
 if [[ $C == MUT0* ]]; then
  if [[ $xrc == 0 ]] && grep -q "LAND_R1H_PASS K=$K" "$OUT/$C.log" && ! grep -q LAND_FAULT "$OUT/$C.log"; then echo "LAND_R1H_BENCH $C PASS"; else echo "LAND_R1H_BENCH $C UNEXPECTED FAIL"; rc=1; fi
 else
  if [[ $xrc != 0 ]] && ! grep -q LAND_R1H_PASS "$OUT/$C.log" && grep -qE 'LAND_R1H_MISMATCH K=2 edge=[0-9]+' "$OUT/$C.log"; then echo "LAND_R1H_BENCH $C FAILS AS REQUIRED"; else echo "LAND_R1H_BENCH $C NOT CAUGHT (exit $xrc)"; rc=1; fi
 fi
done
echo "LAND_R1H_BENCH_EXIT $rc CASES=$CASES"; exit $rc
