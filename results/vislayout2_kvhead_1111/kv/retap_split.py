# VISLAYOUT2 RF1c: keep every existing tap (they satisfy the plan-sink radius incl. reset relays) and ADD taps that
# split the heavy ones: placed clk flops -> nearest tap (Manhattan, the kit split); a tap with load > CAP is
# bisected (longer axis, median) until each part <= CAP and reach <= REACH; part 0 keeps the old tap, every other
# part gets a new added tap at its median (legalised off taps / reset taps / macro halos).  Validated with the
# generator's own taps.grid_explicit_taps (plan sinks + relays, radius 200, cap 1500).
import json,sys,math,os
plan,geom,out,TN,SRC=sys.argv[1:6]
sys.path.insert(0,SRC+"/tools/die_plan"); import schema, taps as TP
from placement_obstacles import placement_boxes
CAP=int(os.environ.get("CAP","700")); REACH=float(os.environ.get("REACH","250"))
p=json.load(open(plan)); t=p["partition_types"][TN]; c=t["clock"]; W,H=t["outline_um"]
P0=schema.Plan(p,plan); sites=TP.grid_explicit_sites(P0,TN); n_grid=len(schema._grid_taps(P0,TN))
CLR=schema.TAP_CLEAR_UM; KO=[tuple(k) for k in c.get("keepouts_um",[])]+list(placement_boxes(t,halo=CLR).values())
MAN=lambda a,b: abs(a[0]-b[0])+abs(a[1]-b[1])
pts=[]
for l in open(geom):
    if l.startswith("C\t") and "DFF" in l:
        f=l.split("\t")
        if "u_ring.s_d" in f[8] or "sd_c" in f[8]: continue
        pts.append(((float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2))
own={i:[] for i in range(len(sites))}
for q in pts: own[min(range(len(sites)),key=lambda i:MAN(q,sites[i][1:]))].append(q)
g=lambda v,s,lo,hi: min(max(round(round(v/s)*s,3),lo),hi)
taken=[(x,y) for _,x,y in sites]+[(float(x),float(y)) for x,y in (t.get("reset") or {}).get("local_taps_um",[])]
def legal(x,y): return (CLR<=x<=W-CLR and CLR<=y<=H-CLR and not any(abs(x-a)<CLR and abs(y-b)<CLR for a,b in taken)
                        and not any(a<x<c2 and b<y<d for a,b,c2,d in KO))
def legalise(x,y):
    x,y=g(x,0.54,CLR,W-CLR),g(y,0.27,CLR,H-CLR)
    for r in range(0,300):
        for dx in range(-r,r+1):
            for dy in ((-r,r) if abs(dx)<r else range(-r,r+1)):
                nx,ny=g(x+dx*2.16,0.54,CLR,W-CLR),g(y+dy*2.16,0.27,CLR,H-CLR)
                if legal(nx,ny): return nx,ny
    raise SystemExit("no site")
def parts(P,s):
    if len(P)<=CAP and max(MAN(s,q) for q in P)<=REACH: return [P]
    xs=[q[0] for q in P]; ys=[q[1] for q in P]; ax=0 if max(xs)-min(xs)>=max(ys)-min(ys) else 1
    P=sorted(P,key=lambda q:q[ax]); m=len(P)//2
    med=lambda v: sorted(v)[len(v)//2]
    out=[]
    for h in (P[:m],P[m:]): out+=parts(h,(med([q[0] for q in h]),med([q[1] for q in h])))
    return out
added=[]; nxt=len(sites)
for i in range(len(sites)):
    P=own[i]
    if len(P)<=CAP: continue
    ps=parts(P,sites[i][1:])
    ps.sort(key=lambda h: min(MAN(sites[i][1:],q) for q in h))       # the part nearest the old tap keeps it
    for h in ps[1:]:
        med=lambda v: sorted(v)[len(v)//2]
        x,y=legalise(med([q[0] for q in h]),med([q[1] for q in h])); taken.append((x,y))
        added.append({"name":f"clk_t{nxt}","xy":[x,y],"split_of":sites[i][0],"placed_sinks":len(h)}); nxt+=1
c["added_taps"]=list(c["added_taps"])+[{"name":a["name"],"xy":a["xy"]} for a in added]
json.dump(p,open(out,"w"),indent=1)
r=TP.grid_explicit_taps(schema.Plan(p,out),TN)
allt=[(n,x,y) for n,x,y,_,_ in r]; ld={n:0 for n,_,_ in allt}; far={n:0 for n,_,_ in allt}
for q in pts:
    n,x,y=min(allt,key=lambda z:MAN(q,z[1:])); ld[n]+=1; far[n]=max(far[n],MAN(q,(x,y)))
print(TN,"taps",len(sites),"->",len(r),"| placed split load",min(ld.values()),max(ld.values()),"reach(manh) max",round(max(far.values())),
      "| generator plan-sink radius max",round(max(z[4] for z in r[n_grid:])),"load",round(min(z[3] for z in r)),round(max(z[3] for z in r)))
json.dump({TN:{"added_taps":added,"rule":f"split placed load > {CAP} or reach > {REACH}"}},open(out+".delta.json","w"),indent=1)
