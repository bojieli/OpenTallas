#!/bin/bash
set -euo pipefail
# Run through ot-run from a staged directory containing these source/results files.
iverilog -g2012 -s tb -o ring_sim ot_vms_rstop_static.sv reference.sv mutant.sv tb.sv
vvp ring_sim
iverilog -g2012 -s status_tb -o status_sim ot_vms_status_static.sv status_reference.sv status_mutant.sv status_tb.sv
vvp status_sim
yosys -Q -T -p 'read_verilog -sv ot_vms_rstop_static.sv; chparam -set LOCAL_CTRL_REPLICAS 1 ot_vms_rstop_static; hierarchy -top ot_vms_rstop_static; proc; flatten; opt; write_json replicas.json' > synthesis.log
python3 replicas_check.py replicas.json
