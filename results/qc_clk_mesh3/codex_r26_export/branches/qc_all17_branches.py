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
def overlap(r,s):return Q(r[0])<Q(s[2]) and Q(s[0])<Q(r[2]) and Q(r[1])<Q(s[3]) and Q(s[1])<Q(r[3])
bytype=defaultdict(list)
for n,v in P.parts.items():bytype[v['type']].append(n)
def rect_at(n,xy,half):
 pts=[P.to_die(n,(xy[0]+dx,xy[1]+dy)) for dx in (-half,half) for dy in (-half,half)]
 return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
def contains(r,q):return Q(q[0])<=Q(r[0]) and Q(q[1])<=Q(r[1]) and Q(r[2])<=Q(q[2]) and Q(r[3])<=Q(q[3])
def legs(p,q):
 for z in [(q[0],p[1]),(p[0],q[1])]:
  if all(not any(overlap([min(a[0],b[0])-.64,min(a[1],b[1])-.64,max(a[0],b[0])+.64,max(a[1],b[1])+.64],k) for k in metal_ko) for a,b in [(p,z),(z,q)]):return [p,z,q]
 return None
# Core logic is <=M7: M8/M9 branch metal can cross it. Physical PHY
# macros retain actual-view metal keepouts; only the terminal pin escape is excepted.
metal_ko=[]
for name in ['io_serdes','io_serdes_1','io_serdes_2','ucie_kv']:
 size=(777.6,777.6) if name=='ucie_kv' else (1563.570,2320.056)
 pts=[P.to_die(name,(x,y)) for x in (0,size[0]) for y in (0,size[1])]
 metal_ko.append((min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts),name))
valid=json.loads((out.parent/'branch_reserve9/uniform_candidates.json').read_text());vehicles={}
for n in [e['part'] for e in json.loads((out.parent/'entry_inventory6/entry_inventory.json').read_text())['entries'] if e['nearest_mesh_um']>450]:
 pr=P.rect(n);end=list(P.to_die(n,P.ptype(n)['clock']['tap_um']));isphy=n in ['io_serdes','io_serdes_1','io_serdes_2','ucie_kv'];mx=P.parts[n].get('orient','R0')=='MX'
 if isphy:
  actual=next(k for k in metal_ko if k[4]==n);approach=[end[0],actual[1]-.81 if mx else actual[3]+.81]
 else:approach=end
 dist,layer,foot=nearest(approach)
 cand=[v for v in valid if abs(v['xy'][1]-approach[1])<900];pts=[foot,approach]+[v['xy'] for v in cand];d={0:(0,0.)};prev={};paths={};h=[(0,0.,0)]
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
 terminal=dict(actual_pin_um=end,layer='M5' if isphy else 'M9',approach_um=approach,normal_segment_um=md(end,approach),pin_exception='Canonical PHY clk normalescape only' if isphy else None,view=P.ptype(n)['contents'][0]['lef'] if isphy else None)
 if 1 not in d:vehicles[n]=dict(verdict='BLOCKED',terminal=terminal,candidates=len(cand),reachable=len(d));continue
 chain=[1]
 while chain[-1]!=0:chain.append(prev[chain[-1]])
 chain.reverse();vehicles[n]=dict(verdict='PLAN_CANDIDATE',terminal=terminal,points=[pts[x] for x in chain]+[end],hop_um=[md(pts[x],pts[y]) for x,y in zip(chain,chain[1:])],routes=[paths[x] for x in chain[1:]]+[[approach,end]],reservations=[cand[x-2] for x in chain if x>=2])
(out/'all17_branches.json').write_text(json.dumps(dict(scope='Proposal only; actualPHY terminal geometry needs nativecoupon; no insidePHYcells',branches=vehicles),indent=1));print(json.dumps({n:dict(verdict=v['verdict'],hops=len(v.get('hop_um',[])),terminal=v['terminal']) for n,v in vehicles.items()}))
