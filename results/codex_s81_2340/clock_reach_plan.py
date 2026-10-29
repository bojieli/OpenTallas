#!/usr/bin/env python3
"""Geometry-only paired-inverter reach repair of an exported clock (trial candidate)."""
import json,sys,math,re
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S,die_trial as D
plan,treepath,out=sys.argv[1:4];o=Path(out);o.mkdir(parents=True,exist_ok=True)
P=S.Plan(json.load(open(plan)));site=D.SiteMap(P);t=json.load(open(treepath));xy=t['sites'];par=t['parent_of'];bound=float(sys.argv[4]) if len(sys.argv)>4 else 405.
def dist(a,b):return sum(abs(x-y) for x,y in zip(a,b))
def snap(q):return [round(round(q[0]/.054)*.054,6),round(round(q[1]/.27)*.27,6)]
def occupied(q,extra):
 return any(abs(q[0]-p[0])<2.16 and abs(q[1]-p[1])<.269 for p in list(xy.values())+extra)
repairs=[]
for child,parent in list(par.items()):
 if child not in xy or parent not in xy or dist(xy[child],xy[parent])<=bound:continue
 a,b=xy[parent],xy[child];L=dist(a,b)
 poly=D.legal_detour(site,a,b)
 if poly is None:raise SystemExit('NO_LEGAL_DETOUR '+child)
 best=None
 for n in range(2,22,2):
  pts,total=D.polyline_points(poly,[(j+1)/(n+1) for j in range(n)])
  ps=[]
  for p in pts:
   q=snap(p)
   candidates=[snap([q[0]+dx*.054,q[1]+dy*.27]) for dy in [0,1,-1,2,-2] for dx in [0,1,-1,2,-2,3,-3]]
   q=next((z for z in candidates if site.legal(z) and not occupied(z,ps)),None)
   if q is None:break
   ps.append(q)
  if len(ps)!=n:continue
  chain=[a]+ps+[b];mx=max(dist(x,y) for x,y in zip(chain,chain[1:]))
  if mx<=bound:
   best=dict(child=child,parent=parent,old_um=L,poly=poly,added=n,sites=ps,max_hop_um=mx,path_um=sum(dist(x,y) for x,y in zip(chain,chain[1:])))
   break
 if best is None:raise SystemExit('NO_FEASIBLE_CHAIN '+child)
 repairs.append(best);print(json.dumps(best),flush=True)
summary=dict(source=treepath,bound_um=bound,edges=len(par),repaired=len(repairs),added=sum(r['added'] for r in repairs),repairs=repairs)
json.dump(summary,open(o/'reach_plan.json','w'),indent=2)
print('SUMMARY',summary['repaired'],summary['added'],flush=True)
