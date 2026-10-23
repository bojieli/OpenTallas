#!/usr/bin/env python3
"""Independently judge a completed real placement replay and pin its inputs."""
import hashlib,json,pickle,sys
from pathlib import Path
root=Path(sys.argv[1]);run=root/sys.argv[2];bind=root/sys.argv[3]
sys.path[:0]=[str(root/'input/src/tools/s81_dv'),str(root/'input/src/tools')]
import dv_rvcase as D
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=json.load(open(run/'result.json'));loc=result['placement']
with open(run/'before_repair.pickle','rb') as f:args,kw=pickle.load(f)
st,parent,kids,terms,old,oldloc,placer,reach,boxes=args
cen=lambda v:(loc[v][0]+loc[v][2]/2,loc[v][1]+loc[v][3]/2)
hop=lambda a,b:sum(abs(x-y) for x,y in zip(a,b))
rows=[dict(source=v,capture=u,hop=hop(cen(v),cen(u))) for v in sorted(st) for u in kids[v]]
rows += [dict(source=v,capture=t,hop=hop(cen(v),t)) for v in sorted(st) for t in terms[v]]
over=[r for r in rows if r['hop']>reach]
# Physical legality is overlap of macro rectangles. Also report the planner's
# stronger 0.5 um guard separately, without confusing it with physical overlap.
W,H=json.load(open(root/'input/case/case.json'))['die_um'];p=D.Placer(W,H)
plan=json.load(open(root/'input/plan.json'))
for v,(x,y,w,h,_) in sorted(loc.items()):
 if v not in st:p.add((x,y,x+w,y+h))
for b in plan.get('blockages',[]):p.add((b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
collisions=[];guard=[];outside=[]
for v in sorted(st):
 x,y,w,h,_=loc[v];r=(x,y,x+w,y+h)
 if p.hits(r,gap=0):collisions.append(v)
 if p.hits(r,gap=.5):guard.append(v)
 p.add(r)
 if v in boxes:
  b=boxes[v];c=cen(v)
  if not (b[0]<=c[0]<=b[2] and b[1]<=c[1]<=b[3]):outside.append(v)
hints=json.load(open(bind/'place_hints.json'));explicit=[]
for h in hints['reset_place']:
 if h.get('kind')=='frame_chain_reset_v2':
  v=h['inst'];explicit.append(dict(inst=v,planned=h['xy'],actual=cen(v),displacement=hop(cen(v),h['xy']),
                  max_hop=max((r['hop'] for r in rows if r['source']==v or r['capture']==v),default=None),box=boxes.get(v)))
nets,tin,tout,insts=D.DPB.parse_die(bind/'die.v','dv_die')
graph={nm:{p:D.DPB.expr_bits(e,nets) for p,e in cm.items()} for mst,nm,_,cm in insts if mst!='__assign__'}
clocks={v:{p:b for p,b in ports.items() if p.lower().startswith(('ck','clk','clock')) or any(n.startswith('ck_') for n,_ in b)} for v,ports in graph.items()}
identity=result['identity'];die_sha=sha(bind/'die.v')
assert die_sha==identity.get(str(bind/'die.v')) or die_sha in identity.values()
assert identity['connectivity_sha256']==hashlib.sha256(json.dumps(graph,sort_keys=True).encode()).hexdigest()
pins={str(p.relative_to(root)):sha(p) for p in [bind/'die.v',bind/'place_hints.json',bind/'bind_case.json',root/'input/case/views/dsfd_rly_1_WN.lef',root/'calendar_sites.py',root/'calendar_sites_cap30.patch',run/'dv_rvcase_patched.py']}
receipt=dict(verdict='PASS' if not (over or collisions or guard or outside) else 'FAIL',
             scope='physical reset placement only; no GRT/STA/clock closure',stages=len(st),hops=len(rows),
             over_reach=over,macro_overlaps=collisions,planner_guard_failures=guard,out_of_region=outside,
             max_hop_um=max(r['hop'] for r in rows),explicit=explicit,
             clock_connections_sha256=hashlib.sha256(json.dumps(clocks,sort_keys=True).encode()).hexdigest(),
             identity=identity,consumed=pins,placement_sha256=sha(run/'result.json'))
json.dump(receipt,open(run/'receipt.json','w'),indent=1)
print(json.dumps({k:v for k,v in receipt.items() if k not in ('explicit','identity','consumed')},indent=1))
