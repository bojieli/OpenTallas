#!/bin/bash
set -eu
cd "${1:?staged packet}"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --cc --exe --build -j 2 -Wno-fatal --top-module tb_landing_phase tb_landing_phase.sv ot_dp_clk_landing.sv ot_meso_fifo.sv run.cpp --Mdir obj > build.log 2>&1
for phase in 0 1000 83000 208000 416500 625000 750000 832000; do
 ./obj/Vtb_landing_phase "$phase" > "phase_$phase.log" 2>&1
 cat "phase_$phase.log"
done
grep -Eq 'wrongedge_mismatches=[1-9][0-9]*' phase_83000.log
grep -Eq 'wrongphase_mismatches=[1-9][0-9]*' phase_83000.log
