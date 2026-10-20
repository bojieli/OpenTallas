#!/bin/bash
set -euo pipefail
O=/work/native
mkdir -p "$O"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
for depth in 2 3; do
  yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv -D SYNTHESIS rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv rtl/test/qwen_dv/reset_forest_lead_coupon.sv; chparam -set DEPTH $depth reset_forest_lead_coupon; hierarchy -check -top reset_forest_lead_coupon; synth -top reset_forest_lead_coupon -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/depth$depth.v" > "$O/depth$depth.log" 2>&1
  python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py "$O/depth$depth.v" > "$O/depth$depth.json"
  python3 -c "import json; d=json.load(open('$O/depth$depth.json')); print('DEPTH$depth',d['verdict'],'max',d['max_nonclock_loads'],'over32',d['nonclock_drivers_over32']); assert d['nonclock_drivers_over32']==0"
done
