#!/bin/bash
# TOKc-SEGCAL 10-22: the generated HP13 landed-parent bench (die parameters: NU 4, OPSEG, CTX, INIT, PRIVATE_CALR, F16WTN,
# XPF21; random stimulus 3000 cycles; flat qfd_tt_ctlm_dv_lpf_hp13 vs qfd_tt_ctlm_dv_lpf_hp13_lp; MUT 0 PASS, MUT 1 2 4 5
# FAIL; lp.py region audit PASS, unland mutant audit FAIL) on the materialized die-form sources with the go port.
#   run_hp13_lp_bench.sh DUT_ROOT OUT          (fleet, Verilator 5.050)
set -u
DUT=$(readlink -f "$1"); OUT=$(readlink -f "$2"); mkdir -p "$OUT"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
LP_ROOT=$DUT SIM=verilator VL_JOBS=8 bash "$DUT/rtl/qwen_dv/headprep13/lp/qfd_tt_ctlm_dv_lpf_hp13_lp_bench.sh" "$OUT" 2>&1 | tee "$OUT/bench.out"
