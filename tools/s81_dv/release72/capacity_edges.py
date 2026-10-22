#!/usr/bin/env python3
"""Reconstruct the final dv_route72c edge occupancy from its actual routed paths.
Read-only classification, not a router or a changed capacity rule.
"""
import json,sys,collections,bisect
import numpy as np
from pathlib import Path
LAT=43.2;CAP=.55*.30*160/.175
p=json.load(open(sys.argv[1]));W,H=p['facts']['die_um'];bs=p['blocks']
rect=[(b['x']-LAT,b['y']-LAT,b['x']+b['w']+LAT,b['y']+b['h']+LAT) for b in bs+p.get('blockages',[])]
def outer(e,f):
 x,y=e[2:4];return(round(x+(-LAT if f=='W' else LAT if f=='E' else 0),4),round(y+(-LAT if f=='S' else LAT if f=='N' else 0),4))
terms={l['i']:[outer(e,f) for e,f in zip(l['e'],l['endpoint_faces'])] for l in p['links']}
def gaps(hi,axis):
 out=set();edges=sorted({(r[axis],r[axis+2]) for r in rect});cuts=sorted([0]+[e for r in edges for e in r]+[hi])
 for u,w in zip(cuts,cuts[1:]):
  if w-u>=2*LAT:
   n=int((w-u)//LAT)
   for k in range(1,n):out.add(round(u+k*(w-u)/n,4))
 return out
xs=sorted({32.4,W-32.4}|{round(v,4) for r in rect for v in(r[0],r[2],(r[0]+r[2])/2) if 0<v<W}|{q[0] for t in terms.values() for q in t}|gaps(W,0))
ys=sorted({32.4,H-32.4}|{round(v,4) for r in rect for v in(r[1],r[3],(r[1]+r[3])/2) if 0<v<H}|{q[1] for t in terms.values() for q in t}|gaps(H,1))
xa,ya=np.array(xs),np.array(ys);blocked=np.zeros((len(ys),len(xs)),dtype=bool)
for x0,y0,x1,y1 in rect:
 ix=np.flatnonzero((xa>x0+1e-5)&(xa<x1-1e-5));iy=np.flatnonzero((ya>y0+1e-5)&(ya<y1-1e-5))
 if len(ix) and len(iy):blocked[iy[0]:iy[-1]+1,ix[0]:ix[-1]+1]=True
def band(a,k):return min((a[k]-a[k-1])/2 if k else LAT/2,LAT/2)+min((a[k+1]-a[k])/2 if k+1<len(a) else LAT/2,LAT/2)
use=collections.defaultdict(list)
for l in p['links']:
 edges=set();segments=[]
 for h in l['h']:
  if segments and abs(segments[-1][2]-h[0])<1e-4 and abs(segments[-1][3]-h[1])<1e-4 and ((abs(segments[-1][0]-segments[-1][2])<1e-6 and abs(h[0]-h[2])<1e-6) or (abs(segments[-1][1]-segments[-1][3])<1e-6 and abs(h[1]-h[3])<1e-6)):
   segments[-1][2:4]=h[2:4]
  else:segments.append(list(h))
 for x1,y1,x2,y2,b in segments:
  if abs(y1-y2)<1e-6:
   j=bisect.bisect_left(ys,round(y1,4));lo,hi=sorted((x1,x2))
   for i in range(max(0,bisect.bisect_right(xs,lo+1e-5)-1),min(len(xs)-1,bisect.bisect_left(xs,hi-1e-5)+1)):
    if xs[i]>=lo-1e-4 and xs[i+1]<=hi+1e-4 and not blocked[j,i] and not blocked[j,i+1]:edges.add(('H',j,i))
  elif abs(x1-x2)<1e-6:
   i=bisect.bisect_left(xs,round(x1,4));lo,hi=sorted((y1,y2))
   for j in range(max(0,bisect.bisect_right(ys,lo+1e-5)-1),min(len(ys)-1,bisect.bisect_left(ys,hi-1e-5)+1)):
    if ys[j]>=lo-1e-4 and ys[j+1]<=hi+1e-4 and not blocked[j,i] and not blocked[j+1,i]:edges.add(('V',j,i))
 for e in edges:use[e].append((l['i'],l['c'],l['b']))
rows=[]
for (d,j,i),links in use.items():
 width=band(ys,j) if d=='H' else band(xs,i);bits=sum(x[2] for x in links);ratio=bits/(CAP*width)
 if ratio<=1:continue
 xy=[xs[i],ys[j],xs[i+1] if d=='H' else xs[i],ys[j] if d=='H' else ys[j+1]]
 near=sorted(bs,key=lambda b:abs(b['x']+b['w']/2-xy[0])+abs(b['y']+b['h']/2-xy[1]))[:3]
 rows.append(dict(direction=d,xy_um=xy,bits=bits,capacity_bits=CAP*width,band_um=width,ratio=ratio,links=links,near=[b['name'] for b in near]))
rows.sort(key=lambda r:-r['ratio']);out=dict(recorded=p['facts']['physical72']['router'],reconstructed_edges=len(rows),max_ratio=rows[0]['ratio'] if rows else 0,hot_edges=rows[:120])
Path(sys.argv[2]).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='hot_edges'}));print(json.dumps(rows[:8],indent=1))
