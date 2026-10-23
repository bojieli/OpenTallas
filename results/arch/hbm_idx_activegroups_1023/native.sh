#!/bin/bash
set -euo pipefail
docker run --rm -v "$PWD:/src" -w /src openroad/orfs:asap7lock yosys -l native.log -s results/arch/hbm_idx_activegroups_1023/native.ys >native.stdout 2>&1
python3 - <<'PY2'
import json
m=json.load(open('native.json'))['modules']['ot_hbm_idx_selector_static_sel'];bits=set(m['ports']['in_line']['bits'][1184:]);sinks=[]
for n,c in m['cells'].items():
 for p,b in c['connections'].items():
  if c['port_directions'].get(p)=='input' and bits.intersection(b):sinks.append((n,p,len(bits.intersection(b))))
mac=[n for n,c in m['cells'].items() if c['type']=='ot_sram_1r1w_256x256_m2_r2c2']
r=dict(upper_input_bits=1184,upper_input_cell_sinks=sinks,sram_count=len(mac),sram_cells=mac,scope='elaborated optimized generic native; no timing/fanout qualification')
json.dump(r,open('native_summary.json','w'),indent=2);print(r)
assert not sinks and len(mac)==6
PY2
