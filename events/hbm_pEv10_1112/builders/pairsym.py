# NW/NE symmetry of lanes landing on shared-type partition pairs (one type => identical landing pads)
import json,sys,collections
d=json.load(open(sys.argv[1])); P={x["id"]:x for x in d["ports"]}; parts=d["partitions"]; parts=parts if isinstance(parts,dict) else {x["name"]:x for x in parts}
tab=d["latency"]["lanes"]; use=collections.defaultdict(list)
for n,p in parts.items(): use[p["type"]].append(n)
land=collections.defaultdict(dict)
for L in d["lanes"]:
    last=P[L["ports"][-1]]["dst"]
    if last["part"] in parts: land[last["part"]][last["bus"]]=(L["id"],tab[L["id"]]["cycles"])
bad=0
for t,ns in use.items():
    if len(ns)!=2: continue
    a,b=ns
    for bus in sorted(set(land[a])|set(land[b])):
        x=land[a].get(bus); y=land[b].get(bus)
        if x and y and x[1]!=y[1]:
            bad+=1; print(f"  {t} {bus}: {a} {x[0]}={x[1]}  {b} {y[0]}={y[1]}")
print(sys.argv[1].split("/")[-2],"shared-type pair landing mismatches",bad)
