#!/bin/bash
# QW-VM8SPLIT lockstep bench (fleet, Verilator 5.050): bench.sh OUT [0|coll|wpri|bsel] [SPLIT 0|1]
set -u
O=$1; M=${2:-0}; S=${3:-0}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
D=""; case $M in 0) ;; coll) D="+define+OT_S8_MUT_COLL";; wpri) D="+define+OT_S8_MUT_WPRI";; bsel) D="+define+OT_S8_MUT_BSEL";; *) echo "unknown M $M"; exit 2;; esac
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 $D +define+VM8X_SPLIT=$S --top-module tb_vm8x \
  rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv \
  rtl/test/qwen_dv/s5/vm8x/tb_vm8x.sv -Mdir "$O/obj_${M}_$S" > "$O/build_${M}_$S.log" 2>&1 || { echo BUILD FAIL; tail -40 "$O/build_${M}_$S.log"; exit 1; }
"$O/obj_${M}_$S/Vtb_vm8x" > "$O/run_${M}_$S.log" 2>&1
cat "$O/run_${M}_$S.log" | tail -12
