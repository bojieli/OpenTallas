import json,sys,collections,statistics
D=sys.argv[1]; arrf=sys.argv[2] if len(sys.argv)>2 else D+"/trial/clock/arr_TT.txt"
def rd(f):
    o={}
    for l in open(f):
        s=l.split()
        if s[0]=="T": o[s[1]]=float(s[2])
    return o
P=rd(arrf)
t=json.load(open(D+"/trial/clock/tree.json"))
part={x["port"]:x["part"] for x in t["taps"]}
by=collections.defaultdict(list)
for k,v in P.items(): by[part[k]].append(v)
sp=sorted(((max(v)-min(v)),p) for p,v in by.items())
std=[s for s,p in sp if not p.startswith("c_W5")]
print("per-partition spread: median %.0f max %.0f (%s); std max %.0f; insertion %.0f-%.0f"%(statistics.median(s for s,_ in sp), sp[-1][0], sp[-1][1], max(std), min(P.values()), max(P.values())))
print("top5", [(round(s),p) for s,p in sp[-5:]])
