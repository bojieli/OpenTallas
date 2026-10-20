#!/usr/bin/env python3
import json,sys,collections
x=json.load(open(sys.argv[1]));report=[]
for mn,m in x['modules'].items():
 if m.get('attributes',{}).get('blackbox'): continue
 loads=collections.Counter();drivers={}
 clock=set()
 for p,v in m['ports'].items():
  if p in ('ck','clk'):clock.update(v['bits'])
  if v['direction']=='input':
   for b in v['bits']:drivers[b]='port:'+p
 for cn,c in m['cells'].items():
  for pn,bits in c['connections'].items():
   direction=c['port_directions'].get(pn)
   if direction=='input':
    for b in bits:
     if isinstance(b,int):loads[b]+=1
   if direction=='output':
    for b in bits:drivers[b]=cn+'/'+pn
 for b,n in loads.items():
  if b not in clock:report.append(dict(module=mn,bit=b,driver=drivers.get(b,'unknown'),loads=n))
report.sort(key=lambda d:-d['loads'])
out=dict(schema='qw.btab.strict_mapped_fanout.v1',max_nonclock_loads=max((r['loads'] for r in report),default=0),over32=[r for r in report if r['loads']>32],top=report[:30])
print(json.dumps(out,indent=2))
sys.exit(bool(out['over32']))
