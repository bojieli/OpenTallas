#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
python3 tools/qwen_dv/bound_math_netlist.py ../construct_rst1/generic.json --load-cap 16 --top qfd_dv_s5_ctl --name qfd_dv_s5_ctl_bounded4_rst1 --out "$O/qfd_dv_s5_ctl_bounded4_rst1.sv" --helpers "$O/qfd_dv_s5_ctl_bounded_helpers.sv" --record "$O/construction.json" > "$O/construct.log" 2>&1
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv $O/qfd_dv_s5_ctl_bounded4_rst1.sv $O/qfd_dv_s5_ctl_bounded_helpers.sv; hierarchy -check -top qfd_dv_s5_ctl_bounded4_rst1; synth -top qfd_dv_s5_ctl_bounded4_rst1 -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat; write_json $O/mapped.json; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
