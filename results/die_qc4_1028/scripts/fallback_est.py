import json,sys,collections
# per-region fallback estimate: min(stock balance_legalize, region-dme) routed per-region tap spread (x spice factor)
A,B,R=sys.argv[1:4]; R=json.load(open(R))["part_region"]
def spread(D,C,f):
    t=json.load(open(D+"/clk/tree.json")); part={x["port"]:x["part"] for x in t["taps"]}
    rg=collections.defaultdict(list)
    for l in open(f"{D}/out_{C}/arr_{C}.txt"):
        s=l.split()
        if s and s[0]=="T": rg[R.get(part[s[1]],"?")].append(float(s[2])*f)
    return {r:max(v)-min(v) for r,v in rg.items()}
out={}
for C,f in (("TT",1.0485),("FF",1.0552)):
    a=spread(A,C,f); b=spread(B,C,f)
    pick={r:("stock" if a.get(r,1e9)<b.get(r,1e9) else "dme") for r in set(a)|set(b)}
    best={r:min(a.get(r,1e9),b.get(r,1e9)) for r in pick}
    w=sorted(best.items(),key=lambda x:-x[1])[:8]
    print(C,"stock max %.0f dme max %.0f | fallback max %.0f n>150 %d, picks stock %d dme %d; worst"%(max(a.values()),max(b.values()),max(best.values()),sum(v>150 for v in best.values()),sum(p=="stock" for p in pick.values()),sum(p=="dme" for p in pick.values())),[(r,round(v),pick[r]) for r,v in w])
    out[C]={r:[round(a.get(r,-1),1),round(b.get(r,-1),1),pick[r]] for r in pick}
json.dump(out,open(sys.argv[4],"w"),indent=0)
