#!/usr/bin/env python3
"""Mapped JSON census, following textbook BUF/INV transparent fanout."""
import collections,hashlib,json,sys
from pathlib import Path
for filename in sys.argv[1:]:
 p=Path(filename);d=json.loads(p.read_text());mods=d['modules'];top=next(n for n,m in mods.items() if m.get('attributes',{}).get('top') in ('1','00000000000000000000000000000001'))
 cells=[];counter=[0];names={}
 def fresh(label):
  counter[0]+=1;names[counter[0]]=label;return counter[0]
 def flatten(mname,prefix,bindings=None):
  m=mods[mname];bits={}
  for pn,ps in m['ports'].items():
   for i,b in enumerate(ps['bits']):bits[b]=bindings[pn][i] if bindings else fresh(prefix+pn+f'[{i}]')
  def bit(b):
   if isinstance(b,str):return b
   if b not in bits:bits[b]=fresh(prefix+str(b))
   return bits[b]
  for n,c in m.get('cells',{}).items():
   con={pn:[bit(b) for b in bs] for pn,bs in c['connections'].items()};sub=mods.get(c['type'])
   if sub and sub.get('cells'):flatten(c['type'],prefix+n+'/',con)
   else:cells.append((prefix+n,c['type'],con,c.get('port_directions') or {pn:ps['direction'] for pn,ps in sub['ports'].items()}))
  return {pn:[bit(b) for b in ps['bits']] for pn,ps in m['ports'].items()}
 ports=flatten(top,'');clock=set(ports['ck']);sinks=collections.defaultdict(list);drivers={};transparent={}
 for n,t,c,direction in cells:
  ins=[b for pn,bs in c.items() if direction[pn]=='input' for b in bs]
  outs=[b for pn,bs in c.items() if direction[pn]=='output' for b in bs]
  for pn,bs in c.items():
   if direction[pn]=='input':
    for b in bs:sinks[b].append((n,t,pn))
   else:
    for b in bs:drivers[b]=(n,t,pn)
  if (t.startswith('BUF') or t.startswith('INV')) and len(ins)==len(outs)==1:transparent[n]=outs[0]
 for pn,ps in mods[top]['ports'].items():
  if ps['direction']=='output':
   for b in ports[pn]:sinks[b].append(('$output/'+pn,'PORT','P'))
 rows=[]
 for b,driver in drivers.items():
  if b in clock or driver[0] in transparent or isinstance(b,str):continue
  todo=[b];seen=set();loads=[]
  while todo:
   x=todo.pop()
   if x in seen:continue
   seen.add(x)
   for s in sinks[x]:
    if s[0] in transparent:todo.append(transparent[s[0]])
    else:loads.append(s)
  rows.append({'net':names[b],'driver':driver,'loads':len(loads)})
 rows.sort(key=lambda r:r['loads'],reverse=True)
 bad=[r for r in rows if r['loads']>32]
 result={'top':top,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mapped_cells':len(cells),'cell_types':dict(collections.Counter(t for n,t,c,dr in cells)),'max_nonclock_driver_loads':max((r['loads'] for r in rows),default=0),'drivers_over32':len(bad),'violations':bad,'verdict':'FAIL' if bad else 'PASS'}
 p.with_suffix('.census.json').write_text(json.dumps(result,indent=2)+'\n');print(p.name,result['verdict'],result['max_nonclock_driver_loads'],result['drivers_over32'])
