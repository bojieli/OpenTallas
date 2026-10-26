#!/bin/bash
set -eu
P=$(realpath -m "${1:?usage: run_sfu.sh OUTPUT}")
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
for M in clean mutant; do
 test ! -e "$P/run_$M.log" || { echo "Use a fresh OUTPUT to preserve prior verdicts"; exit 2; }
 D=; test "$M" = clean || D=+define+OT_S8_CROM_ALIGN_MUTANT
 verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 $D --top-module tb_s8_memalign_sfu -f "$P/sources.f" "$P/qfd_dv_head_safe1.sv" "$P/tb_s8_memalign_sfu.sv" -Mdir "$P/obj_$M" > "$P/build_$M.log" 2>&1
 "$P/obj_$M/Vtb_s8_memalign_sfu" > "$P/run_$M.log" 2>&1
 tail -10 "$P/run_$M.log"
done
grep -q 'S8_MEMALIGN_SFU PASS' "$P/run_clean.log"
grep -q 'S8_MEMALIGN_SFU FAIL' "$P/run_mutant.log"
