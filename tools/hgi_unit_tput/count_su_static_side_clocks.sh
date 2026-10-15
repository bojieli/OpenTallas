#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
python3 - <<'PY'
import os
from pathlib import Path
s=['physical/ref_tile/sfu_lane_ring3_rt/src/'+p for p in (Path(os.environ['DATA'])/'sources.f').read_text().splitlines() if 'vec_side_c12' not in p]
s+=['rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv','rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv']
cmd='read_verilog -sv '+' '.join(s)+'\nhierarchy -check -top ot_hbm_su_static_side\nproc\ncheck\nwrite_json '+os.environ['OUT']+'/side.json\n'
(Path(os.environ['OUT'])/'side.ys').write_text(cmd)
PY
yosys -Q -s "$OUT/side.ys" > "$OUT/side.log" 2>&1
python3 - <<'PY'
import os,json
from pathlib import Path
m=json.loads((Path(os.environ['OUT'])/'side.json').read_text())['modules']
top='ot_hbm_su_static_side';counts=[0]*6
clkmap=dict(zip(m[top]['ports']['clk']['bits'],range(6)))
def visit(name,clockmap,path):
 for key,c in m[name]['cells'].items():
  kind=c['type']
  if kind in ['$dff','$adff','$dffe','$adffe','$sdff','$sdffe']:
   clock=c['connections']['CLK'];assert len(clock)==1
   assert clock[0] in clockmap,(path,key,clock)
   counts[clockmap[clock[0]]]+=int(c['parameters']['WIDTH'],2)
  elif kind in m:
   childmap={}
   for port,definition in m[kind]['ports'].items():
    if definition['direction']=='input':
     for childbit,parentbit in zip(definition['bits'],c['connections'][port]):
      if parentbit in clockmap:childmap[childbit]=clockmap[parentbit]
   visit(kind,childmap,path+'/'+key)
  else:assert 'latch' not in kind,kind
visit(top,clkmap,top)
expected=[8521,3814,10813,10794,9139,13902]
assert counts==expected,(counts,expected)
assert max(counts)<=15000
summary=dict(root_register_sinks=counts,total_register_sinks=sum(counts),max_register_sinks=max(counts),clock_relation='6 roots related1:1 phase0;noaddededges',physical_timing_qualified=False)
(Path(os.environ['OUT'])/'clock_counts.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS actualSIDE6clockroots',counts,'total',sum(counts),'max',max(counts))
PY
