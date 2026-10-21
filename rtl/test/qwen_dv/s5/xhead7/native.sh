#!/bin/bash
# ASAP7 native mapping of the bounded xhead leaf (recipe = CTL repair4 native4) + strict mapped census (<=32, reset incl.)
# bash rtl/test/qwen_dv/s5/xhead7/native.sh OUT   (sources: rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded{,_helpers,_leaf}.sv)
set -euo pipefail
O=$1; mkdir -p "$O"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded_helpers.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead2.sv; hierarchy -check -top qfd_dv_s5_xhead2; synth -top qfd_dv_s5_xhead2 -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py "$O/mapped.v" > "$O/census.json"
python3 - "$O/census.json" <<'PY'
import json,sys;d=json.load(open(sys.argv[1]));m=d['metrics']
print('NATIVE', d['verdict'], 'over32', d['nonclock_drivers_over32'], 'max', d['max_nonclock_loads'], 'rst_n', d['rst_n_loads'],
 'depth_ps', m.get('depth_ps'), 'levels', m.get('depth_levels'), 'in_reg', m.get('in_to_reg_levels'), 'reg_out', m.get('reg_to_out_levels'), 'in_out', m.get('in_to_out_bits'))
PY
grep -iE "chip area|cells$" "$O/mapped.log" | tail -3 || true
gzip -kf "$O/mapped.v"
