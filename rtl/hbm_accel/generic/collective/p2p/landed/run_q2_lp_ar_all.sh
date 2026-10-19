#!/usr/bin/env bash
# TW2-COLLAR 10-19: XDIE-HBM4 AR_ITER=1 / ROWS=128 q2 COLL quadrant parent.  FLEET ONLY (Verilator 5.050):
#   LP_ROOT=<tree> bash rtl/hbm_accel/generic/collective/p2p/landed/run_q2_lp_ar_all.sh OUT [eq|lp|all]
# (1) EQ: the hard parent #(AR_ITER 1, ROWS 128) (ot_hfd_coll_q_hard_v8g.sv) == ot_hfd_coll_q2_lpf_ar under the scripted
#     programme stim_q2_lp_ar.vh (rows 64..99 = 7-bit pc, 3-trip AR loop with iter_ar_tag_step 3), every output every
#     cycle; PASS also needs LP_ACTIVITY ariter_step_cycles > 0.  EQ mutants (each MUST FAIL the lockstep):
#     m_refnostep (OT_COLL_ARITER_MUT_NOSTEP: the v8g reference drops the iteration product),
#     m_leafnostep (OT_ARITER_TAG_MUT_NOSTEP: the u_ariter leaf drops it), m_leafedge (OT_ARITER_TAG_MUT_EDGE: leaf takes
#     the iteration one edge early).
# (2) LP: the generated landed-parent bench (flat ot_hfd_coll_q2_lpf_ar vs ot_hfd_coll_q2_lp_ar, MUT 1/2/4, audit, unland).
set -u
cd "${LP_ROOT:?LP_ROOT}"
OUT=$(realpath -m "${1:?OUT}"); WHICH=${2:-all}; mkdir -p "$OUT"; rc=0
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator; export VERILATOR=$V
"$V" --version | tee "$OUT/verilator.version"
p=rtl/hbm_accel/generic/collective/p2p
SRC=$(python3 -c "import json;s=json.load(open('results/arch/landed_parent_1018/collq/spec_q2_ar.json'));print(' '.join(s['sources']+s['child_sources']))")
sha256sum $p/ot_hfd_coll_q_hard_v8g.sv $SRC $p/tb_hfd_coll_q2_lpf_ar_eq.sv $p/landed/stim_q2_lp_ar.vh > "$OUT/sources.sha256"
eq() {  # name defines...
  local n=$1; shift
  "$V" --binary -j ${VL_JOBS:-16} -O1 -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT "$@" \
    --top-module tb_hfd_coll_q2_lpf_ar_eq $p/ot_hfd_coll_q_hard_v8g.sv $SRC $p/tb_hfd_coll_q2_lpf_ar_eq.sv \
    -Mdir "$OUT/obj_$n" > "$OUT/$n.build.log" 2>&1 && "$OUT/obj_$n/Vtb_hfd_coll_q2_lpf_ar_eq" > "$OUT/$n.log" 2>&1
  rm -rf "$OUT/obj_$n"
  grep -E '^(LPF_EQ|LP_ACTIVITY|EQ_MISMATCH)' "$OUT/$n.log" 2>/dev/null | head -4 | sed "s/^/$n /"
}
if [ "$WHICH" = all ] || [ "$WHICH" = eq ]; then
  eq eq
  if grep -q '^LPF_EQ PASS' "$OUT/eq.log" 2>/dev/null && grep -Eq 'ariter_step_cycles=[1-9]' "$OUT/eq.log"; then echo "EQ PASS"; else echo "EQ FAIL"; rc=1; fi
  for m in "m_refnostep +define+OT_COLL_ARITER_MUT_NOSTEP" "m_leafnostep +define+OT_ARITER_TAG_MUT_NOSTEP" "m_leafedge +define+OT_ARITER_TAG_MUT_EDGE"; do
    set -- $m; eq $1 $2
    if grep -q '^LPF_EQ FAIL' "$OUT/$1.log" 2>/dev/null; then echo "EQ_MUTANT $1 REJECTED"; else echo "EQ_MUTANT $1 SURVIVED"; rc=1; fi
  done
fi
if [ "$WHICH" = all ] || [ "$WHICH" = lp ]; then
  SIM=verilator VL_JOBS=${VL_JOBS:-16} bash $p/landed/ot_hfd_coll_q2_lp_ar_bench.sh "$OUT/lp" > "$OUT/lp_bench.log" 2>&1; brc=$?
  cat "$OUT/lp_bench.log"; grep -h 'LP_ACTIVITY' "$OUT"/lp/mut0.log 2>/dev/null | sed 's/^/lp mut0 /'
  [ $brc -eq 0 ] || rc=1
  rm -rf "$OUT"/lp/obj*
fi
echo "Q2_LP_AR_ALL_EXIT $rc"; exit $rc
