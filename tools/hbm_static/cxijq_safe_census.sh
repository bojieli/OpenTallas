#!/bin/bash
set -euo pipefail
mkdir -p census
sha256sum rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv > census/source.sha256
yosys -Q -T -p 'read_verilog -sv -DSYNTHESIS rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv; chparam -set SAFE_GATHER 1 ot_hbm_su_static_cxport_ij_q; hierarchy -top ot_hbm_su_static_cxport_ij_q; synth -top ot_hbm_su_static_cxport_ij_q -noabc; stat; write_json census/synth.json' > census/yosys.log 2>&1
python3 - <<'CENSUS'
import json,collections
m=json.load(open('census/synth.json'))['modules']['ot_hbm_su_static_cxport_ij_q'];loads=collections.Counter();drivers={};names=collections.defaultdict(list)
for n,o in m['netnames'].items():
 for b in o['bits']:
  if isinstance(b,int):names[b].append(n)
for n,c in m['cells'].items():
 for p,bits in c['connections'].items():
  if c['port_directions'][p]=='input':loads.update(b for b in bits if isinstance(b,int))
  else:
   for b in bits:drivers[b]=(n,c['type'])
r={'celltypes':dict(collections.Counter(c['type'] for c in m['cells'].values())), 'top_fanout':[{'bit':b,'loads':v,'driver':drivers.get(b),'names':names[b][:4]}for b,v in loads.most_common(30)]}
json.dump(r,open('census/fanout.json','w'),indent=2)
print(json.dumps(r,indent=2))
CENSUS
