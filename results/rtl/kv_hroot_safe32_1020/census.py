#!/usr/bin/env python3
"""Mapped gate input-pin fanout census. Excludes clock distribution only."""
import json,collections,sys
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads(p.read_text());m=j['modules']['qkd_kvs_hroot_safe32']
names={}
for n,v in m['netnames'].items():
 for b in v['bits']:
  if isinstance(b,int):names.setdefault(b,n)
loads=collections.Counter();drivers={};clocks=set()
for n,v in m['ports'].items():
 if v['direction']=='input':
  for b in v['bits']:drivers[b]='port:'+n
for n,c in m['cells'].items():
 for pn,bs in c['connections'].items():
  direction=c['port_directions'][pn]
  for b in bs:
   if direction=='input' and pn in ('C','CLK','CK'):clocks.add(b)
   elif direction=='input' and isinstance(b,int):loads[b]+=1
   elif direction=='output':drivers[b]=n+'/'+pn
# External outputs are actual pin loads too.
for n,v in m['ports'].items():
 if v['direction']=='output':
  for b in v['bits']:
   if isinstance(b,int):loads[b]+=1
rows=sorted([dict(net=names.get(b,str(b)),driver=drivers.get(b,'UNKNOWN'),loads=c) for b,c in loads.items() if b not in clocks],key=lambda r:-r['loads'])
r=dict(top='qkd_kvs_hroot_safe32',cells=len(m['cells']),clock_nets=len(clocks),max_loads=rows[0]['loads'],over32=[r for r in rows if r['loads']>32],top50=rows[:50],pass_census=not any(r['loads']>32 for r in rows))
print(json.dumps(r,indent=2))
