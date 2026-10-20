#!/usr/bin/env bash
# PL-COLLQ 10-18: (1) flat-expansion equivalence ot_hfd_coll_q3_hard_v8x #(NLINK 2, TP 192) == ot_hfd_coll_q3_lpf (random lockstep, every
# output every cycle) and (2) the generated landed-parent bench (lockstep flat vs ot_hfd_coll_q3_lp, MUT 1/2/4, audit,
# unland).  FLEET ONLY:  LP_ROOT=<tree> bash rtl/hbm_accel/generic/collective/p2p/landed/run_q3_lp_all.sh OUT
set -u
cd "${LP_ROOT:?LP_ROOT}"
OUT=$(realpath -m "${1:?OUT}"); mkdir -p "$OUT"; rc=0
p=rtl/hbm_accel/generic/collective/p2p
SRC=$(python3 -c "import json;s=json.load(open('results/arch/landed_parent_1018/collq/spec_q3.json'));print(' '.join(s['sources']+s['child_sources']))")
verilator --binary -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hfd_coll_q3_lpf_eq \
  $p/ot_hfd_coll_q_hard_v8g.sv $SRC $p/tb_hfd_coll_q3_lpf_eq.sv -Mdir "$OUT/obj_eq" > "$OUT/eq_build.log" 2>&1 \
  && "$OUT/obj_eq/Vtb_hfd_coll_q3_lpf_eq" > "$OUT/eq.log" 2>&1
grep -q '^LPF_EQ PASS' "$OUT/eq.log" 2>/dev/null && echo "EQ PASS" || { echo "EQ FAIL (see $OUT/eq.log / eq_build.log)"; rc=1; }
SIM=verilator bash $p/landed/ot_hfd_coll_q3_lp_bench.sh "$OUT/lp" > "$OUT/lp_bench.log" 2>&1; brc=$?
cat "$OUT/lp_bench.log"; [ $brc -eq 0 ] || rc=1
echo "Q3_LP_ALL_EXIT $rc"; exit $rc
