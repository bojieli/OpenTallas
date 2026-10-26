#!/usr/bin/env python3
"""E5 spine/rib clock trunk model (CLOCK-RESET 10-26, geometry + Elmore estimate, no timing verdict).
Spine = vertical private legs on M5 up/down the logic column from its midpoint M; ribs = private
legs from spine points along legal M4 horizontal channels (SRAM/ROM obstruct M1-M4 only) then M5
vertical (may cross macros) to tap hubs (<=HUB taps each).  Every level has ONE repeater count
(longest leg / RMAX), so every tap has the identical stage count; no balancing wire is added."""
import json, math, sys, collections
geo, out = sys.argv[1], sys.argv[2]
RMAX=float(sys.argv[3]) if len(sys.argv)>3 else 100.0
HUB=int(sys.argv[4]) if len(sys.argv)>4 else 8
XS=166.0                                # spine x: centre of logic column 137.4..194.4
YS=[15,76,132,170,216,261,300,356,400,452]   # spine points = horizontal channel rows / column rows
T=[];MAC=[];root=None;core=None
for l in open(geo):
    f=l.split()
    if f[0]=='TAP': T.append((f[1],int(f[2])/1e3,int(f[3])/1e3))
    elif f[0]=='CELL' and f[6]=='1': MAC.append([int(v)/1e3 for v in f[2:6]])
    elif f[0]=='ROOT': root=(int(f[1])/1e3,int(f[2])/1e3)
    elif f[0]=='CORE': core=[int(v)/1e3 for v in f[1:5]]
YM=(YS[0]+YS[-1])/2; M=(XS,YM)
def hblocked(y,x0,x1):
    lo,hi=min(x0,x1),max(x0,x1)
    return any(m[1]<y<m[3] and lo<m[2] and hi>m[0] for m in MAC)
# hubs: 25-um bins, chunked by HUB along y, hub = medoid
B=collections.defaultdict(list)
for t in T: B[(int(t[1]//25),int(t[2]//25))].append(t)
hubs=[]
for k,v in B.items():
    v.sort(key=lambda t:(t[2],t[1])); n=math.ceil(len(v)/HUB)
    for i in range(n):
        g=v[i*len(v)//n:(i+1)*len(v)//n]
        cx=sum(t[1] for t in g)/len(g); cy=sum(t[2] for t in g)/len(g)
        m=min(g,key=lambda t:abs(t[1]-cx)+abs(t[2]-cy))
        hubs.append(dict(xy=(m[1],m[2]),taps=g))
# rib route: from spine point (XS,ys) horizontal on M4 at ys to hx (must be legal), then M5 vertical to hy
for h in hubs:
    hx,hy=h['xy'];best=None
    for ys in YS:
        if hblocked(ys,XS,hx): continue
        d=abs(hx-XS)+abs(hy-ys); sp=abs(ys-YM)
        c=(d+sp, d)            # minimise total root->hub, i.e. pick the rib that does not climb the spine needlessly
        if best is None or c<best[0]: best=(c,ys,d)
    h['ys']=best[1]; h['rib']=best[2]
lead=abs(root[0]-XS)+abs(root[1]-YM)
spine={ys:abs(ys-YM) for ys in YS}
used=sorted({h['ys'] for h in hubs})
def reps(dmax): return max(0,math.ceil(dmax/RMAX)-1)
n0=reps(lead); n1=reps(max(spine[y] for y in used)); n2=reps(max(h['rib'] for h in hubs))
locs=[abs(t[1]-h['xy'][0])+abs(t[2]-h['xy'][1]) for h in hubs for t in h['taps']]; n3=reps(max(locs))
# Elmore estimate (assumed BUFx24: t0 14 ps, Rdrv 0.10 kOhm, Cin 3.0 fF; wire r 0.0185 kOhm/um, c 0.11 fF/um; tap BUFx12f Cin 1.6 fF)
t0,Rd,Ci,r,c,Ct=14.0,0.10,3.0,0.0185,0.11,1.6
def leg(d,n,cl=Ci):
    s=d/(n+1); return (n+1)*t0 + n*(Rd*(c*s+Ci)+r*s*(c*s/2+Ci)) + Rd*(c*s+cl)+r*s*(c*s/2+cl)
rows=[]
for h in hubs:
    for t in h['taps']:
        lc=abs(t[1]-h['xy'][0])+abs(t[2]-h['xy'][1])
        wl=lead+spine[h['ys']]+h['rib']+lc
        dl=leg(lead,n0)+leg(spine[h['ys']],n1)+leg(h['rib'],n2)+leg(lc,n3,Ct)
        rows.append((t[0],t[1],t[2],h['ys'],wl,n0+n1+n2+n3+4,dl))
wl=[r_[4] for r_ in rows]; dl=[r_[6] for r_ in rows]
fan=collections.Counter(h['ys'] for h in hubs)
S=dict(rmax_um=RMAX,hub_cap=HUB,taps=len(rows),hubs=len(hubs),spine_x=XS,spine_mid=M,lead_um=round(lead,1),
       reps=dict(lead=n0,spine=n1,rib=n2,tap=n3),stages=sorted({r_[5] for r_ in rows}),
       wl_min=round(min(wl),1),wl_max=round(max(wl),1),wl_spread=round(max(wl)-min(wl),1),
       rib_max=round(max(h['rib'] for h in hubs),1),local_max=round(max(locs),1),
       elmore_ps_min=round(min(dl),1),elmore_ps_max=round(max(dl),1),elmore_spread_ps=round(max(dl)-min(dl),1),
       rib_legs_per_spine_point={str(k):fan[k] for k in sorted(fan)},
       buffers=(n0+1)+len(used)*(n1+1)+len(hubs)*(n2+1)+len(rows)*(n3+1))
json.dump(dict(summary=S,macros=MAC,core=core,root=root,hubs=[dict(xy=h['xy'],ys=h['ys'],rib=h['rib'],n=len(h['taps'])) for h in hubs],
               taps=rows,YS=YS),open(out,'w'))
print(json.dumps(S))
