import json,sys,collections,statistics
# per-partition and per-region tap arrival spread (TT/FF arr file), DIE-QC-2 pspread + region column
D=sys.argv[1]; arrf=sys.argv[2]; R=json.load(open(sys.argv[3]))["part_region"] if len(sys.argv)>3 else {}
sc=float(sys.argv[4]) if len(sys.argv)>4 else 1.0
P={}
for l in open(arrf):
    s=l.split()
    if s and s[0]=="T": P[s[1]]=float(s[2])*sc
t=json.load(open(D+"/clk/tree.json")) if __import__("os").path.exists(D+"/clk/tree.json") else json.load(open(D+"/trial/clock/tree.json"))
part={x["port"]:x["part"] for x in t["taps"]}
by=collections.defaultdict(list); rg=collections.defaultdict(list)
for k,v in P.items(): by[part[k]].append(v); rg[R.get(part[k],"?")].append(v)
sp=sorted(((max(v)-min(v)),p) for p,v in by.items())
std=[s for s,p in sp if not p.startswith("c_W5")]
print("per-partition spread: median %.0f p90 %.0f max %.0f (%s); non-W5 max %.0f; n>150: %d/%d; insertion %.0f-%.0f"%(statistics.median(s for s,_ in sp), sp[int(.9*len(sp))][0], sp[-1][0], sp[-1][1], max(std), sum(1 for s,_ in sp if s>150), len(sp), min(P.values()), max(P.values())))
print("top5", [(round(s),p) for s,p in sp[-5:]])
print("per-region spread:", sorted((round(max(v)-min(v)),r) for r,v in rg.items()))
