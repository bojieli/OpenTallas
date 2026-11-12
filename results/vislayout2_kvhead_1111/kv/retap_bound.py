# VISLAYOUT2 RF1b (COORD 19:2x): balanced taps with a reach bound.  Recursive bisection of the placed clk flops: a
# cluster becomes a tap when its reach (tap at the cluster median, moved off keepouts/macros) <= REACH and its count
# <= CAP; else split at the median of its longer axis.  Existing tap IDs are kept (least-displacement match); extra
# clusters get new added_taps clk_t<next>.  Reports the nearest-tap split (the plan_geom clock_tap_sinks rule, <= 1500,
# no empty tap).
import json,sys,math,os
plan,geom,out,TN,SRC=sys.argv[1:6]
sys.path.insert(0,SRC+"/tools/die_plan"); import schema, taps as TP
from placement_obstacles import placement_boxes
REACH=float(os.environ.get("REACH","400")); CAP=int(os.environ.get("CAP","1200")); GRID_R=float(os.environ.get("GRID_R","120"))
p=json.load(open(plan)); t=p["partition_types"][TN]; c=t["clock"]; W,H=t["outline_um"]
P0=schema.Plan(p,plan); grid=schema._grid_taps(P0,TN)          # pitch-grid taps: fixed (names clk, clk_t1..)
taps=[[a["name"]]+list(a["xy"]) for a in c["added_taps"]]      # movable: the added taps (tap_um untouched)
CLR=schema.TAP_CLEAR_UM
KO=[tuple(k) for k in c.get("keepouts_um",[])]+list(placement_boxes(t,halo=CLR).values())
pts=[]
for l in open(geom):
    if l.startswith("C\t") and "DFF" in l:
        f=l.split("\t"); n=f[8]
        if "u_ring.s_d" in n or "sd_c" in n: continue
        q=((float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2)
        if min(math.dist(q,(x,y)) for _,x,y in grid)<=GRID_R: continue      # served by a fixed grid tap
        pts.append(q)
g=lambda v,s,lo,hi: min(max(round(round(v/s)*s,3),lo),hi)
def site(P):
    med=lambda v: sorted(v)[len(v)//2]
    nx,ny=g(med([q[0] for q in P]),0.54,8.64,W-8.64),g(med([q[1] for q in P]),0.27,8.64,H-8.64)
    for (a,b,c2,d) in KO:
        if a<nx<c2 and b<ny<d:
            o=[(nx-a,a-0.54,ny),(c2-nx,c2+0.54,ny),(ny-b,nx,b-0.27),(d-ny,nx,d+0.27)]
            o=[z for z in o if CLR<=z[1]<=W-CLR and CLR<=z[2]<=H-CLR]
            _,nx,ny=min(o); nx,ny=g(nx,0.54,CLR,W-CLR),g(ny,0.27,CLR,H-CLR)
    return nx,ny
def legal(x,y,taken):
    return (CLR<=x<=W-CLR and CLR<=y<=H-CLR and not any(abs(x-a)<CLR and abs(y-b)<CLR for a,b in taken)
            and not any(a<x<c2 and b<y<d for a,b,c2,d in KO))
def legalise(x,y,taken):
    if legal(x,y,taken): return x,y
    for r in range(1,200):
        for dx in range(-r,r+1):
            for dy in (-r,r) if abs(dx)<r else range(-r,r+1):
                nx,ny=g(x+dx*2.16,0.54,CLR,W-CLR),g(y+dy*2.16,0.27,CLR,H-CLR)
                if legal(nx,ny,taken): return nx,ny
    raise SystemExit("no legal tap site near %s"%((x,y),))
def split(P):
    s=site(P); r=max(math.dist(s,q) for q in P)
    if (r<=REACH and len(P)<=CAP) or len(P)<2: return [(s,P,r)]
    xs=[q[0] for q in P]; ys=[q[1] for q in P]
    ax=0 if (max(xs)-min(xs))>=(max(ys)-min(ys)) else 1
    P=sorted(P,key=lambda q:q[ax]); m=len(P)//2
    return split(P[:m])+split(P[m:])
cl=split(pts)
# merge pass is not needed: K >= old tap count is required (no tap removed); if fewer, split the largest
while len(cl)<len(taps):
    cl.sort(key=lambda z:-len(z[1])); s,P,r=cl.pop(0)
    xs=[q[0] for q in P]; ys=[q[1] for q in P]; ax=0 if (max(xs)-min(xs))>=(max(ys)-min(ys)) else 1
    P=sorted(P,key=lambda q:q[ax]); m=len(P)//2
    for h in (P[:m],P[m:]): sh=site(h); cl.append((sh,h,max(math.dist(sh,q) for q in h)))
pairs=sorted((math.dist(taps[i][1:],cl[j][0]),i,j) for i in range(len(taps)) for j in range(len(cl)))
ui,uj={},set()
for d,i,j in pairs:
    if i in ui or j in uj: continue
    ui[i]=j; uj.add(j)
import re
nxt=len(grid)+len(taps)
names={ui[i]:taps[i][0] for i in ui}
for j in range(len(cl)):
    if j not in names: names[j]=f"clk_t{nxt}"; nxt+=1
order=[a["name"] for a in c["added_taps"]]+sorted(set(names.values())-{a["name"] for a in c["added_taps"]},key=lambda s:int(s[5:]))
byname={names[j]:j for j in names}; taken=[(x,y) for _,x,y in grid]; new={}
for n in order:
    x,y=legalise(*cl[byname[n]][0],taken); new[n]=[x,y]; taken.append((x,y))
c["added_taps"]=[{"name":n,"xy":new[n]} for n in order]
TP.grid_explicit_sites(schema.Plan(p,plan),TN)                 # the generator's own legality check (raises)
# nearest-tap split (plan_geom rule)
sites=list(new.items())+[(n,[x,y]) for n,x,y in grid]; load={n:0 for n,_ in sites}
allp=[((float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2) for f in (l.split("\t") for l in open(geom) if l.startswith("C\t") and "DFF" in l) if "u_ring.s_d" not in f[8] and "sd_c" not in f[8]]
for x,y in allp:
    load[min(sites,key=lambda s:(s[1][0]-x)**2+(s[1][1]-y)**2)[0]]+=1
top=sorted(load.items(),key=lambda q:-q[1])[:3]; low=sorted(load.items(),key=lambda q:q[1])[:2]
print(top,low)
print(TN,"grid",len(grid),"flops(non-grid)",len(pts),"added taps",len(taps),"->",len(cl),"cluster load",min(len(z[1]) for z in cl),max(len(z[1]) for z in cl),
      "reach max",round(max(z[2] for z in cl)),"| nearest split",min(load.values()),max(load.values()),"empty",sum(v==0 for v in load.values()))
json.dump(p,open(out,"w"),indent=1)
oldxy={n:[x,y] for n,x,y in taps}
json.dump({TN:{"clock.taps":{n:[oldxy.get(n),xy] for n,xy in new.items()},"reach_um_max":round(max(z[2] for z in cl)),"rule":f"REACH {REACH} CAP {CAP}"}},open(out+".delta.json","w"),indent=1)
