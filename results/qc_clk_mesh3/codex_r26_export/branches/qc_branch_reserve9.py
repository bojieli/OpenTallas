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
bytype=defaultdict(list)
for n,v in P.parts.items():bytype[v['type']].append(n)
def rect_at(n,xy,half):
 pts=[P.to_die(n,(xy[0]+dx,xy[1]+dy)) for dx in (-half,half) for dy in (-half,half)]
 return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
def contains(r,q):return Q(q[0])<=Q(r[0]) and Q(q[1])<=Q(r[1]) and Q(r[2])<=Q(q[2]) and Q(r[3])<=Q(q[3])
def legs(p,q):
 for z in [(q[0],p[1]),(p[0],q[1])]:
  if all(not any(overlap([min(a[0],b[0])-.64,min(a[1],b[1])-.64,max(a[0],b[0])+.64,max(a[1],b[1])+.64],k) for k in ko) for a,b in [(p,z),(z,q)]):return [p,z,q]
 return None
# Extra measurement candidates are new reservations, never core-internal cells.
prior=json.loads((out.parent/'entry_inventory6/entry_inventory.json').read_text())['entries']
for e in prior:
 if e['part'] not in ('glue','native59','coll_f3'):continue
 ex,ey=e['entry']
 for n in P.parts:
  rr=P.rect(n)
  if rr[0]>1800 or rr[3]<ey-650 or rr[1]>ey+650:continue
  for x in [ex+dx for dx in (-345.6,-259.2,-172.8,-86.4,0,86.4,172.8,259.2,345.6)]:
   for y in [ey+dy for dy in (-518.4,-345.6,-172.8,-86.4,0,86.4,172.8,345.6,518.4)]:
    if rr[0]+9.72<x<rr[2]-9.72 and rr[1]+9.72<y<rr[3]-9.72:
     free.append(dict(part=n,index='NEW_WINDOW',xy=[x,y]))
valid=[];seen=set();reject=Counter()
for i in free:
 if i['xy'][0]>1800:continue
 n=i['part'];t=P.parts[n]['type'];pr=P.rect(n);xy=[i['xy'][0]-pr[0],i['xy'][1]-pr[1]];o=P.parts[n].get('orient','R0')
 if o in ('MY','R180'):xy[0]=pr[2]-pr[0]-xy[0]
 if o in ('MX','R180'):xy[1]=pr[3]-pr[1]-xy[1]
 key=(t,*map(Q,xy))
 if key in seen:continue
 seen.add(key);members=[];why=None
 for member in bytype[t]:
  win=rect_at(member,xy,4.32);halo=rect_at(member,xy,9.72)
  if not contains(halo,P.rect(member)):why='halo_outside_host';break
  if any(overlap(halo,k) for k in ko):why='halo_opaque';break
  if occupied(halo):why='halo_existing_clock';break
  members.append(dict(part=member,window=win,halo=halo))
 if why:reject[why]+=1;continue
 for m in members:valid.append(dict(part=m['part'],type=t,local_center_um=xy,xy=list(P.to_die(m['part'],xy)),members=members,source_island=i['index']))
old=json.loads((out.parent/'entry_inventory6/entry_inventory.json').read_text())['entries'];vehicles={}
for e in old:
 n=e['part'];e['entry']=list(P.to_die(n,P.ptype(n)['clock']['tap_um']));dd,ll,ff=nearest(e['entry']);e['nearest_mesh_um']=dd;e['nearest_mesh_foot']=list(ff)
(out/'uniform_candidates.json').write_text(json.dumps(valid))

for e in old:
 if e['nearest_mesh_um']<=450 or e['entry_phy_hits']:continue
 end=e['entry'];foot=e['nearest_mesh_foot'];cand=[v for v in valid if abs(v['xy'][1]-end[1])<900];pts=[foot,end]+[v['xy'] for v in cand]
 d={0:(0,0.)};prev={};paths={};h=[(0,0.,0)]
 while h:
  hops,length,u=heapq.heappop(h)
  if (hops,length)!=d[u]:continue
  if u==1:break
  for v,q in enumerate(pts):
   L=md(pts[u],q)
   if u==v or L>405.0001:continue
   path=legs(pts[u],q)
   if path is None:continue
   nd=(hops+1,length+L)
   if v not in d or nd<d[v]:d[v]=nd;prev[v]=u;paths[v]=path;heapq.heappush(h,(*nd,v))
 if 1 not in d:
  near=sorted([(md(v['xy'],end),v) for v in cand],key=lambda q:q[0])[:5]
  vehicles[e['part']]=dict(verdict='BLOCKED',reason='no405um chain full-window uniform reservation macro-clear legs',candidates=len(cand),entry=end,nearest_uniform=near,reachable=len(d));continue
 chain=[1]
 while chain[-1]!=0:chain.append(prev[chain[-1]])
 chain.reverse();vehicles[e['part']]=dict(verdict='PLAN_CANDIDATE',endpoint=end,points=[pts[x] for x in chain],hop_um=[md(pts[x],pts[y]) for x,y in zip(chain,chain[1:])],routes=[paths[x] for x in chain[1:]],reservations=[cand[x-2] for x in chain if x>=2])
r=dict(scope='Reservation delta only; no plan/emitter modified; PG/shields/STA unqualified. Four PHY actualtargets pending provider binding.',reference_geometry='export8 canonicalrow/pins; exactprovider58cc059cae',window_um=8.64,halo_um=5.4,max_hop_um=405,uniform_candidates=len(valid),reject=dict(reject),branches=vehicles)
(out/'branch_reservations.json').write_text(json.dumps(r,indent=1));print(json.dumps({k:v for k,v in r.items() if k!='branches'}));print(json.dumps({k:dict(verdict=v['verdict'],hops=len(v.get('hop_um',[])),max_um=max(v.get('hop_um',[0]))) for k,v in vehicles.items()}))
