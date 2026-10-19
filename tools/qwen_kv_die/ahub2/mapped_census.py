#!/usr/bin/env python3
"""Uncapped every-driver logical-pin census on a MAPPED netlist json: mapped_census.py <mapped.json> <top> (KV-AHUB2 generalisation of ahub_safe/driver_census.py)."""
import collections,gzip,hashlib,json,sys
from pathlib import Path
path=Path(sys.argv[1]);j=json.loads(gzip.decompress(path.read_bytes())if path.suffix=='.gz'else path.read_bytes());top=sys.argv[2];m=j['modules'][top];drivers={};inputs={b:(p,i)for p,v in m['ports'].items()if v['direction']=='input'for i,b in enumerate(v['bits'])}
def transparent(c):return c['type'].startswith(('INV','BUF','HB'))
for n,c in m['cells'].items():
 for p,bs in c['connections'].items():
  if c['port_directions'][p]=='output':
   for i,b in enumerate(bs):assert b not in drivers;drivers[b]=(n,p,i)
def resolve(b):
 seen=set();pol=0
 while b in drivers:
  n,p,i=drivers[b];c=m['cells'][n]
  if not transparent(c):return ('cell',n,p,i),pol
  assert n not in seen;seen.add(n)
  ins=[x for q,bs in c['connections'].items()if c['port_directions'][q]=='input'for x in bs];assert len(ins)==1
  pol^=c['type'].startswith('INV');b=ins[0]
 if b in inputs:return ('input',*inputs[b]),pol
 assert b in ('0','1','x','z'),('undriven',b)
 return ('constant',b),pol
inventory={}
def register(rt):
 if rt in inventory:return
 if rt[0]=='cell':
  c=m['cells'][rt[1]];kind='FF'if c['type'].startswith('DFF')else'macro'if c['type']in('ot_nhb_zh','ot_qkh_recip_leaf')else'comb';master=c['type']
 elif rt[0]=='input':kind='clock'if rt[1]=='ck'else'reset'if rt[1]=='rst_n'else'top_input';master=None
 else:kind='constant';master=None
 inventory[rt]={'driver':list(rt),'role':kind,'master':master,'endpoints':[]}
for n,c in m['cells'].items():
 if transparent(c):continue
 for p,bs in c['connections'].items():
  if c['port_directions'][p]=='output':
   for b in bs:register(resolve(b)[0])
for b in inputs:register(resolve(b)[0])
# Enumerate real logical-pin loads through unlimited transparent depth. No
# endpoint truncation or macro/input/constant exclusions are applied.
for n,c in m['cells'].items():
 if transparent(c):continue
 for p,bs in c['connections'].items():
  if c['port_directions'][p]!='input':continue
  for i,b in enumerate(bs):
   rt,pol=resolve(b);register(rt);role='clock'if p.upper()in('CLK','CK','CLOCK')else'reset'if p.upper()in('RESETN','SETN','RST_N','RESET','RST')else'macro'if c['type']in('ot_nhb_zh','ot_qkh_recip_leaf')else'FF'if c['type'].startswith('DFF')else'comb'
   inventory[rt]['endpoints'].append({'kind':'cell_pin','instance':n,'master':c['type'],'pin':p,'bit':i,'polarity':int(pol),'role':role})
for p,v in m['ports'].items():
 if v['direction']!='output':continue
 for i,b in enumerate(v['bits']):
  rt,pol=resolve(b);register(rt);inventory[rt]['endpoints'].append({'kind':'top_output','port':p,'bit':i,'polarity':int(pol),'role':'top_output'})
records=list(inventory.values());findings=[]
for r in records:
 r['loads']=len(r['endpoints']);r['endpoint_role_counts']=dict(collections.Counter(x['role']for x in r['endpoints']));r['clock_only']=bool(r['endpoints'])and all(x['role']=='clock'for x in r['endpoints'])
 if r['loads']>32:findings.append({'driver':r['driver'],'role':r['role'],'loads':r['loads'],'clock_only':r['clock_only'],'constant':r['role']=='constant'})
unsafe=[x for x in findings if not x['clock_only']and not x['constant']]
report={'schema':'opentallas.ahub.uncapped_every_driver_census.v1','status':'PASS'if not unsafe else'FAIL','source_reparsed_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'physical_qualified':False,'count_basis':'first nontransparent logical input pins and top-output port bits; all polarities, classes, endpoints and zero-load drivers retained','driver_role_counts':dict(collections.Counter(x['role']for x in records)),'driver_count':len(records),'ff_count':sum(1 for c in m['cells'].values() if c['type'].startswith(('DFF','ASYNC','SDF'))),'cell_type_counts':dict(collections.Counter(c['type'] for c in m['cells'].values())),'endpoint_count':sum(x['loads']for x in records),'maximum_by_role':{role:max(x['loads']for x in records if x['role']==role)for role in set(x['role']for x in records)},'all_over32_findings':findings,'unsafe_over32_findings':unsafe,'drivers':records}
print(json.dumps(report,indent=2));print('MAPPED_CENSUS',report['status'],'ff',report['ff_count'],'max_by_role',report['maximum_by_role'],'unsafe',len(unsafe),file=sys.stderr);assert not unsafe,[ (x['driver'],x['loads']) for x in unsafe]
