#!/bin/bash
# Lockstep bench of rtl/physical/qcluster/qfd_c_land_k.sv (qfd_c_land_w1k + qfd_c_land_r1k, kept per-group control copies)
# vs qfd_c_land_w + qfd_c_land_r (rtl/physical/qcluster/qfd_c_land.sv), Verilator 5.050 (closure daemon pin).
# usage: bench_land_k.sh OUTDIR [CASE...]  (repo root; default all cases).  Sources read: tb_land_k.sv, qfd_c_land.sv, qfd_c_land_k.sv
#   MUT0K1 MUT0K2 MUT0K3 : unmutated, K 1/2/3                         -> LAND_K_PASS
#   M1 : writer one-hot reset value off by one slot                   -> LAND_K_MISMATCH
#   M2 : writer one-hot rotates right                                 -> LAND_K_MISMATCH
#   M3 : writer slot enable ignores the group reset copy (writes in reset) -> LAND_K_MISMATCH
#   M4 : reader one-hot reset value off by one slot                   -> LAND_K_MISMATCH
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1"); shift
CASES=${*:-MUT0K1 MUT0K2 MUT0K3 M1 M2 M3 M4}
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
DUT=rtl/physical/qcluster/qfd_c_land_k.sv; REF=rtl/physical/qcluster/qfd_c_land.sv; TB=tools/qwen_cluster/tb_land_k.sv
rc=0
for C in $CASES; do
 S="$OUT/src_$C"; mkdir -p "$S"; F="$S/qfd_c_land_k.sv"; cp "$DUT" "$F"; K=2
 case $C in
  MUT0K1) K=1;; MUT0K2) K=2;; MUT0K3) K=3;;
  M1) sed -i "s/if (!rqg) woh <= {{(D-1){1'b0}}, 1'b1};/if (!rqg) woh <= {{(D-2){1'b0}}, 2'b10};/" "$F";;
  M2) sed -i 's/else      woh <= {woh\[D-2:0\], woh\[D-1\]};/else      woh <= {woh[0], woh[D-1:1]};/' "$F";;
  M3) sed -i 's/wire en = rqg \&\& woh\[s\];/wire en = woh[s];/' "$F";;
  M4) sed -i 's/if (!rqg) oh <= {{(D-1){1.b0}}, 1.b1} << S0;/if (!rqg) oh <= {{(D-1){1'"'"'b0}}, 1'"'"'b1} << ((S0 + 1) % D);/' "$F";;
  *) echo "unknown case $C"; rc=1; continue;;
 esac
 nd=$(diff "$DUT" "$F" | grep -c '^>'); echo "== $C: K=$K source lines mutated: $nd"
 if [[ $C == M* && $C != MUT0* && $nd == 0 ]]; then echo "LAND_K_BENCH $C: sed matched nothing"; rc=1; continue; fi
 B="$OUT/obj_$C"
 "$V" --binary --timing -j 4 -Wno-fatal --top-module tb -GK=$K -Mdir "$B" $TB $REF "$F" > "$OUT/build_$C.log" 2>&1 \
   || { rm -rf "$B"; "$V" --binary --timing -j 4 -Wno-fatal --top-module tb -GK=$K -Mdir "$B" $TB $REF "$F" > "$OUT/build_$C.log" 2>&1; }
 [[ -x "$B/Vtb" ]] || { echo "LAND_K_BENCH $C: build failed"; tail -20 "$OUT/build_$C.log"; rc=1; continue; }
 "$B/Vtb" > "$OUT/$C.log" 2>&1; xrc=$?; tail -5 "$OUT/$C.log"
 if [[ $C == MUT0* ]]; then
  if [[ $xrc == 0 ]] && grep -q "LAND_K_PASS K=$K" "$OUT/$C.log" && ! grep -q LAND_FAULT "$OUT/$C.log"; then echo "LAND_K_BENCH $C PASS"; else echo "LAND_K_BENCH $C UNEXPECTED FAIL"; rc=1; fi
 else
  if [[ $xrc != 0 ]] && ! grep -q LAND_K_PASS "$OUT/$C.log" && grep -qE 'LAND_K_MISMATCH K=2 edge=[0-9]+' "$OUT/$C.log"; then echo "LAND_K_BENCH $C FAILS AS REQUIRED"; else echo "LAND_K_BENCH $C NOT CAUGHT (exit $xrc)"; rc=1; fi
 fi
 rm -rf "$B"
done
echo "LAND_K_BENCH_EXIT $rc CASES=$CASES"; exit $rc
