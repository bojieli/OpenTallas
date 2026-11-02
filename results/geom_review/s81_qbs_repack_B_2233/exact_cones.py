"""Exact FF and directed physical macro-port endpoints from the matched native net index."""
import collections

def physical_port_map(complete):
 out=collections.defaultdict(list)
 for nm,m in complete['macros'].items():
  for p in m['ports']:
   if p['geom_net_index']is not None:
    out[(m['cid'],p['geom_net_index'],p['io'])].append((*p['xy'],'M:'+nm+'.'+p['port']))
 return out

def endpoints(D,cid,forward):
 seq=set();macro=set();todo=[cid];seen=set()
 while todo:
  c=todo.pop()
  if c in seen:continue
  seen.add(c)
  if forward:
   for ni in D.drives.get(c,[]):
    sig,dr,sinks=D.nets[ni]
    if sig in ('CLOCK','POWER','GROUND'):continue
    for r in sinks:
     if r[0]!='i'or r[2]:continue
     k=D.kind(r[1])
     if k=='S':seq.add(r[1])
     elif k=='M':macro.add((r[1],ni,'INPUT'))
     elif k in ('B','L','K'):todo.append(r[1])
  else:
   for ni,clock in D.cell_in.get(c,[]):
    if clock:continue
    sig,dr,ss=D.nets[ni]
    if sig in ('CLOCK','POWER','GROUND'):continue
    drivers=[('i',v,False)for v in D.multi_drv[ni]]if ni in D.multi_drv else([dr]if dr else[])
    for r in drivers:
     if r[0]!='i':continue
     k=D.kind(r[1])
     if k=='S':seq.add(r[1])
     elif k=='M':macro.add((r[1],ni,'OUTPUT'))
     elif k in ('B','L','K'):todo.append(r[1])
 return seq,macro
