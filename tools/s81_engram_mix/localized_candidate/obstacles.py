#!/usr/bin/env python3
"""Necessary-only channel visibility lowerbound with explicit optimistic owner stubs."""
import argparse,json,re,subprocess,itertools,heapq,bisect
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();O=a.out;R=Path(__file__).resolve().parents[3];j=json.loads((O/'connected_geometry.json').read_text());boxes=j['results']['Q_cooptimized_capsules']['placement'];legs=json.loads((O/'parent_figure_receipt.json').read_text())['top_grouped_actual_failing_legs'];pins={}
for m,v in j['leaf_views'].items():
 s=subprocess.check_output(['git','show',v['record']+':'+v['path']],cwd=R).decode();pins[m]={}
 for pm in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',s,re.M|re.S):pins[m][pm[1]]=[((float(x)+float(z))/2,(float(y)+float(w))/2)for x,y,z,w in re.findall(r'RECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',pm[2])]
rects={n:(b['x']-.036,b['y']-.036,b['x']+b['w']+.036,b['y']+b['h']+.036)for n,b in boxes.items()}
def inside(x,y):return any(x0+1e-7<x<x1-1e-7 and y0+1e-7<y<y1-1e-7 for x0,y0,x1,y1 in rects.values())
def escapes(row,side):
 n,pin=row[side];b=boxes[n];x0,y0,x1,y1=rects[n];out=[]
 for dx,dy in pins[row[side+'_master']][pin]:
  x,y=b['x']+dx,b['y']+dy
  candidates=[(x0,y),(x1,y),(x,y0),(x,y1)];stub=min(abs(x-u)+abs(y-v)for u,v in candidates)
  for u,v in candidates:
   if abs(x-u)+abs(y-v)<=stub+1e-7 and not inside(u,v):out.append((u,v,stub))
 return out
rows=[]
for leg in legs:
 sources,targets=escapes(leg,'source'),escapes(leg,'target');xs=sorted({x for r in rects.values()for x in[r[0],r[2]]}|{x for x,y,c in sources+targets});ys=sorted({y for r in rects.values()for y in[r[1],r[3]]}|{y for x,y,c in sources+targets});nx,ny=len(xs),len(ys);free={(i,k)for i,x in enumerate(xs)for k,y in enumerate(ys)if not inside(x,y)};dist={};queue=[];targetmap={}
 for x,y,c in targets:
  node=(bisect.bisect_left(xs,x),bisect.bisect_left(ys,y));targetmap[node]=min(c,targetmap.get(node,1e99))
 for x,y,c in sources:
  node=(bisect.bisect_left(xs,x),bisect.bisect_left(ys,y));dist[node]=min(c,dist.get(node,1e99));heapq.heappush(queue,(c,node))
 best=1e99
 while queue:
  cost,node=heapq.heappop(queue)
  if cost!=dist[node]or cost>=best:continue
  if node in targetmap:best=min(best,cost+targetmap[node])
  i,k=node
  for other in [(i-1,k),(i+1,k),(i,k-1),(i,k+1)]:
   if other not in free:continue
   u,v=other
   if inside((xs[i]+xs[u])/2,(ys[k]+ys[v])/2):continue
   nc=cost+abs(xs[i]-xs[u])+abs(ys[k]-ys[v])
   if nc<dist.get(other,1e99):dist[other]=nc;heapq.heappush(queue,(nc,other))
 value=None if best==1e99 else best;rows.append({'source':leg['source'],'target':leg['target'],'terminal_L1_um':leg['distance_um'],'whole_outline_visibility_um':value,'extra_obstacle_um':None if value is None else max(0,value-leg['distance_um']),'optimistic_setup_ps_with_visibility':None if value is None else leg['selected_setup_ps']-.76*(value-leg['distance_um']),'owner_escape_stubs':'Nearest-outline-edge escape only from each actual terminal rectangle center; short access stub explicit, access unqualified.'})
report={'status':'NECESSARY_ONLY_CHANNEL_VISIBILITY_SCREEN','rows':rows,'scope':['Whole actual child outlines blocked plus .036um wire-center halo; orthogonal visibility graph uses all rectangle edges and nearest-side source/target owner escapes.','Owner escape stubs are explicitly optimistic, not LEF pin access proof. No route/track/PG/clock feasibility claimed.','Allows paths along expanded-outline boundaries; fullparent transports and all other incident nets not routed.']};(O/'obstacle_visibility.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(rows,indent=1))
