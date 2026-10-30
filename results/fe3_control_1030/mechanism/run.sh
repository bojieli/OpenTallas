#!/bin/bash
set -eu
B=$(cd "$(dirname "$0")" && pwd)
W=$(git -C "$B" rev-parse --show-toplevel)
cd "$B"
COMMON=("$W/rtl/common/ot_dp_clk_landing.sv" "$W/rtl/common/ot_dp_clk_landing_ca.sv" "$W/rtl/common/ot_meso_fifo.sv")
iverilog -g2012 -s tb -o sim tb.sv baseline_controls.sv candidate_controls.sv ot_dp_cells.sv "${COMMON[@]}"
for phase in 80 166 333 500 666;do vvp sim +PHASE=$phase;done
for mut in wrongK missingstage wrongreset_depth;do
 d=mutants/$mut
 iverilog -g2012 -s tb -o "$d/sim" "$d/tb.sv" baseline_controls.sv "$d/candidate_controls.sv" ot_dp_cells.sv "${COMMON[@]}"
 if vvp "$d/sim" +PHASE=166 > "$d/recheck.log" 2>&1;then echo "MUTANT SURVIVED $mut";exit 1;fi
 grep -q FATAL "$d/recheck.log"
 echo "MUTANT CAUGHT $mut"
done
