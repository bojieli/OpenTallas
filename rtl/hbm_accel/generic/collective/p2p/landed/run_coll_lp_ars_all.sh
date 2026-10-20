#!/usr/bin/env bash
# HBM-ELEMOWN3/COLLQ3 10-19: SAFE successor of the q2/q3 COLL quadrant landed parents (ot_hfd_coll_<v>_lp_ars: hard issuer /
# fj / link_e1 / 16 reduce lanes, rc bundle pin registers).  FLEET ONLY (Verilator 5.050):
#   LP_ROOT=<tree> bash rtl/hbm_accel/generic/collective/p2p/landed/run_coll_lp_ars_all.sh q3|q2 OUT [eq|lp|rs|all]
# (1) EQ: the hard parent #(AR_ITER 1, ROWS 128) == ot_hfd_coll_<v>_lpf_ars under the _ar scripted programme
#     (stim_<v>_lp_ar.vh), every output every cycle (+ LP_ACTIVITY ariter_step_cycles > 0).  EQ mutants (each MUST FAIL):
#     m_refnostep (OT_COLL_ARITER_MUT_NOSTEP, reference), m_leafedge (OT_ARITER_TAG_MUT_EDGE, u_ariter leaf),
#     m_rlaneext (OT_COLL_RLANE_MUT_EXT: the hardened reduce lane's external operand rotated).
# (2) LP: the generated landed-parent bench (flat lpf_ars vs lp_ars, MUT 1/2/4, audit, unland).
# (3) RS: tb_hgi_coll_reduce_split_eq (reduce_static vs control + 16 lanes, random) + mutants SMUT_TAG / SMUT_BF16 / RLANE_MUT_EXT.
set -u
cd "${LP_ROOT:?LP_ROOT}"
VAR=${1:?q3|q2}; OUT=$(realpath -m "${2:?OUT}"); WHICH=${3:-all}; mkdir -p "$OUT"; rc=0
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator; export VERILATOR=$V
"$V" --version | tee "$OUT/verilator.version"
p=rtl/hbm_accel/generic/collective/p2p
SRC=$(python3 -c "import json;s=json.load(open('results/arch/landed_parent_1018/collq/spec_${VAR}_ars.json'));print(' '.join(s['sources']+s['child_sources']))")
TB=tb_hfd_coll_${VAR}_lpf_ars_eq
sha256sum $p/ot_hfd_coll_q_hard_v8g.sv $SRC $p/$TB.sv $p/landed/stim_${VAR}_lp_ar.vh $p/tb_hgi_coll_reduce_split_eq.sv > "$OUT/sources.sha256"
eq() {  # name defines...
  local n=$1; shift
  "$V" --binary -j ${VL_JOBS:-16} -O1 -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT "$@" \
    --top-module $TB $p/ot_hfd_coll_q_hard_v8g.sv $SRC $p/$TB.sv \
    -Mdir "$OUT/obj_$n" > "$OUT/$n.build.log" 2>&1 && "$OUT/obj_$n/V$TB" > "$OUT/$n.log" 2>&1
  rm -rf "$OUT/obj_$n"
  grep -E '^(LPF_EQ|LP_ACTIVITY|EQ_MISMATCH)' "$OUT/$n.log" 2>/dev/null | head -4 | sed "s/^/$n /"
}
if [ "$WHICH" = all ] || [ "$WHICH" = eq ]; then
  eq eq
  if grep -q '^LPF_EQ PASS' "$OUT/eq.log" 2>/dev/null && grep -Eq 'ariter_step_cycles=[1-9]' "$OUT/eq.log"; then echo "EQ PASS"; else echo "EQ FAIL"; rc=1; fi
  for m in "m_refnostep +define+OT_COLL_ARITER_MUT_NOSTEP" "m_leafedge +define+OT_ARITER_TAG_MUT_EDGE" "m_rlaneext +define+OT_COLL_RLANE_MUT_EXT"; do
    set -- $m; eq $1 $2
    if grep -q '^LPF_EQ FAIL' "$OUT/$1.log" 2>/dev/null; then echo "EQ_MUTANT $1 REJECTED"; else echo "EQ_MUTANT $1 SURVIVED"; rc=1; fi
  done
fi
if [ "$WHICH" = all ] || [ "$WHICH" = rs ]; then
  RSRC="$p/ot_hgi_coll_reduce_static.sv $p/ot_hgi_coll_safe_leaves.sv $p/ot_hgi_coll_pring_static.sv $p/ot_hfd_coll_q_hard_v5.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv"
  rs() { local n=$1; shift
    "$V" --binary -j ${VL_JOBS:-16} -O1 -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT "$@" \
      --top-module tb_hgi_coll_reduce_split_eq $SRC $p/tb_hgi_coll_reduce_split_eq.sv -Mdir "$OUT/obj_$n" > "$OUT/$n.build.log" 2>&1 \
      && "$OUT/obj_$n/Vtb_hgi_coll_reduce_split_eq" > "$OUT/$n.log" 2>&1
    rm -rf "$OUT/obj_$n"; grep -E '^RSPLIT' "$OUT/$n.log" 2>/dev/null | head -3 | sed "s/^/$n /"; }
  rs rs_eq
  if grep -q '^RSPLIT_EQ PASS' "$OUT/rs_eq.log" 2>/dev/null; then echo "RS PASS"; else echo "RS FAIL"; rc=1; fi
  for m in "rs_mtag -GSMUT_TAG=1" "rs_mbf16 -GSMUT_BF16=1" "rs_mext +define+OT_COLL_RLANE_MUT_EXT"; do
    set -- $m; rs $1 $2
    if grep -q '^RSPLIT_EQ FAIL' "$OUT/$1.log" 2>/dev/null; then echo "RS_MUTANT $1 REJECTED"; else echo "RS_MUTANT $1 SURVIVED"; rc=1; fi
  done
fi
if [ "$WHICH" = all ] || [ "$WHICH" = lp ]; then
  SIM=verilator VL_JOBS=${VL_JOBS:-16} bash $p/landed/ot_hfd_coll_${VAR}_lp_ars_bench.sh "$OUT/lp" > "$OUT/lp_bench.log" 2>&1; brc=$?
  cat "$OUT/lp_bench.log"; grep -h 'LP_ACTIVITY' "$OUT"/lp/mut0.log 2>/dev/null | sed 's/^/lp mut0 /'
  [ $brc -eq 0 ] || rc=1
  rm -rf "$OUT"/lp/obj*
fi
echo "COLL_LP_ARS_ALL_EXIT $rc"; exit $rc
