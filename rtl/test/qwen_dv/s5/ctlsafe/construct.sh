#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
yosys -Q -p "read_verilog -sv rtl/test/qwen_dv/s5/ctlsafe/ctl_gate2_snapshot.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv; hierarchy -check -top qfd_dv_s5_ctl; synth -top qfd_dv_s5_ctl -flatten -noabc -nofsm -noshare; dffunmap; clean; write_json $O/generic.json" > "$O/generic.log" 2>&1
python3 tools/qwen_dv/bound_math_netlist.py "$O/generic.json" --top qfd_dv_s5_ctl --name qfd_dv_s5_ctl_bounded4 --out "$O/qfd_dv_s5_ctl_bounded4.sv" --helpers "$O/qfd_dv_s5_ctl_bounded_helpers.sv" --record "$O/construction.json" > "$O/construct.log" 2>&1
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv $O/qfd_dv_s5_ctl_bounded4.sv $O/qfd_dv_s5_ctl_bounded_helpers.sv; hierarchy -check -top qfd_dv_s5_ctl_bounded4; synth -top qfd_dv_s5_ctl_bounded4 -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat; write_json $O/mapped.json; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
