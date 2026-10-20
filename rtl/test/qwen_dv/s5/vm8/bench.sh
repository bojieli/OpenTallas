#!/bin/bash
# QW-SUVM8 lockstep bench (fleet, Verilator 5.050): bench.sh OUT [0|coll|wpri|bsel]
set -u
O=$1; M=${2:-0}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
D=""; case $M in 0) ;; coll) D="+define+OT_S8_MUT_COLL";; wpri) D="+define+OT_S8_MUT_WPRI";; bsel) D="+define+OT_S8_MUT_BSEL";; *) echo "unknown M $M"; exit 2;; esac
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 $D --top-module tb_vm8 \
  rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8.sv \
  rtl/test/qwen_dv/s5/vm8/tb_vm8.sv -Mdir "$O/obj_$M" > "$O/build_$M.log" 2>&1 || { echo BUILD FAIL; tail -40 "$O/build_$M.log"; exit 1; }
"$O/obj_$M/Vtb_vm8" > "$O/run_$M.log" 2>&1
cat "$O/run_$M.log" | tail -12
