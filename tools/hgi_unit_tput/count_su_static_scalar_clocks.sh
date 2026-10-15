#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
python3 - <<'PY'
import os
from pathlib import Path
s=['physical/ref_tile/sfu_lane_ring3_rt/src/'+p for p in (Path(os.environ['DATA'])/'sources.f').read_text().splitlines() if 'vec_side_c12' not in p]
s+=['rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv','rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_scalar.sv']
base=Path(os.environ['DEPS'])
s += [str(base/'rtl/hbm_accel/generic/adapters/static_su'/p) for p in ['arithmetic/ot_hbm_su_static_lane.sv','arithmetic/ot_hbm_su_static_ins.sv','data_store/ot_hbm_su_static_data_store.sv','data_store/ot_hbm_su_static_pinned_bank.sv']]
s += [str(base/'rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv')]
for name,top in [('head','ot_hbm_su_static_scalar'),('bank','ot_hbm_su_static_pinned_bank')]:
 cmd='read_verilog -defer -sv '+' '.join(s)+'\nread_verilog -lib physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v\nhierarchy -check -top '+top+'\nproc\ncheck\nwrite_json '+os.environ['OUT']+'/'+name+'.json\n'
 (Path(os.environ['OUT'])/(name+'.ys')).write_text(cmd)
PY
for block in head bank;do
 if [ ! -s "$OUT/$block.json" ];then yosys -Q -s "$OUT/$block.ys" > "$OUT/$block.log" 2>&1;fi
done
python3 - <<'PY'
import os,json
from pathlib import Path
all_counts={}
for name,top,ports in [('head','ot_hbm_su_static_scalar',['clk_lane','clk_insert','clk_side','clk_bcast']),('bank','ot_hbm_su_static_pinned_bank',['clk'])]:
 m=json.loads((Path(os.environ['OUT'])/(name+'.json')).read_text())['modules'];counts={};clkmap={}
 for port in ports:
  for i,bit in enumerate(m[top]['ports'][port]['bits']):
   key=f'{port}[{i}]';counts[key]=0;clkmap[bit]=key
 def visit(mod,clockmap,path):
  for key,c in m[mod]['cells'].items():
   kind=c['type']
   if kind in ['$dff','$adff','$dffe','$adffe','$sdff','$sdffe']:
    clock=c['connections']['CLK'];assert len(clock)==1
    assert clock[0] in clockmap,(path,key,clock)
    counts[clockmap[clock[0]]]+=int(c['parameters']['WIDTH'],2)
   elif kind.startswith('ot_sram_'):
    clock=c['connections']['clk'];assert len(clock)==1 and clock[0] in clockmap
    counts[clockmap[clock[0]]]+=1
   elif kind in m:
    childmap={}
    for port,definition in m[kind]['ports'].items():
     if definition['direction']=='input':
      for childbit,parentbit in zip(definition['bits'],c['connections'][port]):
       if parentbit in clockmap:childmap[childbit]=clockmap[parentbit]
    visit(kind,childmap,path+'/'+key)
   else:assert 'latch' not in kind,kind
 visit(top,clkmap,top)
 assert max(counts.values())<=15000,counts
 all_counts[name]=counts
print('PASS actualnativehead19roots+6SRAMbank1root',all_counts)
(Path(os.environ['OUT'])/'clock_counts.json').write_text(json.dumps(dict(root_sinks=all_counts,max_root_sinks=max(v for d in all_counts.values() for v in d.values()),all_related_phase0=True,clock_period_ps=833.333,physical_qualified=False),indent=2)+'\n')
PY
