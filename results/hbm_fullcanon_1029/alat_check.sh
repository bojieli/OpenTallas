#!/bin/bash
set -eu
cd "$(dirname "$0")"
Y=/home/ubuntu/.local/opentallas-tools/bin/yosys
MEM=$(find rtl -maxdepth 1 -name '*.sv' | grep -v -e '_core.sv$' -e '__wrap.sv$' -e '__fshell.sv$' -e face_reg | tr '\n' ' ')
for top in ot_hbm_su_pg_lanes4_core ot_hbm_su_pg_lane_exp_core ot_hbm_su_pg_lane_full_core; do
 for side in gold gate; do
  $Y -Q -q -l $top.$side.log -p "read_verilog -sv -lib macro_bb.v; read_verilog -sv -DSYNTHESIS $MEM $side/$top.sv; hierarchy -top $top; write_rtlil $top.$side.il" > $top.$side.stdout 2>&1
  python3 rtlil_canon.py $top.$side.il $top.$side.canon "\\$top"
 done
 cmp $top.gold.canon $top.gate.canon
 echo "$top DEFAULT_GRAPH_IDENTICAL"
 $Y -Q -q -l $top.a4.log -p "read_verilog -sv -lib macro_bb.v; read_verilog -sv -DSYNTHESIS $MEM gate/$top.sv; hierarchy -top $top -chparam ALAT 4 -chparam MLAT 5 -chparam WCOPY 1; proc; write_json $top.a4.json" > $top.a4.stdout 2>&1
 python3 - "$top.a4.json" <<'PY'
import json,sys
mods=json.load(open(sys.argv[1]))['modules'];seen=[]
for mn,m in mods.items():
 if mn.endswith('ot_hbm_su_static_lane_pinreg'):
  a=m['parameter_default_values']['ALAT'];seen.append(int(a,2))
assert seen and set(seen)=={4},seen
print(sys.argv[1],'ENABLED_ALAT4_ALL_LANES',len(seen))
PY
done
