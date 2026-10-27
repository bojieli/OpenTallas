import json,collections,sys
d=json.load(open(sys.argv[1]))
cs=d["cell_sites"]; nets=d["nets"]
G=collections.defaultdict(list)
for n,v in cs.items(): G["g%d"%v["group"]].append(n)
def c0(g): return cs[sorted(G[g],key=lambda u:cs[u]["origin_um"][1])[0]]
by=collections.defaultdict(list)
for n in nets: by[n["drv"]].append(n)
iv=[]
for g,ns in by.items():
    if ns[0]["layer"]!="M9": continue
    ys=[c0(g)["origin_um"][1]]+[c0(n["load"])["origin_um"][1] for n in ns]
    iv.append((round(c0(g)["origin_um"][0]), min(ys), max(ys), g, ns[0]["edge"]))
cols=collections.defaultdict(list)
for r in iv: cols[round(r[0]/50)].append(r)
for k,L in sorted(cols.items())[:3]:
    ev=[]
    for r in L: ev+=[(r[1]-3.4,1,r),(r[2]+3.4,-1,r)]
    ev.sort(key=lambda e:(e[0],e[1]))
    c=m=0;where=None
    for y,e,r in ev:
        c+=e
        if c>m: m=c;where=y
    print("col x~",k*50,"nets",len(L),"max depth",m,"at y",where)
    for r in sorted(L,key=lambda r:r[1]):
        if r[1]<=where<=r[2]+4: print("   ",r)
