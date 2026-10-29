#!/usr/bin/env python3
"""Unadopted BTAB compact core delta, retaining parent partitions and origins."""
import json,sys,copy
from pathlib import Path
src,dst=map(Path,sys.argv[1:3]);p=json.loads(src.read_text());before=copy.deepcopy(p)
W,H=259.2,138.24;pin=[134.7,19.98];rows=[]
for name,t in p['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c['module']!='qfd_dv_s8x_btab':continue
  old=copy.deepcopy(c);c['outline_um']=[W,H];c['pins_file']='cores/su/qfd_dv_s8x_btab_pins_compactblock.json'
  c['note']='BTAB compact2x2 CANDIDATE: pins/outline changed, old views invalid; frozen planned tree candidate; current QC clock trial unchanged'
  origin=c['origin_um'];matches=[]
  for tap in t['clock']['taps']:
   if tap.get('name')==c['inst']+'.ck':
    prev=copy.deepcopy(tap);tap['xy']=[round(origin[0]+pin[0],6),round(origin[1]+pin[1],6)]
    tap['insertion_ps']=250;tap['insertion_ff_ps']=202.5
    tap['budget_owner']='BTAB compact frozen planned tree CANDIDATE; routed related-pair TT/FF actual view pending'
    matches.append(dict(old=prev,new=tap))
  assert len(matches)==1
  rows.append(dict(type=name,core=c['inst'],origin_um=origin,old_outline_um=old['outline_um'],new_outline_um=[W,H],clock=matches[0]))
assert rows
assert p['partitions']==before['partitions'] and p['ports']==before['ports'] and p['lanes']==before['lanes']
dst.write_text(json.dumps(p,indent=1)+'\n')
report=dict(label='UNADOPTED candidate; compile/placement/tree required',changed_types=len(rows),changed_core_instances=sum(any(r['type']==x['type'] for r in rows) for x in p['partitions']),rows=rows,parent_partitions_unchanged=True,ports_lanes_unchanged=True,added_cycles=0)
dst.with_suffix('.delta.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
