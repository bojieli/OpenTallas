#!/usr/bin/env python3
"""Recursive primitive pin-load census of a Yosys-mapped JSON, with aliases unified.
Counts all data/reset/enable sinks and excludes only the named root clock net.
Generic ABC-mapped measurement; technology-specific native mapping still required.
"""
import json,sys,collections
x=json.load(open(sys.argv[1]));top=sys.argv[2];mods=x['modules'];loads=collections.Counter();drivers={};names={};clocks=set();leaves=0

def visit(mod,path,portmap=None):
 global leaves
 m=mods[mod];mapping={}
 if portmap:
  for n,p in m['ports'].items():
   for b,v in zip(p['bits'],portmap[n]):mapping[b]=v
 def bit(b):
  if isinstance(b,str):return b
  return mapping.get(b,(path,b))
 for n,p in m.get('netnames',{}).items():
  for i,b in enumerate(p['bits']):names.setdefault(bit(b),f'{path}.{n}[{i}]')
 if path==top:
  clocks.update(bit(b) for b in m['ports']['ck']['bits'])
 for n,c in m['cells'].items():
  conn={p:[bit(b) for b in bs] for p,bs in c['connections'].items()}
  if c['type'] in mods:
   visit(c['type'],path+'/'+n,conn)
  else:
   leaves+=1
   for p,bs in conn.items():
    direction=c['port_directions'][p]
    for b in bs:
     if isinstance(b,str) or b in clocks:continue
     if direction=='input':loads[b]+=1
     if direction=='output':drivers[b]=path+'/'+n+'/'+p
visit(top,top)
rank=sorted(loads,key=lambda b:loads[b],reverse=True)
rows=[{'net':names.get(b,str(b)),'driver':drivers.get(b,'top_input'),'loads':loads[b]} for b in rank]
json.dump({'kind':'generic_ABC_recursive_primitive_pin_census','top':top,'primitive_cells':leaves,'clock_exclusion':'root ck only','maximum_loads':max(loads.values(),default=0),'violations':[r for r in rows if r['loads']>32],'top_drivers':rows[:30],'pass':not any(r['loads']>32 for r in rows),'limits':'ASAP7 mapped census, reach, depth, storage and registered hard-boundary checks remain required before any gate'},sys.stdout,indent=2);print()
