import json,collections,sys
d=json.load(open(sys.argv[1]))
cs=d["cell_sites"]; nets=d["nets"]
G=collections.defaultdict(list)
for n,v in cs.items(): G["g%d"%v["group"]].append(n)
for g in G: G[g].sort(key=lambda u: cs[u]["origin_um"][1])
def pins(g,pin):
    out=[]
    for u in G[g]:
        v=cs[u]; x,y=v["origin_um"]
        bar={"A":0.027,"Y":1.593}[pin]
        if v["orient"] in("MY","R180"): bar=1.593+0.027-bar
        out.append((round(x+bar,4),round(y+0.135,4)))
    return out
by=collections.defaultdict(list)
for n in nets: by[n["drv"]].append(n)
rows=[]
bad=collections.Counter()
for g,ns in by.items():
    if ns[0]["layer"]!="M8": continue
    D=pins(g,"Y")[0]
    L=[p for n in ns for p in [min(pins(n["load"],"A"),key=lambda q:abs(q[1]-D[1]))]]
    dy=max(abs(p[1]-D[1]) for p in L)
    xs=[D[0]]+[p[0] for p in L]
    rows.append((D[1],min(xs),max(xs),dy,g,cs[G[g][0]]["kind"]))
    bad["dy>1.6" if dy>1.636 else "ok"]+=1
print("M8 nets",len(rows),bad)
import statistics
print("dy hist",collections.Counter(round(r[3]) for r in rows).most_common(12))
# cluster lines
rows.sort()
lines=[];cur=[]
for r in rows:
    if cur and r[0]-cur[-1][0]>12: lines.append(cur);cur=[]
    cur.append(r)
lines.append(cur)
print("lines",len(lines))
mm=8.64
depth=collections.Counter()
for L in lines:
    ev=[]
    for r in L: ev+= [(r[1]-mm,1),(r[2]+mm,-1)]
    ev.sort(key=lambda e:(e[0],e[1]))
    c=m=0
    for _,e in ev: c+=e; m=max(m,c)
    depth[m]+=1
print("line overlap depth (mm-reserved)",sorted(depth.items()))
ys=collections.Counter(round(r[0],2) for r in rows)
print("distinct driver pin rows",len(ys))
for mmv in (0.0,2.0):
    depth=collections.Counter()
    for L in lines:
        ev=[]
        for r in L: ev+= [(r[1]-mmv,1),(r[2]+mmv,-1)]
        ev.sort(key=lambda e:(e[0],e[1]))
        c=m=0
        for _,e in ev: c+=e; m=max(m,c)
        depth[m]+=1
    print("depth mm=",mmv,sorted(depth.items()))
L=lines[3]
print("line y",L[0][0], len(L))
for r in sorted(L,key=lambda r:r[1]):
    if r[1]<5000: print(r)
