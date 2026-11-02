#!/bin/bash
# Approved source-only normal-profile candidate: never floorplan/PLACE/STA/route/LEC.
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl
python3 -I /work/partition_ir.py patch /OpenROAD-flow-scripts/flow/scripts
export OT_DEFER_PARTITION_IR=1
mapfile -t synth_libs < <(find /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -maxdepth 1 -name 'asap7sc7p5t_*RVT_*.lib*' ! -name '*FAKE*')
python3 -I /work/sdc_lint.py /work --liberty "${synth_libs[@]}" > /work/sdc_lint.log 2>&1
python3 -I /work/rtl_lint.py /work
python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1
python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 synth
python3 -I /work/adder_map_dontuse.py check --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --netlist /work/run/results/asap7/dp_tt_ctlm/base/1_2_yosys.v --report /work/dont_use_check.json
