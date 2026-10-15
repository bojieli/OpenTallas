#!/usr/bin/env bash
set -euo pipefail
OUT=/tmp/hbm-static-ring-root-count-1014
mkdir -p "$OUT"
P=rtl/hbm_accel/generic/collective/p2p
for top in ot_hgi_coll_pring_static ot_hgi_coll_pring_static_state_lane ot_hgi_coll_pring_static_add_lane; do
 yosys -Q -T -p "read_verilog -sv $P/ot_hgi_coll_pring_static.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv; hierarchy -top $top; proc; memory_map; opt; write_json $OUT/$top.json" > "$OUT/$top.log" 2>&1
done
python3 - <<'PY'
import json,pathlib
p=pathlib.Path('/tmp/hbm-static-ring-root-count-1014')
out={}
for f in p.glob('*.json'):
 v=json.loads(f.read_text())['modules']
 def count(mod):
  n=0
  for cell in v[mod]['cells'].values():
   typ=cell['type']
   if typ in v:n+=count(typ)
   elif 'dff' in typ.lower():n+=int(cell['parameters']['WIDTH'],2)
  return n
 m=v[f.stem]
 own=sum(int(c['parameters']['WIDTH'],2) for c in m['cells'].values() if 'dff' in c['type'].lower())
 out[f.stem]={'own_register_bits':own,'all_register_bits':count(f.stem),'status':'Yosys proc/memory_map/opt register count; not mapped CTS/timing evidence'}
(p/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
PY
