import sys, json
sys.path.insert(0, sys.argv[1])
import qc_clk_mesh3 as Q3
from collections import defaultdict, Counter
class A: pass
a=A(); a.r2=sys.argv[2]
rec, P, dtp, parts, cores, cols, gaps, rows, m, dy = Q3.lattice(a)
bt=defaultdict(list)
for n in P.parts: bt[P.parts[n]["type"]].append(n)
for y in (10454.4,11793.6,13132.8,14472.0):
    ps=sorted([n for n in P.parts if abs(P.rect(n)[1]-y)<1], key=lambda n:P.rect(n)[0])
    print("ROW",y, " ".join(f"{P.parts[n]['type'][:14]}({len(bt[P.parts[n]['type']])})@{P.rect(n)[0]:.0f}" for n in ps))
for n in P.parts:
    r=P.rect(n)
    if r[0]>=1563 and 10000<r[1]<15800 and abs(r[1]-10454.4)>1 and abs(r[1]-11793.6)>1 and abs(r[1]-13132.8)>1 and abs(r[1]-14472)>1: print("other",n,P.parts[n]['type'],[round(v,1) for v in r])
# uncovered: grid sample
import numpy as np
W,H=31216.32,26265.6
xs=np.arange(5,W,20.0); ys=np.arange(5,H,20.0)
cov=np.zeros((len(xs),len(ys)),bool)
for n in P.parts:
    x0,y0,x1,y1=P.rect(n)
    cov[np.ix_((xs>=x0)&(xs<x1),(ys>=y0)&(ys<y1))]=True
u=~cov
print("uncovered frac",u.mean())
ix,iy=np.nonzero(u)
print("uncovered x range",xs[ix].min(),xs[ix].max(),"y",ys[iy].min(),ys[iy].max())
# columns of uncovered by x bins
for xb in range(0,32000,1563):
    sel=(xs[ix]>=xb)&(xs[ix]<xb+1563)
    if sel.any(): print("xbin",xb,"cells",sel.sum(),"y",ys[iy[sel]].min(),ys[iy[sel]].max())
