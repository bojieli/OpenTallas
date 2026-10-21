#!/usr/bin/env python3
"""Actual primitive-copy cohort D-cone congruence, without assumed FF equality.

Adaptation of the original copy-init walk. Initial physical FFQ leaves are
unique. Exact (master, output-pin, ordered input-pin/cone tuples) are interned;
only a proven cohort is subsequently one Q leaf. Macro/stateful unknown outputs
are opaque. Input aliases are explicit wires in the supplied production-bound
proof vehicle, not logical-copy state aliases. This proves cohort convergence
under the stated equal reset/clock binding, not full RTL cold observability.
"""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mapped',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sp=importlib.util.spec_from_file_location('physical_cone_T',a.parser);T=importlib.util.module_from_spec(sp);sys.modules[sp.name]=T;sp.loader.exec_module(T)
r=json.load(open(a.record));g,top=T.flatten(T.parse_verilog(a.mapped.read_text()),r['top']);A=T.build(g,None);groups={};origin={};replica={}
for ci,(typ,name,pins) in enumerate(g.cells):
 if A['kind'][ci]!='ff':continue
 m=re.fullmatch(r'u(\d+)_c(\d+)\.u_cell',name);assert m,('unknown physical FF',name)
 oi,k=map(int,m.groups());origin[ci]=oi;replica[ci]=k;groups.setdefault(oi,[]).append(ci)
record={q['cell']:q for q in r['copied_cells'] if q['type'].startswith('DFF')};groups={oi:cs for oi,cs in groups.items() if oi in record}
assert set(groups)==set(record),('missing FF cohorts',sorted(set(record)-set(groups)))
assert all(len(cs)==record[oi]['copies'] and sorted(replica[c] for c in cs)==list(range(record[oi]['copies'])) for oi,cs in groups.items()),'missing/duplicate physical replicas'
assert all(g.cells[c][0]==record[oi]['type'] for oi,cs in groups.items() for c in cs),'FF master changed'
input_examples=[]
for name,(direction,net) in g.ports.items():
 if direction=='input' and '[' in name:
  assert A['driver'][net]==(-1,name),('input bit identity lost',name,A['driver'][net])
  if len(input_examples)<4:input_examples.append(dict(port_bit=name,driver_port_bit=A['driver'][net][1],net=net))
proven={};details={};rounds=[]
def cones():
 table={};memo={};visiting=set()
 def intern(key):
  if key not in table:table[key]=len(table)
  return table[key]
 def fp(x):
  if x in memo:return memo[x]
  if x in visiting:return intern(('opaque_combinational_cycle',x))
  if x<=3:answer=intern(('literal',x))
  else:
   driver=A['driver'].get(x)
   if driver is None:answer=intern(('opaque_undriven',x))
   else:
    ci,pn=driver
    if ci<0:answer=intern(('physical_input',pn))
    else:
     typ,name,pins=g.cells[ci];index=pins[pn].index(x);kind=A['kind'][ci]
     if kind=='ff':
      oi=origin[ci];answer=intern(('proved_cohort_Q',oi,pn,index) if oi in proven else ('physical_FF_Q',name,pn,index))
     elif kind in ('macro','latch'):
      answer=intern(('opaque_state_output',name,pn,index))
     else:
      visiting.add(x)
      args=tuple((ip,tuple(fp(b) for b in bs)) for ip,bs in sorted(pins.items()) if A['pin_dir'][ci][ip]=='in')
      visiting.remove(x);answer=intern(('comb',typ,pn,index,args))
  memo[x]=answer;return answer
 return fp
# Seed only reviewed actual async FF cohorts with equal physical reset/clock
# pins; data does not matter while the common reset is asserted. The reset
# predicate is the production rst_n assertion, not a new initial-state axiom.
fp=cones()
for oi,cs in groups.items():
 typ,_,pins=g.cells[cs[0]]
 reset=[p for p in pins if p in ('RESETN','SETN','RN','SN')]
 if not reset:continue
 assert typ=='DFFASRHQNx1_ASAP7_75t_R',('unsupported reset primitive',typ)
 signatures=[tuple((p,tuple(fp(b) for b in g.cells[c][2][p])) for p in sorted(pins) if p!='D' and A['pin_dir'][c][p]=='in') for c in cs]
 assert all(x==signatures[0] for x in signatures),'reset/clock identity differs'
 proven[oi]=0;details[oi]=dict(origin=oi,master=typ,method='actual common asynchronous reset contract',bound_edges=0)
for step in range(1,len(groups)+1):
 fp=cones();new=[]
 for oi,cs in groups.items():
  if oi in proven:continue
  roots=[g.cells[c][2]['D'][0] for c in cs];ids=[fp(x) for x in roots]
  config=[tuple((p,tuple(fp(b) for b in g.cells[c][2][p])) for p in sorted(g.cells[c][2]) if p!='D' and A['pin_dir'][c][p]=='in') for c in cs]
  if len(set(ids))==1 and all(x==config[0] for x in config):
   new.append(oi);details[oi]=dict(origin=oi,master=g.cells[cs[0]][0],method='same physical D wire' if len(set(roots))==1 else 'exact structural D-cone congruence',physical_D_roots=roots,bound_edges=step)
 if not new:break
 rounds.append(dict(edge=step,newly_proved_groups=len(new)))
 for oi in new:proven[oi]=step
fp=cones();unproved=[]
for oi,cs in groups.items():
 if oi in proven:continue
 roots=[g.cells[c][2]['D'][0] for c in cs]
 unproved.append(dict(origin=oi,master=g.cells[cs[0]][0],physical_D_roots=roots,distinct_D_wires=len(set(roots)),distinct_structural_D_cones=len({fp(x) for x in roots})))
# Causal graph negative: replace one ACTUAL copied FF's D with a new,
# independent physical input bit. No cohort-state alias can make that equal.
negative_origin=next(oi for oi,v in proven.items() if v>0)
negative_cell=max(groups[negative_origin],key=lambda c:replica[c]);old_cell=g.cells[negative_cell]
negative_net=g.net('__negative_independent_D[1]');A['driver'][negative_net]=(-1,'__negative_independent_D[1]')
changed=dict(old_cell[2]);changed['D']=[negative_net];g.cells[negative_cell]=(old_cell[0],old_cell[1],changed)
previous_bound=proven.pop(negative_origin);nfp=cones();negative_roots=[g.cells[c][2]['D'][0] for c in groups[negative_origin]];negative_distinct=len({nfp(x) for x in negative_roots})
assert negative_distinct>1,'distinct physical-D negative was incorrectly admitted'
negative=dict(refused=True,origin=negative_origin,cell=old_cell[1],replacement_physical_input='__negative_independent_D[1]',distinct_structural_D_cones=negative_distinct,remaining_cohorts_canonicalized=True)
g.cells[negative_cell]=old_cell;del A['driver'][negative_net];proven[negative_origin]=previous_bound
summary=dict(groups=len(groups),async_reset_groups=sum(v==0 for v in proven.values()),proven_unreset_groups=sum(v>0 for v in proven.values()),unproved_groups=len(unproved),max_cohort_convergence_edges=max(proven.values(),default=0),rounds=rounds)
x=dict(qualified=False,audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_driver_bit_examples=input_examples,causal_negative=negative,mapped_binding_sha256=hashlib.sha256(a.mapped.read_bytes()).hexdigest(),record_sha256=hashlib.sha256(a.record.read_bytes()).hexdigest(),parser_sha256=hashlib.sha256(a.parser.read_bytes()).hexdigest(),summary=summary,proven_groups=list(details.values()),unproved=unproved,scope='cohort convergence among actual physical replicas; exact explicit bound input aliases; common clock within each cohort, edges are local to that cohort domain; held common asynchronous reset; does not prove full RTL/mapped cold equivalence or valid-data observability; no canonical mapped-source CDC admission')
a.out.write_text(json.dumps(x,indent=1)+'\n');print(json.dumps(summary))
