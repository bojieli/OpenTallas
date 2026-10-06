#!/usr/bin/env python3
"""Extract actual full32 mapped local registers for finite parent placement.

This emits instance/pin bindings, never a placeholder macro or clock closure.
Run beside retained objects on the compute host; bulk pin data stays there.
"""
import hashlib,json,re,sys
from collections import Counter
from pathlib import Path
src,layout,out=map(Path,sys.argv[1:]);assert not out.exists()
r=json.loads((src/'result.json').read_text());assert r['exit']==0 and r['shape']['NSM']==32
mapped=next(src.glob('work/orfs/results/asap7/*/base/1_2_yosys.v'))
sha=hashlib.sha256(mapped.read_bytes()).hexdigest()
assert sha==r['artifacts'][str(mapped.relative_to(src))]['sha256']
g=json.loads(layout.read_text());slots={int(x['name'][2:]):x for x in g['retained_claims'] if re.fullmatch(r'sm\d+',x['name'])}
assert set(slots)==set(range(32))
coll=next(x for x in g['retained_claims'] if x['name']=='hb_coll')
rows=[dict(caller=s,actual_allocation=slots[s],register_kinds=Counter(),masters=Counter(),clock_connections=Counter(),pins=[]) for s in range(32)]
pattern=re.compile(r'^\s*(DFF\w+)\s+\\(g_on\.g_sm_caller\[(\d+)\]\.([^\s]+))\s+\($')
with mapped.open() as f:
 for l in f:
  m=pattern.match(l)
  if not m:continue
  master,inst,s,reg=m.groups();s=int(s);assert s<32
  body=[]
  for z in f:
   if z.strip()==');':break
   body.append(z)
  pins=dict(re.findall(r'\.(\w+)\(([^)]+)\)', ''.join(body)))
  assert pins.get('CLK')=='clk_sm',(inst,pins)
  kind=reg.split('[')[0].split('$')[0]
  row=rows[s];row['register_kinds'][kind]+=1;row['masters'][master]+=1;row['clock_connections'][pins['CLK']]+=1
  row['pins'].append(dict(instance=inst,master=master,pins=pins))
for row in rows:
 assert row['register_kinds']['c_data']==4096,row['register_kinds']
 assert row['register_kinds']['vr']==4096,row['register_kinds']
 assert row['register_kinds']['c_count']==8 and row['register_kinds']['c_mode']==1
 assert row['register_kinds']['bst']>=2,row['register_kinds']
out.mkdir(parents=True)
with (out/'actual_register_pins.jsonl').open('w') as f:
 for row in rows:
  for x in row.pop('pins'):f.write(json.dumps(dict(caller=row['caller'],**x))+'\n')
summary=dict(source_commit=r['source_commit'],mapped_sha256=sha,layout_sha256=hashlib.sha256(layout.read_bytes()).hexdigest(),callers=rows,
 request_register_bits=32*4096,response_register_bits=32*4096,distributed_vector_bits=32*8192,
 root_clock='clk_sm',actual_register_CLK_connections=True,propagated_root_insertion_measured=False,
 finite_endpoint_mux_allocation=coll,bulk_actual_pin_map=str(out/'actual_register_pins.jsonl'),
 bulk_pin_map_sha256=hashlib.sha256((out/'actual_register_pins.jsonl').read_bytes()).hexdigest(),
 shared_spine_tracks_assumed_free=0,external_perimeter_equivalent=False,physical_qualified=False,adopted=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(mapped_registers=sum(sum(x['masters'].values()) for x in rows),source_local_callers=32,distributed_vector_bits=32*8192,actual_clk_sm=True)))
