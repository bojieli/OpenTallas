#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
out=$(mkdir -p "$1" && cd "$1" && pwd)
yosys=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
col=$root/rtl/hbm_accel/generic/adapters/static_su/collport
macro=$root/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
for name in legacy physical;do
 top=ot_hbm_su_sfustore_hw_bank
 [ "$name" != physical ] || top=ot_hbm_su_sfustore_hw_bank_if
 "$yosys" -Q -T -p "read_verilog -lib $macro; read_verilog -sv $col/ot_hbm_su_static_sfustore_hw.sv $col/ot_hbm_su_sfustore_hw_bank_if.sv $root/rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_data_store.sv; hierarchy -top $top; tcl $root/physical/common_flow/ot_keep_regs.tcl; flatten; opt; techmap; opt; write_json $out/$name.json; stat" > "$out/$name.log" 2>&1
done
python3 - "$out" <<'PY'
from pathlib import Path
import json,sys
r=Path(sys.argv[1]);d={}
for name in ('legacy','physical'):
 j=json.load(open(r/(name+'.json')));m=j['modules']['ot_hbm_su_sfustore_hw_bank'+('_if' if name=='physical' else '')]
 cells=m['cells'];ff={k:v for k,v in cells.items() if 'DFF' in v['type'].upper()}
 d[name]=dict(ff=len(ff),macro=sum(v['type']=='ot_sram_1r1w_128x256_m1_r2c2' for v in cells.values()),cells=len(cells))
assert d['legacy']['macro']==d['physical']['macro']==1,d
d['added_ff_per_bank']=d['physical']['ff']-d['legacy']['ff'];d['added_ff_per_tile']=16*d['added_ff_per_bank']
(r/'count.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(d))
PY
