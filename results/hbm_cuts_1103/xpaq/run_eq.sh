#!/bin/bash
# DIE-HBM-61/CUTS: YCUT lockstep EQ + mutants (iverilog). Run from the repo root: results/hbm_cuts_1103/xpaq/run_eq.sh OUT [GOLD_REV]
set -u; OUT=${1:?}; GOLD=${2:-3465966986}; mkdir -p "$OUT"
git show $GOLD:physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv | sed 's/^module ot_hbm_xp_aq_tree13 /module gold_ot_hbm_xp_aq_tree13 /' > "$OUT/gold_tree13.sv"
F="results/hbm_cuts_1103/xpaq/tb_aq_tree13_ycut.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv rtl/hdc/ot_hdc_delay.sv $OUT/gold_tree13.sv"
for m in 0 1 2 3; do
  iverilog -g2012 -o "$OUT/sim$m" -Ptb.YMUT=$m $F $(cat "$OUT/extra.f" 2>/dev/null) > "$OUT/build$m.log" 2>&1 || { echo "BUILD FAIL $m"; cat "$OUT/build$m.log" | head; continue; }
  vvp -n "$OUT/sim$m" | grep -E "YCUT_" | tail -6
done
