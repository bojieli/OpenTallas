#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-qc-slectl/proof
iverilog -g2012 -s tb -o good.vvp ot_meso_fifo.sv ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv wrapper.sv tb.sv
vvp good.vvp > good.log
iverilog -g2012 -s tb -o mutant.vvp ot_meso_fifo.sv ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv mutant.sv tb.sv
if vvp mutant.vvp > mutant.log; then echo MUTANT_NOT_CAUGHT; exit 1; fi
echo LOCKSTEP_PASS_MUTANT_CAUGHT
