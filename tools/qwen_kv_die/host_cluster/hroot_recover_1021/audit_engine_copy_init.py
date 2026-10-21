#!/usr/bin/env python3
"""Adapt the existing attn_safe_control_1019/audit_copy_init.py graph walk.
No state-model admission or simulation is performed. Acyclic replica dependencies
permit a bound only among copies under identical driving inputs/reset sources;
feedback/cyclic groups remain explicitly unproved. It is not a full RTL/netlist
cold-equivalence certificate or a universal valid-data observability proof.
"""
import argparse,collections,hashlib,importlib.util,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
spec=importlib.util.spec_from_file_location('engine_init_lint',a.parser);T=importlib.util.module_from_spec(spec);sys.modules[spec.name]=T;spec.loader.exec_module(T)
raw=a.source.read_bytes();rec=json.load(open(a.record));assert hashlib.sha256(raw).hexdigest()==rec['source_sha256']
g,top=T.flatten(T.parse_verilog(raw.decode()),None);A=T.build(g,None);cnt={q['cell']:q['copies']-1 for q in rec['copied_cells']};out=[]
for oi,k in cnt.items():
 if A['kind'][oi]!='ff':continue
 typ,name,pins=g.cells[oi];stack=list(pins.get('D',[]));seen=set();up=set()
 while stack:
  x=stack.pop()
  if x in seen:continue
  seen.add(x);ci,pn=A['driver'].get(x,(-1,''))
  if ci<0:continue
  if A['kind'][ci]=='ff':up.add(ci);continue
  for pn,bs in g.cells[ci][2].items():
   if A['pin_dir'][ci][pn]=='in':stack.extend(bs)
 out.append(dict(origin=oi,name=name,master=typ,extra_copies=k,unreset=not any(p in pins for p in ('RESETN','SETN','RN','SN')),self_feedback=oi in up,upstream_copied_FF=sorted(x for x in up if x in cnt)))
by={q['origin']:q for q in out};edges={oi:[v for v in q['upstream_copied_FF'] if v in by and by[v]['unreset']] for oi,q in by.items() if q['unreset']}
# Tarjan SCCs expose all cyclic dependencies rather than assuming a fixed warmup.
index=0;indices={};low={};stack=[];active=set();components=[]
def visit(v):
 global index
 indices[v]=index;low[v]=index;index+=1;stack.append(v);active.add(v)
 for u in edges[v]:
  if u not in indices:visit(u);low[v]=min(low[v],low[u])
  elif u in active:low[v]=min(low[v],indices[u])
 if low[v]==indices[v]:
  comp=[]
  while True:
   u=stack.pop();active.remove(u);comp.append(u)
   if u==v:break
  if len(comp)>1 or v in edges[v]:components.append(sorted(comp))
for v in edges:
 if v not in indices:visit(v)
cyclic={v for c in components for v in c};memo={v:None for v in cyclic}
def depth(v):
 if v in memo:return memo[v]
 ds=[depth(u) for u in edges[v]];memo[v]=None if None in ds else 1+max(ds,default=0);return memo[v]
for v in edges:depth(v)
for q in out:q['replica_convergence_bound_edges']=memo.get(q['origin'],0 if not q['unreset'] else None)
summary=dict(copied_FF_groups=len(out),unreset_groups=sum(q['unreset'] for q in out),unreset_extra_copies=sum(q['extra_copies'] for q in out if q['unreset']),self_feedback_unreset=sum(q['unreset'] and q['self_feedback'] for q in out),cyclic_groups=len(cyclic),cyclic_components=components,unreset_groups_without_derived_bound=sum(memo[v] is None for v in edges),max_acyclic_replica_bound=max([d for d in memo.values() if d is not None],default=0))
x=dict(qualified=False,adapted_from='tools/qwen_kv_die/attn_safe_control_1019/audit_copy_init.py',source_sha256=hashlib.sha256(raw).hexdigest(),record_sha256=hashlib.sha256(a.record.read_bytes()).hexdigest(),parser_sha256=hashlib.sha256(a.parser.read_bytes()).hexdigest(),summary=summary,groups=out,scope='among added copies only; asserted equal reset sources; production clk/clk_bank/clk_out tied to one ingest clock; any cyclic/feedback cones remain unproved; no universal whole-engine cold conclusion')
a.out.write_text(json.dumps(x,indent=1)+'\n');print(json.dumps(summary))
