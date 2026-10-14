#!/bin/bash
set -eu
out=$1
mkdir -p "$out"
cp tools/s81_ph/fixtures/capc_fifo_orig_9c12f4d15.sv "$out/original_fifo.sv"
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_capc_local_ctrl -Mdir "$out/obj" -o sim rtl/common/ot_ratio_cdc_fifo.sv "$out/original_fifo.sv" tools/s81_ph/tb_capc_local_ctrl.sv > "$out/build.log" 2>&1
for phase in 0 1 2 3; do "$out/obj/sim" +PHASE=$phase > "$out/phase_$phase.log" 2>&1 & done
wait
for phase in 0 1 2 3; do grep '^SS_CTRL_EQ PASS.*mismatches=0' "$out/phase_$phase.log"; done
