"""KV-PLAN-DELTA-6 what-if: drop whole lanes (ports + their ft slots) to measure tile FT capacity premises."""
import json,sys
inp,outp=sys.argv[1:3]; lids=set(sys.argv[3:])
d=json.load(open(inp)); T=d["partition_types"]; PT={p["name"]:p["type"] for p in d["partitions"]}
P={p["id"]:p for p in d["ports"]}
drop=set(); slots=set()
for l in d["lanes"]:
    if l["id"] in lids:
        for pid in l["ports"]:
            drop.add(pid); q=P[pid]
            if q["dst"]["bus"].startswith("ft") and q["dst"]["bus"].endswith("_i"): slots.add((PT[q["dst"]["part"]],q["dst"]["bus"][:-2]))
d["lanes"]=[l for l in d["lanes"] if l["id"] not in lids]
for lid in lids: d["latency"]["lanes"].pop(lid,None)
d["ports"]=[p for p in d["ports"] if p["id"] not in drop]
for tn,s in slots: T[tn]["ft_slots"]=[x for x in T[tn]["ft_slots"] if x["name"]!=s]
for g in d.get("latency_groups",[]): assert not set(g["lanes"])&lids
json.dump(d,open(outp,"w"),indent=1); print("dropped",len(drop),"ports",sorted(slots))
