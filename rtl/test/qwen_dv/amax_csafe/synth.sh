#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/amax_csafe/merge_lib.py "$FLOW" "$out/cells.lib"
for nu in 1 4; do
 top=qfd_dv_amax_csafe_n${nu}m0
 yosys -Q -p "read_liberty -lib $out/cells.lib; read_verilog -sv generated/qfd_dv_amax_mu_csafe.sv; hierarchy -check -top $top; synth -top $top -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $out/cells.lib; clean; stat; write_json $out/n$nu.json; write_verilog -noattr $out/n$nu.v" > "$out/n$nu.log" 2>&1
done
