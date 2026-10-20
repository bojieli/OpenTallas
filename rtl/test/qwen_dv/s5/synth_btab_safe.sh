#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
# Run in the exact gate image; synthesize only, no layout gate.
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/merge_btab_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v; read_verilog -sv rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv; hierarchy -check -top qfd_dv_s5_btab_safe; synth -top qfd_dv_s5_btab_safe -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat; write_json $O/mapped.json; write_verilog -noattr $O/mapped.v" > "$O/synth.log" 2>&1
python3 rtl/test/qwen_dv/s5/btab_safe_census.py "$O/mapped.json" > "$O/census.json"
