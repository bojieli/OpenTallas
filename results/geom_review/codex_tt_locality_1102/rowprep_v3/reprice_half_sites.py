"""Finite207 fresh-master half-site choices, AFTER existing87-row terminal only.

No CAD, new architecture, generic optimization or accepted source-state aliases.
Every fresh smaller cell remains inside its old already legal occupied box.
The only center choices are +/-0.027 for207 x2->x1 cells; exact2-SAT couples
all their actual first-register DATA/reset/macro and fixed clock/pin bounds.
"""
from pathlib import Path
import json,math,collections
P=Path(__file__).parent
report=json.loads((P/'rowjoint_report.json').read_text())
if report['status']!='PASS_FINITE_JOINT_ROW_SITE_MODEL_ONLY':raise ValueError('Existing row87 has no successful terminal; do not duplicate it')
exec((P/'rowprep_greedy.py').read_text().split('# Place the most constrained')[0])
complete=json.loads((P/'rowprep_complete_homes.json').read_text())
if {h['name'] for h in complete}!={d.cells[i][6] for i in variables}:raise ValueError('Existing row87 did not supply complete3011 homes')
for h in complete:
 i=names[h['name']];c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];x,y=h['xy'];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
changes=json.loads((P/'fresh_master_changes.json').read_text());choice={};fresh=set()
for z in changes:
 i=names[z['name']];c=d.cells[i];x,y=g.ctr(c)
 if c[1]!=z['old_master'] or abs(c[4]-c[2]-z['old_width_um'])>1e-6:raise ValueError('Reference oldPLACE footprint differs')
 w,hh=z['fresh_width_um'],z['fresh_height_um']
 if w>c[4]-c[2]+1e-6 or abs(hh-(c[5]-c[3]))>1e-6:raise ValueError('Fresh footprint is not the observed contained shrink')
 d.cells[i]=(c[0],z['fresh_master'],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6]);fresh.add(i)
 if abs((x-w/2)/.054-round((x-w/2)/.054))>1e-5:choice[i]=[(x-.027,y),(x+.027,y)]
if len(changes)!=244 or len(choice)!=207:raise ValueError('Observed244fresh/207halfsite cohort differs')
keys=sorted(choice);idx={i:k for k,i in enumerate(keys)};N=len(keys);graph=[set() for _ in range(2*N)];reverse=[set() for _ in range(2*N)];clauses=[]
def imply(a,b):graph[a].add(b);reverse[b].add(a)
def forbid(i,bi,j=None,bj=None,reason=None):
 a=2*idx[i]+bi
 if j is None:imply(a,a^1)
 else:
  b=2*idx[j]+bj;imply(a,b^1);imply(b,a^1)
 clauses.append(dict(i=d.cells[i][6],value=bi,j=None if j is None else d.cells[j][6],other_value=bj,reason=reason))
def xy(node,bit=None):
 if isinstance(node,tuple):return fixed[node]
 return choice[node][bit] if node in choice else g.ctr(d.cells[node])
edges=set()
for i in keys:
 for j in walk(i,False):edges.update(translate(j,i))
 for j in walk(i,True):edges.update(translate(i,j))
for a,b in edges:
 if b==('pd',3):continue # physically absent and no observing consumer
 if a==('pd',3):raise ValueError('Model unexpectedly gives deadPD3 a functional receiver')
 va,vb=a in choice,b in choice
 if not va and not vb:continue
 for ba in range(2) if va else [None]:
  for bb in range(2) if vb else [None]:
   pa,pb=xy(a,ba),xy(b,bb)
   if abs(pa[0]-pb[0])+abs(pa[1]-pb[1])<=405.00005:continue
   if va and vb:forbid(a,ba,b,bb,'actual_first_register_DATA_reset_macro405')
   elif va:forbid(a,ba,reason='actual_first_register_DATA_reset_macro405')
   else:forbid(b,bb,reason='actual_first_register_DATA_reset_macro405')
for i in keys:
 tap=pins[assign[d.cells[i][6]]];targets=[(tap['x'],tap['y'],200.0,'same63clock_assignment')]
 if i in pin_targets:targets.append((*pin_targets[i],30.0,'existing_TL_output_pin'))
 for bit,(x,y) in enumerate(choice[i]):
  for ax,ay,r,why in targets:
   if abs(x-ax)+abs(y-ay)>r+.00005:forbid(i,bit,reason=why)
  c=d.cells[i];llx,lly=x-(c[4]-c[2])/2,y-(c[5]-c[3])/2
  if abs(llx/.054-round(llx/.054))>1e-5 or abs(lly/.27-round(lly/.27))>1e-5:forbid(i,bit,reason='actual_row_site')
# Iterative Kosaraju2-SAT, a bounded finite feasibility problem (no L1 optimum).
seen=set();order=[]
for root in range(2*N):
 if root in seen:continue
 stack=[(root,False)]
 while stack:
  v,done=stack.pop()
  if done:order.append(v);continue
  if v in seen:continue
  seen.add(v);stack.append((v,True));stack.extend((u,False) for u in graph[v] if u not in seen)
component={};count=0
for root in reversed(order):
 if root in component:continue
 stack=[root];component[root]=count
 while stack:
  v=stack.pop()
  for u in reverse[v]:
   if u not in component:component[u]=count;stack.append(u)
 count+=1
bad=[d.cells[i][6] for i,k in idx.items() if component[2*k]==component[2*k+1]]
out=dict(status='FINITE_HALF_SITE_UNSAT_NO_ARCHITECTURE_CLAIM' if bad else 'PASS_FINITE_HALF_SITE_CHOICES_ONLY',variables=N,actual_edges=len(edges),forbidden_combinations=len(clauses),unsat_variables=bad,source_declared_added_ff=13,source_actual_added_ff=12,dead_PD3_not_physical=True,accepted_aliases=False,native_placement=False,physical_release=False,required='Complete fresh38243 DATA/reset/macro/clock/row/collision audit and all native/source/parent gates; no sourcealias acceptance from these choices')
(P/'fresh_halfsite_report.json').write_text(json.dumps(out,indent=1)+'\n')
if bad:raise SystemExit(2)
selected={i:int(component[2*k+1]>component[2*k]) for i,k in idx.items()}
# Check every clause explicitly; component-order convention must never invert bits.
for row in clauses:
 i=names[row['i']];j=None if row['j'] is None else names[row['j']]
 if selected[i]==row['value'] and (j is None or selected[j]==row['other_value']):raise ValueError('2SAT assignment violates an actual forbidden combination')
for i,b in selected.items():
 c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];x,y=choice[i][b];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
rows=[dict(name=d.cells[i][6],xy=list(g.ctr(d.cells[i]))) for i in sorted(variables|fresh)]
(P/'fresh_repriced_homes_DISABLED.json').write_text(json.dumps(rows,separators=(',',':'))+'\n');print('FRESH_HALF_SITE',out['status'],N,'binary choices',len(edges),'actual edges; full audit stillrequired',flush=True)
