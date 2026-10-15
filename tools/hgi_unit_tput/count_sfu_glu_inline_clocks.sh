#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
python3 - <<'PY'
from pathlib import Path
import os
s=['physical/ref_tile/sfu_lane_ring3_rt/src/'+p for p in (Path(os.environ['DATA'])/'sources.f').read_text().splitlines()]
s += [os.environ['DEPS']+'/rtl/hbm_accel/generic/peers/static_activation/ot_hbm_sm_aq_static.sv','rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_split.sv','rtl/hbm_accel/generic/peers/ot_hgi_sfu_glu_quant_inline.sv']
cmd='read_verilog -defer -sv '+' '.join(s)+'\nread_verilog -lib physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v\nhierarchy -check -top ot_hgi_sfu_glu_quant_inline\nproc\nmemory_map\ncheck\nwrite_json '+os.environ['OUT']+'/design.json\n'
(Path(os.environ['OUT'])/'design.ys').write_text(cmd)
PY
yosys -Q -s "$OUT/design.ys" > "$OUT/hierarchy.log" 2>&1
python3 - <<'PY'
from pathlib import Path
import os,json
m=json.loads((Path(os.environ['OUT'])/'design.json').read_text())['modules'];top='ot_hgi_sfu_glu_quant_inline';counts={};cmap={}
for port in ['clk_math','clk_control','clk_aq_core','clk_aq_delay','clk_aq_encode','clk_code']:
 for i,bit in enumerate(m[top]['ports'][port]['bits']):
  key=f'{port}[{i}]';counts[key]=0;cmap[bit]=key
macros=[0]
def walk(name,cmap):
 for c in m[name]['cells'].values():
  k=c['type']
  if k in ['$dff','$adff','$dffe','$adffe','$sdff','$sdffe']:
   clk=c['connections']['CLK'];assert len(clk)==1 and clk[0] in cmap
   counts[cmap[clk[0]]]+=int(c['parameters']['WIDTH'],2)
  elif k.startswith('ot_sram_'):
   clk=c['connections']['clk'];assert len(clk)==1 and clk[0] in cmap
   counts[cmap[clk[0]]]+=1;macros[0]+=1
  elif k in m:
   nxt={}
   for port,definition in m[k]['ports'].items():
    if definition['direction']=='input':
     for childbit,parentbit in zip(definition['bits'],c['connections'][port]):
      if parentbit in cmap:nxt[childbit]=cmap[parentbit]
   walk(k,nxt)
  else:assert 'latch' not in k,k
walk(top,cmap)
assert macros[0]==8,macros
assert len(counts)==11 and max(counts.values())<=15000,counts
record=dict(root_clock_sinks=counts,physical_macro_clock_pins_included=8,max_root=max(counts.values()),all_related1to1_phase0=True,physical_timing_qualified=False)
(Path(os.environ['OUT'])/'counts.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS11inlineclockroots',counts,'max',max(counts.values()))
PY
