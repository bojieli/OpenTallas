#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair3.sv rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair3_helpers.sv rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair3_leaf.sv; hierarchy -check -top qfd_dv_s5_ctl_repair3_leaf; synth -top qfd_dv_s5_ctl_repair3_leaf -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_json $O/mapped.json; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
