"""Geometry-only candidates for unowned clock bodies; no route/timing adoption."""
from pathlib import Path
import json,re,sys,math
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-clock-sparse/tools/die_plan')
import schema as S,die_trial as DT
r=Path(__file__).resolve().parent;P=S.Plan(S.load(r/'current_C11E_plan.json'));sm=DT.SiteMap(P)
t=(r/'composite_ctree.tcl').read_text();v=(r/'composite_ctree.v').read_text();homes={z[1]:(float(z[2]),float(z[3])) for z in re.finditer(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}',t)}
claimed={z['cell'] for z in json.load(open(r/'current_C11E_clock_body_classification.json'))['cells'] if z['entries']}
cells={m[2]:(m[1],m[3],m[4]) for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\(\s*\.A\((\w+)\)\s*,\s*\.Y\((\w+)\)\s*\);',v,re.M)}
drivers={}
for n,(_,a,y) in cells.items():drivers.setdefault(y,[]).append(n)
legs=[(ds[0],n) for n,(_,a,y) in cells.items() if len(ds:=drivers.get(a,[]))==1]
def legal(q):return all(sm.legal((q[0]+x,q[1]+y)) for x,y in [(0,0),(1.62,.27)])
for axis in ['minimax']:
 moves={};failed=[];occupied={};current=dict(homes)
 neighbors={n:[] for n in homes}
 for a,b in legs:
  old=sum(abs(homes[a][k]-homes[b][k]) for k in (0,1))
  neighbors[a].append((b,old));neighbors[b].append((a,old))
 def buckets(q):
  return {(int(x//20),int(y//20)) for x,y in [(q[0],q[1]),(q[0]+1.62,q[1]+.27)]}
 def add(n,q):
  for k in buckets(q):occupied.setdefault(k,[]).append((n,q))
 def free(q):
  return not any(q[0]<p[0]+1.62 and q[0]+1.62>p[0] and q[1]<p[1]+.27 and q[1]+.27>p[1] for k in buckets(q) for _,p in occupied.get(k,[]))
 needs={n for n,q in homes.items() if not legal(q) and n not in claimed}
 for n,q in homes.items():
  if n not in needs:add(n,q)
 for n in sorted(needs):
  q=homes[n];candidates={sm.nearest(q,axis=a) for a in [None,'x','y']}
  incident=[current[z] for z,_ in neighbors[n]]
  if incident:
   mx=(min(z[0] for z in incident)+max(z[0] for z in incident))/2
   my=(min(z[1] for z in incident)+max(z[1] for z in incident))/2
   candidates.update(sm.nearest(z) for z in [(mx,my),(mx,q[1]),(q[0],my)])
  # Macro edges with full cell extent, then legal row/site snapping.
  for obs in sm.hits(q)+sm.hits((q[0]+1.62,q[1]+.27)):
   x0,y0,x1,y1,*_=obs
   candidates.update([(x0-1.674,q[1]),(x1+.054,q[1]),(q[0],y0-.54),(q[0],y1+.27)])
   for nq in incident:
    candidates.update([(x0-1.674,nq[1]),(x1+.054,nq[1]),(nq[0],y0-.54),(nq[0],y1+.27)])
  found=[]
  for x,y in candidates:
   for dx in range(-2,3):
    for dy in range(-2,3):
     p=(round((round(x/.054)+dx)*.054,3),round((round(y/.27)+dy)*.27,3))
     if legal(p) and free(p):
      ux,uy=abs(p[0]-q[0]),abs(p[1]-q[1])
      reach=[(abs(p[0]-current[z][0])+abs(p[1]-current[z][1]),old) for z,old in neighbors[n]]
      excess=[max(0,d-max(405,old)) for d,old in reach]
      score=(max(excess,default=0),sum(e>0 for e in excess),max((d for d,_ in reach),default=0),sum(d for d,_ in reach),ux+uy)
      found.append((score,p))
  if not found:failed.append(n);add(n,q);continue
  p=min(found)[1];moves[n]=p;current[n]=p;add(n,p)
 new={**homes,**moves};changes=[]
 for a,b in legs:
  old=sum(abs(homes[a][k]-homes[b][k]) for k in (0,1));now=sum(abs(new[a][k]-new[b][k]) for k in (0,1))
  if a in moves or b in moves:changes.append(dict(src=a,dst=b,old_um=round(old,3),new_um=round(now,3),delta_um=round(now-old,3)))
 out=dict(schema='ot_clock_rehome_candidate/1',axis=axis,adopted=False,route_allowed=False,basis='C11E SiteMap existing2.16halo; claimed entry windows kept HELD until actual child reservation evidence',total=len(homes),moves={n:dict(old_um=homes[n],new_um=q) for n,q in moves.items()},unplaced=failed,claimed_entry_cells_held=sorted(claimed),max_move_um=max((sum(abs(q[k]-homes[n][k]) for k in (0,1)) for n,q in moves.items()),default=0),changed_legs=changes,new_over405=[z for z in changes if z['new_um']>405 and z['old_um']<=405],all_changed_over405=[z for z in changes if z['new_um']>405],timing='NOT_RUN: all affected clock arrivals and CA must be remeasured')
 (r/f'rehome_{axis}.json').write_text(json.dumps(out,indent=2))
 print(axis,'moved',len(moves),'unplaced',len(failed),'maxmove',out['max_move_um'],'newlong',len(out['new_over405']),'allchangedlong',len(out['all_changed_over405']))
