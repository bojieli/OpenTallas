#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing --assert -Wno-fatal --top-module tb --Mdir obj -j 2 tb.sv bind_cells.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv > build.log 2>&1
for phase in 0 83 750;do ./obj/Vtb +PHASE=$phase +MUT=0 > "base_$phase.log" 2>&1;done
./obj/Vtb +PHASE=0 +MUT=1 > mutant.log 2>&1
cat base_0.log mutant.log
