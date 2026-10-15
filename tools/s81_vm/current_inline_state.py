#!/usr/bin/env python3
"""Count declared sequential state bits in actual unhardened WFC/XIO control RTL.
This is source-state evidence, not mapped FF/cell area or a physical slot.
"""
import argparse,collections,json,pathlib,re
from current_physical_inventory import walk,local

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ast',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();t=json.loads(a.ast.read_text());idx={n['addr']:n for n in walk(t)if'addr'in n}
 def c(n):
  p=n['name'].split("'")[1].lstrip('s');return int(p[1:],{'h':16,'d':10,'b':2,'o':8}[p[0]])
 def bits(dtype):
  d=idx[dtype]
  if d['type']in ('UNPACKARRAYDTYPE','PACKARRAYDTYPE'):
   rr=d['rangep'][0];return(abs(c(rr['leftp'][0])-c(rr['rightp'][0]))+1)*bits(d['refDTypep'])
  r=d.get('range');return abs(int(r.split(':')[0])-int(r.split(':')[1]))+1 if r else 1
 records=[]
 for m in t['modulesp']:
  if m.get('origName')not in ('dsfd_vm_static_wfc','dsfd_vm_static_xio'):continue
  groups=collections.defaultdict(set)
  for n in local(m['stmtsp']):
   if n['type']!='ALWAYS':continue
   roots=[v['name']for s in walk(n.get('sentreep',[]))if s.get('type')=='SENITEM'and s.get('edgeType')=='POS'for v in s.get('sensp',[])if v['type']=='VARREF']
   if not roots:continue
   for d in walk(n.get('stmtsp',[])):
    if d.get('type')!='ASSIGNDLY':continue
    for v in walk(d['lhsp']):
     if v.get('type')=='VARREF':groups[','.join(roots)].add(v['varp'])
  records.append(dict(master=m['origName'],clock_regions=[dict(clock=k,declared_state_bits=sum(bits(idx[x]['dtypep'])for x in ids),variables=[dict(name=idx[x]['name'],declared_bits=bits(idx[x]['dtypep']))for x in sorted(ids)])for k,ids in groups.items()],physical_outline=None,mapped_cell_area_um2=None,area_status='UNMAPPED_SOURCE_STATE_NO_HARDENED_FOOTPRINT_OR_PIN_HOMES',scope='Declared storage bits in source variables assigned by edge-triggered nonblocking statements. Mapped replicas/clock/reset/hold repair and combinational logic absent; not a physical FF census.'))
 a.out.write_text(json.dumps(records,indent=1)+'\n');print(json.dumps([dict(master=x['master'],regions=[(y['clock'],y['declared_state_bits'])for y in x['clock_regions']])for x in records],indent=1))
if __name__=='__main__':main()
