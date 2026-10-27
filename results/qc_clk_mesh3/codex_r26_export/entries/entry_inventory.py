#!/usr/bin/env python3
"""Inventory real QC entries against the exported mesh and declared clock holes.
All island candidates remain plan geometry, not permission to modify a core.
"""
import argparse,csv,heapq,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('spec');ap.add_argument('out');a=ap.parse_args()
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-qc-export-1027/tools/die_plan')
import schema as S,die_clock as D,master_plan as MP,master_rulings as MR,infra_sites as IS
P=S.Plan(S.load(a.plan),Path(a.plan));sp=json.loads(Path(a.spec).read_text());mesh=sp['mesh'];out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
md=lambda p,q:abs(p[0]-q[0])+abs(p[1]-q[1]);Q=lambda x:int(round(x*1000))
ko=D.keepouts(P);_,cores=MR.die_geometry(P,MP.core_to_type,IS.rect_pts)
phy=[(*io['rect_um'],io['name']) for io in P.die.get('io',[]) if io.get('kind') in ('phy_macro','phy','serdes','hbm_phy')]
inside=lambda r,p:r[0]-1e-6<=p[0]<=r[2]+1e-6 and r[1]-1e-6<=p[1]<=r[3]+1e-6
hit=lambda p,rs:[r[4] for r in rs if inside(r,p)]
# Actual mesh segments, clipped exactly as exported rather than a full-height grid.
segs=[('M8',(s['x0'],s['y']),(s['x1'],s['y'])) for s in mesh['M8']]+[('M9',(s['x'],s['y0']),(s['x'],s['y1'])) for s in mesh['M9']]
def nearest(p):
 best=None
 for l,b,c in segs:
  q=(max(b[0],min(c[0],p[0])),max(b[1],min(c[1],p[1])))
  cand=(md(p,q),l,q)
  if best is None or cand<best:best=cand
 return best
# Declared plan islands, not inferred spare cell sites. Reject all opaque overlap.
cells=[];bins=defaultdict(list)
for n,v in sp['cell_sites'].items():
 x,y=v['origin_um'];r=(x,y,x+v['w'],y+.27,n);idx=len(cells);cells.append(r)
 for ix in range(math.floor(x/8.64),math.floor(r[2]/8.64)+1):
  for iy in range(math.floor(y/8.64),math.floor(r[3]/8.64)+1):bins[ix,iy].append(idx)
def overlap(r,s):return Q(r[0])<Q(s[2]) and Q(s[0])<Q(r[2]) and Q(r[1])<Q(s[3]) and Q(s[1])<Q(r[3])
def occupied(r):
 ids=set()
 for ix in range(math.floor(r[0]/8.64),math.floor(r[2]/8.64)+1):
  for iy in range(math.floor(r[1]/8.64),math.floor(r[3]/8.64)+1):ids.update(bins[ix,iy])
 return [cells[i][4] for i in ids if overlap(r,cells[i])]
islands=[];by_part=defaultdict(list)
for n in P.parts:
 for i,r in enumerate(P.ptype(n).get('clock',{}).get('die_islands_um',[])):
  pts=[P.to_die(n,(x,y)) for x in (r[0],r[2]) for y in (r[1],r[3])]
  rr=(min(q[0] for q in pts),min(q[1] for q in pts),max(q[0] for q in pts),max(q[1] for q in pts))
  blocked=[k[4] for k in ko if overlap(rr,k)]
  oc=occupied(rr);j=dict(part=n,index=i,rect=list(rr),xy=[(rr[0]+rr[2])/2,(rr[1]+rr[3])/2],blocked=blocked,occupied=oc)
  j['available']=not blocked and not oc
  by_part[n].append(j);islands.append(j)
free=[j for j in islands if j['available']]
rows=[]
for t in mesh['partition_taps']:
 n=t['part'];entry=P.to_die(n,P.ptype(n)['clock']['tap_um']);oldentry=t.get('entry',entry);dist,layer,foot=nearest(entry)
 available=by_part[n]
 row=dict(part=n,type=P.parts[n]['type'],entry=list(entry),legacy_entry=list(oldentry),legacy_entry_delta_um=round(md(entry,oldentry),6),
          old_mesh_foot=t['tap'],old_stub_um=t['stub_um'],nearest_mesh_foot=list(foot),nearest_mesh_layer=layer,nearest_mesh_um=round(dist,6),
          segments_450=math.ceil(dist/450-1e-9),segments_405=math.ceil(dist/405-1e-9),
          entry_core_hits=hit(entry,[r[:4]+(r[4]+'/'+r[5],) for r in cores]),entry_phy_hits=hit(entry,phy),
          declared_islands=len(available),declared_opaque_islands=sum(bool(i['blocked']) for i in available),
          declared_occupied_islands=sum(bool(i['occupied']) for i in available),declared_free_islands=sum(i['available'] for i in available))
 for key in ('entry_core_hits','entry_phy_hits'):row[key]=row[key]
 row['station_candidates']=[]
 ns=max(1,row['segments_450']);px,py=foot;ex,ey=entry
 for k in range(1,ns):
  # Manhattan lower-bound route (x first), not a routed clock leg.
  d=k*dist/ns;dx=abs(ex-px)
  pt=(px+math.copysign(min(d,dx),ex-px),py) if d<=dx else (ex,py+math.copysign(d-dx,ey-py))
  near=sorted(free,key=lambda i:md(i['xy'],pt))[:3]
  row['station_candidates'].append(dict(ideal=list(pt),opaque_hits=hit(pt,ko),nearest_declared_free=[dict(part=i['part'],index=i['index'],xy=i['xy'],distance_um=round(md(i['xy'],pt),3)) for i in near]))
 rows.append(row)
rows.sort(key=lambda r:-r['nearest_mesh_um'])
# Only the two requested side-bar vehicles: shortest path through existing free
# declared holes, with every segment <=450um and no new buffer inside a macro.
vehicles={}
for name in ('tt_ctlm','ucie_kv'):
 r=next(r for r in rows if r['part']==name);e=r['entry'];f=r['nearest_mesh_foot']
 candidates=[i for i in free if min(e[0],f[0])-450<=i['xy'][0]<=max(e[0],f[0])+450 and min(e[1],f[1])-450<=i['xy'][1]<=max(e[1],f[1])+450]
 pts=[f,e]+[i['xy'] for i in candidates];dist={0:(0,0.)};prev={};heap=[(0,0.,0)]
 while heap:
  hops,length,u=heapq.heappop(heap)
  if (hops,length)!=dist[u]:continue
  if u==1:break
  for v,q in enumerate(pts):
   if v==u:continue
   L=md(pts[u],q)
   if L>450.0001:continue
   nd=(hops+1,length+L)
   if v not in dist or nd<dist[v]:dist[v]=nd;prev[v]=u;heapq.heappush(heap,(*nd,v))
 if 1 in dist:
  chain=[];u=1
  while u!=0:chain.append(u);u=prev[u]
  chain.append(0);chain.reverse()
  vehicle=dict(verdict='PLAN_CANDIDATE',segments=dist[1][0],wire_um=round(dist[1][1],3),points=[pts[u] for u in chain],
               islands=[candidates[u-2] for u in chain if u>=2],hop_um=[round(md(pts[u],pts[v]),3) for u,v in zip(chain,chain[1:])])
 else:
  reached=sorted(dist);closest=min(((md(pts[u],e),u) for u in reached));vehicle=dict(verdict='NEEDS_PLAN_ISLAND',reachable_nodes=len(reached),candidate_islands=len(candidates),nearest_reachable_to_entry_um=round(closest[0],3),nearest_reachable=pts[closest[1]])
 vehicle['scope']='declared empty plan holes only; pin/PG/shield/clock timing and kit reservation unqualified; no core-internal buffer invented'
 vehicles[name]=vehicle
summary=dict(partitions=len(rows),legacy_entry_mismatches=sum(r['legacy_entry_delta_um']>.001 for r in rows),
             nearest_mesh_um=dict(max=rows[0]['nearest_mesh_um'],over450=sum(r['nearest_mesh_um']>450 for r in rows),over405=sum(r['nearest_mesh_um']>405 for r in rows)),
             entry_inside_core=sum(bool(r['entry_core_hits']) for r in rows),entry_inside_phy=sum(bool(r['entry_phy_hits']) for r in rows),
             declared_islands=len(islands),declared_free=len(free),declared_opaque=sum(bool(i['blocked']) for i in islands),vehicles=vehicles)
(out/'entry_inventory.json').write_text(json.dumps(dict(summary=summary,entries=rows),indent=1))
fields=['part','type','old_stub_um','nearest_mesh_um','nearest_mesh_layer','segments_450','segments_405','declared_islands','declared_free_islands','entry_core_hits','entry_phy_hits']
with (out/'entry_inventory.csv').open('w') as h:
 w=csv.DictWriter(h,fieldnames=fields);w.writeheader()
 for r in rows:w.writerow({k:r[k] for k in fields})
(out/'summary.json').write_text(json.dumps(summary,indent=1));print(json.dumps(summary,indent=1)[:15000])
