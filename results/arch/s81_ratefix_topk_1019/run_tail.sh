#!/bin/bash
# S81-RATEFIX: topk_final drain-window (TAIL_BUDGET) sweep on the successor quarter RTL (INDEXED13 + FIFO_SRAM + P192 +
# SUCC + RST64 + FAN32 = the s81dvbk_sq_succ2 / _reg kit defines), Verilator 5.050.  Run from the source root.
set -uo pipefail
O=${1:?out}; mkdir -p "$O"; S=results/arch/s81_topk_final_1019/bench; H=results/arch/s81_ratefix_topk_1019
DEF="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_RST64 -DOT_S81PH_SEL_FAN32"
D=""
for c in indexed13 indexed13_ties indexed13_ninf indexed13_zeros; do
  for t in ${TAILS:-280 300 310 320 330 340 360 640}; do python3 $H/mk_tail.py $S/$c $O/${c}_t$t $t >/dev/null && D="$D $O/${c}_t$t"; done
done
VL_EXTRA="$DEF" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build" $D
for d in $D; do echo "$(basename $d) $(head -c 160 $d/verdict.txt)"; done | tee $O/summary.txt
