#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
iverilog -g2012 -s tb -o good.vvp actual_old_helpers.sv ot_meso_fifo.sv ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv wrapper.sv tb.sv
vvp good.vvp > good.log
iverilog -g2012 -s tb -o mutant.vvp actual_old_helpers.sv ot_meso_fifo.sv ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv mutant.sv tb.sv
if vvp mutant.vvp > mutant.log; then echo MUTANT_NOT_CAUGHT; exit 1; fi
echo ACTUAL_FW632_LOCKSTEP_PASS_MUTANT_CAUGHT
