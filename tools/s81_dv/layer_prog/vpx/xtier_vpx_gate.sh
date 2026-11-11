#!/bin/bash
# xtier_vpx_gate.sh <outdir> [op ...]  (cwd = repo root; heavy: one tb_vpx_ag build ~75 min / ~48 GB, run it via ot-run)
# S81-XTIER-FIX 11-11: the vpx send-path constants against the die's u_xr form (ot_s81sl_xrt1 / xrt3, FACE_LAND landing).
#   1. fast RTL gate: test_xtier_land.py (compiler constants == bound RTL landing edges; RTL mutants refused)
#   2. builds tb_vpx_ag with VPX_DEFINES (default OT_S81SL_KV_TRANSPORT = the as-built die define) once
#   3. every op x {none, row, shift} compiled by lower_vpx for that form (OT_S81_SELECTED_DEFINES = VPX_DEFINES):
#      none must PASS, row / shift must FAIL (run_vpx_ag.sh verdicts)
#   4. stale control per op: the same compile with the lo face landing forced to 0 (OT_S81_XTIER_FACE_OVERRIDE, i.e. the
#      pre-fix LO_AFTER_CTL 15) on the same binary must FAIL
# env FIXTURES = the L0 layer fixture dir (ops/attn.a_allgather.bin ...); OBJ = reuse a built obj dir (default <outdir>/b).
# Prints XTIER_VPX_GATE PASS / FAIL; exit 0 only on PASS.
set -u
O=$(realpath -m $1); shift
OPS=${*:-a_allgather router_allgather substage_hop0 out_allreduce_rs out_allreduce_ag}
FX=${FIXTURES:?set FIXTURES to the L0 fixture dir}
export VPX_DEFINES=${VPX_DEFINES-OT_S81SL_KV_TRANSPORT}
export OT_S81_SELECTED_DEFINES=$VPX_DEFINES PYTHONDONTWRITEBYTECODE=1
B=${OBJ:-$O/b}; mkdir -p $O $B
date > $O/started
PYTHONSAFEPATH=1 python3 -m pytest -q -p no:cacheprovider tools/s81_dv/layer_prog/test_xtier_land.py > $O/rtl_gate.log 2>&1 \
  || { tail -5 $O/rtl_gate.log; echo "XTIER_VPX_GATE FAIL rtl gate"; exit 1; }
GEN=tools/s81_dv/layer_prog/vpx/gen_vpx_ag.py
C=(); S=()
for op in $OPS; do
  for m in none row shift; do
    python3 -I $GEN --fixtures $FX --out $O/cases/${op}_$m --op $op --mut $m > $O/cases_${op}_$m.gen 2>&1 || { echo "GEN_FAIL $op $m"; exit 2; }
    C+=($O/cases/${op}_$m)
  done
  OT_S81_XTIER_FACE_OVERRIDE='{"lo": 0}' python3 -I $GEN --fixtures $FX --out $O/stale/${op}_none --op $op --mut none \
    > $O/stale_${op}.gen 2>&1 || { echo "GEN_FAIL stale $op"; exit 2; }
  S+=($O/stale/${op}_none)
done
bash tools/s81_dv/layer_prog/vpx/run_vpx_ag.sh $B > $O/build.out 2>&1
[ -x $B/obj/Vtb_vpx_ag ] || { cat $O/build.out; echo "XTIER_VPX_GATE FAIL build"; exit 3; }
for c in "${C[@]}" "${S[@]}"; do ( bash tools/s81_dv/layer_prog/vpx/run_vpx_ag.sh $B $c > $c/case.out 2>&1; echo "rc $?" >> $c/case.out ) & done
wait
bad=0
for c in "${C[@]}"; do
  r=$(tail -1 $c/case.out); echo "$(basename $c): $(grep -m1 CASE $c/case.out | cut -c1-200) | $r"; [ "$r" = "rc 0" ] || bad=1
done
for c in "${S[@]}"; do      # stale constant: run_vpx_ag expects PASS for mut none -> rc 1 and a check FAIL is the catch
  r=$(tail -1 $c/case.out); v=$(grep -m1 CASE $c/case.out | cut -c1-200); echo "stale $(basename $c): $v | $r"
  { [ "$r" = "rc 1" ] && echo "$v" | grep -q "exit 1:"; } || bad=1
done
date > $O/finished
[ $bad = 0 ] && { echo "XTIER_VPX_GATE PASS defines=$VPX_DEFINES ops=$OPS"; exit 0; }
echo "XTIER_VPX_GATE FAIL"; exit 1
