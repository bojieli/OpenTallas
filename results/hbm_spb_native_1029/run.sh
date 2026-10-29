#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
python3 spb0_native.py bound_spb0_fixture.sv actual_spb0_graph.json contract.json transformed
iverilog -g2012 -s tb -o transport_tb transformed/ot_hbm_spb0_regs.sv transformed/bound_spb0_fixture.sv sim_models.sv tb.sv
for mutant in 0 1 2; do vvp transport_tb +MUT=$mutant; done
