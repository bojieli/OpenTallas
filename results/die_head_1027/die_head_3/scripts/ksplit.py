import json,sys
from collections import defaultdict
lp=json.load(open(sys.argv[1]));ca=json.load(open(sys.argv[2]));base=json.load(open(sys.argv[3]))
K={c["port"]:c["K"] for c in ca["crossings"]}
ptype={p["name"]:p["type"] for p in lp["partitions"]}
sig=defaultdict(list)
for p in base["ports"]:
    if p["id"] in K:
        sig[p["src"]["part"]].append(("tx",p["src"].get("bus"),K[p["id"]]))
        sig[p["dst"]["part"]].append(("rx",p["dst"].get("bus"),K[p["id"]]))
t=defaultdict(set)
for n,ty in ptype.items(): t[ty].add(tuple(sorted(sig.get(n,[]))))
print("types after landed-mask split",len(t),"after CA K-signature split",sum(len(v) for v in t.values()))
print({k:len(v) for k,v in t.items() if len(v)>1})
