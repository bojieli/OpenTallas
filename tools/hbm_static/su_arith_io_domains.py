#!/usr/bin/env python3
"""Conservative IO-to-root graph audit of the existing Yosys leaf census.

Whole-cell vector dependencies overapproximate bit timing arcs. This flags
ports requiring real mapped STA ownership; it cannot qualify a clock domain.
"""
import collections,hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);top=json.loads(p.read_text())['modules']['ot_hbm_su_static_lane'];ports=top['ports'];roots={b:f'{n}[{i}]' for n in ['clk_stage','clk_insert'] for i,b in enumerate(ports[n]['bits'])};names=list(roots.values());masks={b:1<<names.index(n) for b,n in roots.items()};seq=[];comb=[]
for name,c in top['cells'].items():
 ins=[b for n,bs in c['connections'].items()if c['port_directions'][n]=='input'and n not in ['CLK','ARST','ALOAD']for b in bs if isinstance(b,int)]
 outs=[b for n,bs in c['connections'].items()if c['port_directions'][n]=='output'for b in bs if isinstance(b,int)]
 if c['type']in ['$dff','$adff','$dffe','$adffe','$sdff','$sdffe']:
  cl=c['connections']['CLK'];assert len(cl)==1 and cl[0]in masks,(name,cl);seq.append((ins,outs,masks[cl[0]]))
 elif 'dff'in c['type'].lower()or 'latch'in c['type'].lower():raise RuntimeError(c['type'])
 else:comb.append((ins,outs))
def closure(back):
 state={};listeners=collections.defaultdict(list);work=collections.deque();pending=set()
 cells=[(out,ins)if back else(ins,out)for ins,out in comb]
 for i,(dep,targ)in enumerate(cells):
  for b in set(dep):listeners[b].append(i)
 def add(b,m):
  old=state.get(b,0)
  if old|m!=old:
   state[b]=old|m
   for i in listeners.get(b,[]):
    if i not in pending:pending.add(i);work.append(i)
 for ins,out,m in seq:
  for b in ins if back else out:add(b,m)
 while work:
  i=work.popleft();pending.remove(i);dep,targ=cells[i];m=0
  for b in dep:m|=state.get(b,0)
  for b in targ:add(b,m)
 return state
states={'input':closure(True),'output':closure(False)};records=[]
for name,d in ports.items():
 if name.startswith('clk_'):continue
 mask=0
 for b in d['bits']:mask|=states[d['direction']].get(b,0)
 records.append(dict(port=name,direction=d['direction'],roots=[n for i,n in enumerate(names)if mask&(1<<i)],bits=len(d['bits'])))
input_names=[n for n,d in ports.items()if d['direction']=='input'and not n.startswith('clk_')]
saved_seq=seq;seq=[([],ports[n]['bits'],1<<i)for i,n in enumerate(input_names)];direct=closure(False);seq=saved_seq;exposures=[]
for n,d in ports.items():
 if d['direction']!='output':continue
 mask=0
 for b in d['bits']:mask|=direct.get(b,0)
 if mask:exposures.append(dict(output=n,inputs=[v for i,v in enumerate(input_names)if mask&(1<<i)]))
report=dict(unregistered_input_to_output=exposures,qualified=False,method='Conservative whole-vector Yosys cell dependency graph; actual mapped per-bit STA still required',source_netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),sequential_groups=len(seq),ports=records,multi_root_inputs=[r for r in records if r['direction']=='input'and len(r['roots'])>1],multi_root_outputs=[r for r in records if r['direction']=='output'and len(r['roots'])>1])
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['multi_root_inputs','multi_root_outputs','unregistered_input_to_output']}))
