#!/bin/bash
set -euo pipefail
cd /work
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 - <<'LIB'
from pathlib import Path
import gzip
root=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
parts=[]
for family in ('INVBUF','SEQ','SIMPLE','AO','OA'):
 for p in root.glob('asap7sc7p5t_'+family+'_RVT_TT_nldm*'):
  t=(gzip.open(p,'rt') if p.suffix=='.gz' else p.open()).read()
  parts.append(t[t.index('{')+1:t.rfind('}')])
Path('cells.lib').write_text('library(ot_start) {\n'+'\n'.join(parts)+'\n}\n')
LIB
cat > map.ys <<'YS'
read_verilog -sv start_stages.sv ot_dp_clk_landing_ca.sv
hierarchy -check -top ot_die_start_stages
synth -top ot_die_start_stages -noabc
dfflibmap -liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
abc -liberty cells.lib -dont_use *xp* -dont_use *x1p* -dont_use SDF* -dont_use ICG*
setattr -mod -unset keep_hierarchy
flatten
opt_clean
clean
delete t:$scopeinfo
read_liberty -lib cells.lib
check -assert
stat -liberty cells.lib
write_json mapped.json
write_verilog -noattr mapped.v
YS
yosys -ql map.log map.ys
python3 - <<'PY'
import json,collections
p=json.load(open('mapped.json'))['modules']['ot_die_start_stages']
s=json.load(open('start_stages.json'))
c=collections.Counter(x['type'] for x in p['cells'].values())
ff=sum(v for k,v in c.items() if k.startswith(('DFF','SDFF')))
r={'scope':'CA4 mapping inventory only; old global reset and 30 part-stars remain held, no route','mapped_cells':len(p['cells']),'mapped_flops':ff,'planned_flops':s['counts']['flops'],'cell_types':dict(c),'unmapped_types':[k for k in c if '_ASAP7_' not in k]}
json.dump(r,open('summary.json','w'),indent=1)
print(json.dumps(r))
PY
