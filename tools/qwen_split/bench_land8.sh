#!/bin/bash
# QW-LAND8 10-19: behavioural bench of the D8 hop-0 landing (rtl/qwen_split/qfd_land8.sv) through one class master of
# physical/qwen_fwd_lane/qfd_land8_masters.sv -- Verilator 5.050 (the closure daemon's version).
# usage: bench_land8.sh <pass|sel|naive|vld|encomb|k3|wsel|rsel> <work dir> <master module> <W>
#   pass: tools/qwen_split/bench_land8.py lanes (72 lanes, K 0..15, 8 phases, 3 release orders, paired / source-only /
#         receiver-only restarts), arbitrary initial state, 3 seeds: every seed must print LAND8_BENCH PASS.
#   others: the same bench on the RTL built with one OT_QFD_LAND8_MUT_* define; must print LAND8_BENCH FAIL.
set -u
mode=$1; O=$2; M=$3; W=$4
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
DEF=
case $mode in
  pass) ;; sel) DEF=+define+OT_QFD_LAND8_MUT_SEL ;; naive) DEF=+define+OT_QFD_LAND8_MUT_NAIVE ;;
  vld) DEF=+define+OT_QFD_LAND8_MUT_VLD ;; encomb) DEF=+define+OT_QFD_LAND8_MUT_ENCOMB ;;
  k3) DEF=+define+OT_QFD_LAND8_MUT_K3 ;; wsel) DEF=+define+OT_QFD_LAND8_MUT_WSEL ;; rsel) DEF=+define+OT_QFD_LAND8_MUT_RSEL ;;
  *) echo "bad mode $mode"; exit 2 ;;
esac
python3 tools/qwen_split/bench_land8.py "$M" "$W" "$O/tb.sv" || { echo GEN_FAILED; exit 2; }
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY \
  --x-assign unique --x-initial unique --top-module tb $DEF -Mdir "$O/obj" -o tb "$O/tb.sv" \
  physical/qwen_fwd_lane/qfd_land8_masters.sv rtl/qwen_split/qfd_land8.sv rtl/hdc/ot_hdc_cg.sv > "$O/build.log" 2>&1 || {
  echo BUILD_FAILED; tail -20 "$O/build.log"; exit 2; }
rc=0
for seed in 11 2026 777; do
  "$O/obj/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$O/bench_$seed.log" 2>&1
  echo "seed $seed: $(grep -E 'LAND8_BENCH' "$O/bench_$seed.log")"
  grep -E 'LAND8_(MISMATCH|FAULT)' "$O/bench_$seed.log" | head -3
  grep -q 'LAND8_BENCH PASS' "$O/bench_$seed.log" || rc=1
done
if [ $rc = 0 ]; then echo "LAND8_BENCH_ALL PASS ($mode $M)"; else echo "LAND8_BENCH_ALL FAIL ($mode $M)"; fi
exit $rc
